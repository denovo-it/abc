#!/usr/bin/env python3
"""
Book Database Setup and Management

Unified script for:
- Database schema creation
- Open Library bulk download and import
- Manual book/author/publisher management
- Database queries and statistics

Usage:
    python3 setup_database.py download          # Download Open Library dump (~12GB)
    python3 setup_database.py import            # Import downloaded dump
    python3 setup_database.py import --lang it  # Import only Italian books
    python3 setup_database.py stats             # Show database statistics
    python3 setup_database.py add "Title" "Author" "Publisher"
    python3 setup_database.py search "query"
    python3 setup_database.py add-imprint "OSCAR" "MONDADORI"

Data Source: Open Library (openlibrary.org)
License: Open Database License (ODbL) v1.0
"""

import os
import sys
import json
import gzip
import time
import sqlite3
import subprocess
import re
import urllib.request
import urllib.parse
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Set
from difflib import SequenceMatcher


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Book:
    """Book metadata"""
    title: str
    author: str
    publisher: str = ""
    isbn: str = ""
    year: int = 0
    language: str = "en"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# =============================================================================
# DATABASE CLASS
# =============================================================================

class BookDatabase:
    """
    SQLite database for books, authors, publishers, and imprints.
    Used by scan_books.py for OCR validation and fuzzy matching.
    """

    def __init__(self, db_path: str = "books.db"):
        self.db_path = db_path
        self._init_db()
        # Caches for fast lookups
        self._authors_cache = None
        self._publishers_cache = None
        self._imprints_cache = None

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Books table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                title_normalized TEXT NOT NULL,
                author TEXT NOT NULL,
                author_normalized TEXT NOT NULL,
                publisher TEXT DEFAULT '',
                isbn TEXT DEFAULT '',
                year INTEGER DEFAULT 0,
                language TEXT DEFAULT 'en',
                ol_key TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Authors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                name_normalized TEXT NOT NULL,
                book_count INTEGER DEFAULT 1
            )
        ''')

        # Publishers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS publishers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                name_normalized TEXT NOT NULL,
                book_count INTEGER DEFAULT 1
            )
        ''')

        # Imprints table (maps imprint/series to parent publisher)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS imprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imprint TEXT NOT NULL UNIQUE,
                imprint_normalized TEXT NOT NULL,
                parent_publisher TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def _create_indexes(self):
        """Create indexes for fast search (call after bulk import)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_title ON books(title_normalized)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_author ON books(author_normalized)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_isbn ON books(isbn)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lang ON books(language)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_author_name ON authors(name_normalized)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_publisher_name ON publishers(name_normalized)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_imprint ON imprints(imprint_normalized)')
        conn.commit()
        conn.close()

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # =========================================================================
    # BOOKS
    # =========================================================================

    def add_book(self, book: Book) -> bool:
        """Add a book. Returns True if added, False if duplicate."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        title_norm = self.normalize(book.title)
        author_norm = self.normalize(book.author)

        try:
            cursor.execute('''
                INSERT INTO books (title, title_normalized, author, author_normalized,
                                   publisher, isbn, year, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (book.title, title_norm, book.author, author_norm,
                  book.publisher, book.isbn, book.year, book.language))

            # Also add author and publisher
            self._add_author_internal(cursor, book.author)
            if book.publisher:
                self._add_publisher_internal(cursor, book.publisher)

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def add_books_batch(self, books_data: list) -> Tuple[int, int]:
        """Add multiple books efficiently (for bulk import)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        added = 0
        skipped = 0

        for data in books_data:
            title_norm = self.normalize(data[0])
            author_norm = self.normalize(data[1])

            try:
                cursor.execute('''
                    INSERT INTO books (title, title_normalized, author, author_normalized,
                                      publisher, isbn, year, language, ol_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (data[0], title_norm, data[1], author_norm,
                      data[2], data[3], data[4], data[5], data[6] if len(data) > 6 else ''))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1

        conn.commit()
        conn.close()

        return added, skipped

    def search_title(self, query: str, limit: int = 10) -> List[Book]:
        """Search books by title"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query_norm = self.normalize(query)
        cursor.execute('''
            SELECT title, author, publisher, isbn, year, language
            FROM books WHERE title_normalized LIKE ?
            ORDER BY title_normalized LIMIT ?
        ''', (f'%{query_norm}%', limit))

        results = [Book(title=r[0], author=r[1], publisher=r[2],
                       isbn=r[3], year=r[4], language=r[5])
                  for r in cursor.fetchall()]
        conn.close()
        return results

    def fuzzy_match_title(self, query: str, threshold: float = 0.6, limit: int = 5) -> List[Tuple[Book, float]]:
        """Fuzzy match title against database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT title, title_normalized, author, publisher, isbn, year, language FROM books')

        query_norm = self.normalize(query)
        matches = []

        for row in cursor.fetchall():
            ratio = SequenceMatcher(None, query_norm, row[1]).ratio()
            if ratio >= threshold:
                book = Book(title=row[0], author=row[2], publisher=row[3],
                           isbn=row[4], year=row[5], language=row[6])
                matches.append((book, ratio))

        conn.close()
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]

    def fuzzy_match_words(self, words: List[str], threshold: float = 0.7, limit: int = 5) -> List[Tuple[Book, float]]:
        """Match OCR words against book titles"""
        combined = ' '.join(words)
        combined_norm = self.normalize(combined)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT title, title_normalized, author, publisher, isbn, year, language FROM books')

        matches = []
        stopwords = {'the', 'a', 'an', 'of', 'and', 'in', 'on', 'at', 'to', 'il', 'la', 'lo', 'gli', 'le', 'di', 'da'}

        for row in cursor.fetchall():
            title_norm = row[1]

            # Direct similarity
            ratio1 = SequenceMatcher(None, combined_norm, title_norm).ratio()

            # Word overlap (order-independent)
            title_words = set(title_norm.split()) - stopwords
            query_words = set(combined_norm.split()) - stopwords

            if title_words and query_words:
                overlap = len(title_words & query_words)
                ratio2 = overlap / len(title_words) if title_words else 0
            else:
                ratio2 = 0

            best_ratio = max(ratio1, ratio2)

            if best_ratio >= threshold:
                book = Book(title=row[0], author=row[2], publisher=row[3],
                           isbn=row[4], year=row[5], language=row[6])
                matches.append((book, best_ratio))

        conn.close()
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]

    # =========================================================================
    # AUTHORS
    # =========================================================================

    def _add_author_internal(self, cursor, name: str):
        """Add author using existing cursor"""
        if not name or name == 'Unknown':
            return
        name_norm = self.normalize(name)
        try:
            cursor.execute('''
                INSERT INTO authors (name, name_normalized, book_count)
                VALUES (?, ?, 1)
                ON CONFLICT(name) DO UPDATE SET book_count = book_count + 1
            ''', (name, name_norm))
        except Exception:
            pass

    def add_author(self, name: str) -> bool:
        """Add an author"""
        if not name:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO authors (name, name_normalized, book_count)
                VALUES (?, ?, 1)
                ON CONFLICT(name) DO UPDATE SET book_count = book_count + 1
            ''', (name, self.normalize(name)))
            conn.commit()
            self._authors_cache = None
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_all_authors(self) -> Set[str]:
        """Get all authors as uppercase set"""
        if self._authors_cache is not None:
            return self._authors_cache

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM authors')
        authors = {row[0].upper() for row in cursor.fetchall()}
        conn.close()

        self._authors_cache = authors
        return authors

    def is_known_author(self, name: str) -> bool:
        """Check if author is known"""
        return name.upper() in self.get_all_authors()

    # =========================================================================
    # PUBLISHERS
    # =========================================================================

    def _add_publisher_internal(self, cursor, name: str):
        """Add publisher using existing cursor"""
        if not name:
            return
        name_norm = self.normalize(name)
        try:
            cursor.execute('''
                INSERT INTO publishers (name, name_normalized, book_count)
                VALUES (?, ?, 1)
                ON CONFLICT(name) DO UPDATE SET book_count = book_count + 1
            ''', (name, name_norm))
        except Exception:
            pass

    def add_publisher(self, name: str) -> bool:
        """Add a publisher"""
        if not name:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO publishers (name, name_normalized, book_count)
                VALUES (?, ?, 1)
                ON CONFLICT(name) DO UPDATE SET book_count = book_count + 1
            ''', (name, self.normalize(name)))
            conn.commit()
            self._publishers_cache = None
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_all_publishers(self) -> Set[str]:
        """Get all publishers as uppercase set"""
        if self._publishers_cache is not None:
            return self._publishers_cache

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM publishers')
        publishers = {row[0].upper() for row in cursor.fetchall()}
        conn.close()

        self._publishers_cache = publishers
        return publishers

    def is_known_publisher(self, name: str) -> bool:
        """Check if publisher is known"""
        return name.upper() in self.get_all_publishers()

    # =========================================================================
    # IMPRINTS
    # =========================================================================

    def add_imprint(self, imprint: str, parent_publisher: str) -> bool:
        """Add an imprint mapping"""
        if not imprint or not parent_publisher:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO imprints (imprint, imprint_normalized, parent_publisher)
                VALUES (?, ?, ?)
            ''', (imprint.upper(), self.normalize(imprint), parent_publisher.upper()))
            conn.commit()
            self._imprints_cache = None
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_all_imprints(self) -> dict:
        """Get all imprints as dict {IMPRINT: PUBLISHER}"""
        if self._imprints_cache is not None:
            return self._imprints_cache

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT imprint, parent_publisher FROM imprints')
        imprints = {row[0].upper(): row[1] for row in cursor.fetchall()}
        conn.close()

        self._imprints_cache = imprints
        return imprints

    def get_parent_publisher(self, imprint: str) -> Optional[str]:
        """Get parent publisher for an imprint"""
        return self.get_all_imprints().get(imprint.upper())

    # =========================================================================
    # STATS & EXPORT
    # =========================================================================

    def get_stats(self) -> dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}
        for table, key in [('books', 'total_books'), ('authors', 'total_authors'),
                           ('publishers', 'total_publishers'), ('imprints', 'total_imprints')]:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[key] = cursor.fetchone()[0]

        cursor.execute('SELECT language, COUNT(*) FROM books GROUP BY language ORDER BY COUNT(*) DESC')
        stats['by_language'] = dict(cursor.fetchall())

        conn.close()
        return stats

    def export_json(self, filepath: str):
        """Export books to JSON"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT title, author, publisher, isbn, year, language FROM books')

        books = [{'title': r[0], 'author': r[1], 'publisher': r[2],
                  'isbn': r[3], 'year': r[4], 'language': r[5]}
                 for r in cursor.fetchall()]
        conn.close()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=2, ensure_ascii=False)

    def import_json(self, filepath: str) -> Tuple[int, int]:
        """Import books from JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        added, skipped = 0, 0
        for d in data:
            book = Book.from_dict(d)
            if self.add_book(book):
                added += 1
            else:
                skipped += 1
        return added, skipped


# =============================================================================
# OPEN LIBRARY DOWNLOAD & IMPORT
# =============================================================================

DUMP_URL = 'https://openlibrary.org/data/ol_dump_editions_latest.txt.gz'
DATA_DIR = 'openlibrary_data'


def download_dump():
    """
    Download Open Library editions dump.

    Uses aria2c if available (parallel connections, faster),
    falls back to wget or curl with resume support.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = os.path.join(DATA_DIR, 'ol_dump_editions.txt.gz')

    print("=" * 60)
    print("DOWNLOAD OPEN LIBRARY DUMP")
    print("=" * 60)
    print(f"URL: {DUMP_URL}")
    print(f"Destination: {filename}")
    print(f"Size: ~12 GB")
    print()

    # Check for existing partial download
    if os.path.exists(filename):
        size_mb = os.path.getsize(filename) / 1024 / 1024
        print(f"Existing file found: {size_mb:.1f} MB - will resume")

    # Try aria2c first (fastest, parallel connections)
    aria2_available = subprocess.run(['which', 'aria2c'],
                                      capture_output=True).returncode == 0

    if aria2_available:
        print("Using aria2c (parallel download)...")
        cmd = [
            'aria2c',
            '--continue=true',           # Resume partial downloads
            '--max-connection-per-server=8',  # Parallel connections
            '--split=8',                 # Split file into parts
            '--min-split-size=10M',      # Min size per split
            '--max-tries=0',             # Infinite retries
            '--retry-wait=5',            # Wait 5s between retries
            '--timeout=60',              # Connection timeout
            '--connect-timeout=30',      # Connect timeout
            '--file-allocation=none',    # Don't pre-allocate (faster start)
            '--auto-file-renaming=false',
            '--allow-overwrite=true',
            '-d', DATA_DIR,
            '-o', 'ol_dump_editions.txt.gz',
            DUMP_URL
        ]
        try:
            result = subprocess.run(cmd)
            if result.returncode == 0:
                print(f"\nDownload complete: {filename}")
                _cleanup_download_log()
                return filename
            else:
                print(f"aria2c failed with code {result.returncode}, trying wget...")
        except Exception as e:
            print(f"aria2c error: {e}, trying wget...")

    # Try wget (with resume)
    wget_available = subprocess.run(['which', 'wget'],
                                     capture_output=True).returncode == 0

    if wget_available:
        print("Using wget (resume enabled)...")
        cmd = ['wget', '-c', '--tries=0', '--timeout=60', '-O', filename, DUMP_URL]
        try:
            result = subprocess.run(cmd)
            if result.returncode == 0:
                print(f"\nDownload complete: {filename}")
                _cleanup_download_log()
                return filename
        except Exception as e:
            print(f"wget error: {e}")

    # Fall back to curl
    print("Using curl...")
    cmd = ['curl', '-L', '-C', '-', '--retry', '999', '--retry-delay', '5',
           '-o', filename, DUMP_URL]
    try:
        subprocess.run(cmd, check=True)
        print(f"\nDownload complete: {filename}")
        _cleanup_download_log()
        return filename
    except Exception as e:
        print(f"Download failed: {e}")
        return None


def _cleanup_download_log():
    """Remove download.log after successful download"""
    log_file = 'download.log'
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
            print(f"Cleaned up {log_file}")
        except Exception:
            pass


def import_dump(db_path: str = 'books.db', language_filter: str = None, limit: int = None):
    """Import Open Library dump into database"""
    dump_file = os.path.join(DATA_DIR, 'ol_dump_editions.txt.gz')

    if not os.path.exists(dump_file):
        print(f"Dump file not found: {dump_file}")
        print("Run 'python3 setup_database.py download' first")
        return

    print("=" * 60)
    print("IMPORT OPEN LIBRARY DUMP")
    print("=" * 60)
    print(f"Source: {dump_file}")
    print(f"Database: {db_path}")
    if language_filter:
        print(f"Language filter: {language_filter}")
    if limit:
        print(f"Limit: {limit:,}")
    print()

    # Initialize database
    db = BookDatabase(db_path)

    # Drop and recreate for fresh import
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM books')
    cursor.execute('DELETE FROM authors')
    cursor.execute('DELETE FROM publishers')
    conn.commit()
    conn.close()

    # Stats
    total_lines = 0
    imported = 0
    skipped = 0
    batch = []
    batch_size = 10000

    start_time = datetime.now()

    with gzip.open(dump_file, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            total_lines += 1

            if total_lines % 100000 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = total_lines / elapsed if elapsed > 0 else 0
                print(f"  Lines: {total_lines:,} | Imported: {imported:,} | Rate: {rate:.0f}/s")

            # Parse line
            record = _parse_edition_line(line)
            if not record:
                skipped += 1
                continue

            # Language filter
            if language_filter and record['language'] != language_filter:
                skipped += 1
                continue

            # Add to batch
            batch.append((
                record['title'],
                record['author'],
                record['publisher'],
                record['isbn'],
                record['year'],
                record['language'],
                record['ol_key']
            ))
            imported += 1

            # Insert batch
            if len(batch) >= batch_size:
                db.add_books_batch(batch)
                batch = []

            if limit and imported >= limit:
                break

    # Insert remaining
    if batch:
        db.add_books_batch(batch)

    # Create indexes
    print("\nCreating indexes...")
    db._create_indexes()

    # Populate authors and publishers from books
    print("Populating authors and publishers...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO authors (name, name_normalized, book_count)
        SELECT author, author_normalized, COUNT(*) FROM books
        WHERE author != '' AND author != 'Unknown'
        GROUP BY author_normalized
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO publishers (name, name_normalized, book_count)
        SELECT publisher, LOWER(publisher), COUNT(*) FROM books
        WHERE publisher != ''
        GROUP BY publisher
    ''')
    conn.commit()
    conn.close()

    # Add default Italian imprints
    _add_default_imprints(db)

    elapsed = (datetime.now() - start_time).total_seconds()

    print()
    print("=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"Lines processed: {total_lines:,}")
    print(f"Books imported: {imported:,}")
    print(f"Skipped: {skipped:,}")
    print(f"Time: {elapsed/60:.1f} minutes")

    stats = db.get_stats()
    print(f"\nDatabase: {stats['total_books']:,} books, {stats['total_authors']:,} authors, {stats['total_publishers']:,} publishers")

    db_size = os.path.getsize(db_path)
    print(f"Size: {db_size / 1024 / 1024:.1f} MB")


def _parse_edition_line(line: str) -> Optional[dict]:
    """Parse a single line from Open Library dump"""
    try:
        parts = line.strip().split('\t')
        if len(parts) < 5:
            return None

        data = json.loads(parts[4])
        title = data.get('title', '')
        if not title:
            return None

        # Authors
        authors = []
        for ref in data.get('authors', []):
            if isinstance(ref, dict):
                authors.append(ref.get('key', '').replace('/authors/', ''))
        if not authors and 'by_statement' in data:
            authors = [data['by_statement']]

        # Publisher
        publishers = data.get('publishers', [])
        publisher = publishers[0] if publishers else ''

        # ISBN
        isbns = data.get('isbn_13', []) or data.get('isbn_10', [])
        isbn = isbns[0] if isbns else ''

        # Year
        year = 0
        pub_date = data.get('publish_date', '')
        if pub_date:
            match = re.search(r'(\d{4})', pub_date)
            if match:
                year = int(match.group(1))

        # Language
        lang = 'en'
        languages = data.get('languages', [])
        if languages:
            lang_key = languages[0].get('key', '') if isinstance(languages[0], dict) else ''
            if 'ita' in lang_key:
                lang = 'it'
            elif 'spa' in lang_key:
                lang = 'es'
            elif 'fra' in lang_key:
                lang = 'fr'
            elif 'deu' in lang_key or 'ger' in lang_key:
                lang = 'de'

        return {
            'title': title,
            'author': ', '.join(authors[:2]) if authors else 'Unknown',
            'publisher': publisher,
            'isbn': isbn,
            'year': year,
            'language': lang,
            'ol_key': parts[1] if len(parts) > 1 else ''
        }
    except Exception:
        return None


def _add_default_imprints(db: BookDatabase):
    """Add default Italian publisher imprints"""
    imprints = [
        # Mondadori
        ('OSCAR', 'MONDADORI'), ('OSCAR MONDADORI', 'MONDADORI'),
        ('OSCAR BESTSELLERS', 'MONDADORI'), ('OSCAR CLASSICI', 'MONDADORI'),
        ('OMNIBUS', 'MONDADORI'), ('STRADE BLU', 'MONDADORI'),
        # Rizzoli
        ('BUR', 'RIZZOLI'), ('BUR RIZZOLI', 'RIZZOLI'),
        # Einaudi
        ('EINAUDI TASCABILI', 'EINAUDI'), ('SUPER ET', 'EINAUDI'),
        ('STILE LIBERO', 'EINAUDI'),
        # Feltrinelli
        ('UNIVERSALE ECONOMICA', 'FELTRINELLI'), ('UE FELTRINELLI', 'FELTRINELLI'),
        # Adelphi
        ('BIBLIOTECA ADELPHI', 'ADELPHI'), ('PICCOLA BIBLIOTECA ADELPHI', 'ADELPHI'),
        # Newton Compton
        ('GRANDI TASCABILI ECONOMICI', 'NEWTON COMPTON'),
        # Garzanti
        ('ELEFANTI', 'GARZANTI'), ('GLI ELEFANTI', 'GARZANTI'),
        # International
        ('PENGUIN CLASSICS', 'PENGUIN'), ('VINTAGE', 'RANDOM HOUSE'),
        ('ANCHOR', 'RANDOM HOUSE'), ('BANTAM', 'RANDOM HOUSE'),
    ]

    for imprint, publisher in imprints:
        db.add_imprint(imprint, publisher)


# =============================================================================
# CLI
# =============================================================================

def print_usage():
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        print_usage()
        db = BookDatabase('books.db')
        stats = db.get_stats()
        print(f"\nCurrent database: {stats['total_books']:,} books, {stats['total_authors']:,} authors")
        return

    cmd = sys.argv[1]

    if cmd == 'download':
        download_dump()

    elif cmd == 'import':
        lang = None
        limit = None
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] in ('--lang', '--language', '-l') and i + 1 < len(sys.argv):
                lang_map = {'it': 'it', 'ita': 'it', 'en': 'en', 'eng': 'en'}
                lang = lang_map.get(sys.argv[i + 1].lower(), sys.argv[i + 1])
                i += 2
            elif sys.argv[i] in ('--limit', '-n') and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1
        import_dump(language_filter=lang, limit=limit)

    elif cmd == 'stats':
        db = BookDatabase('books.db')
        stats = db.get_stats()
        print(f"Books:      {stats['total_books']:,}")
        print(f"Authors:    {stats['total_authors']:,}")
        print(f"Publishers: {stats['total_publishers']:,}")
        print(f"Imprints:   {stats['total_imprints']:,}")
        print(f"Languages:  {stats['by_language']}")

        if os.path.exists('books.db'):
            size = os.path.getsize('books.db')
            print(f"DB size:    {size / 1024 / 1024:.1f} MB")

    elif cmd == 'add' and len(sys.argv) >= 4:
        db = BookDatabase('books.db')
        title = sys.argv[2]
        author = sys.argv[3]
        publisher = sys.argv[4] if len(sys.argv) > 4 else ''
        book = Book(title=title, author=author, publisher=publisher)
        if db.add_book(book):
            print(f"Added: {title} by {author}")
        else:
            print(f"Already exists: {title}")

    elif cmd == 'search' and len(sys.argv) > 2:
        db = BookDatabase('books.db')
        query = ' '.join(sys.argv[2:])
        results = db.fuzzy_match_title(query, threshold=0.5, limit=10)
        if results:
            print(f"Results for '{query}':")
            for book, score in results:
                print(f"  [{score:.0%}] {book.title} - {book.author}")
        else:
            print("No matches found")

    elif cmd == 'add-imprint' and len(sys.argv) >= 4:
        db = BookDatabase('books.db')
        imprint = sys.argv[2]
        publisher = sys.argv[3]
        if db.add_imprint(imprint, publisher):
            print(f"Added: {imprint} -> {publisher}")
        else:
            print("Failed to add imprint")

    elif cmd == 'export' and len(sys.argv) > 2:
        db = BookDatabase('books.db')
        db.export_json(sys.argv[2])
        print(f"Exported to {sys.argv[2]}")

    elif cmd == 'import-json' and len(sys.argv) > 2:
        db = BookDatabase('books.db')
        added, skipped = db.import_json(sys.argv[2])
        print(f"Imported {added}, skipped {skipped}")

    else:
        print_usage()


if __name__ == "__main__":
    main()
