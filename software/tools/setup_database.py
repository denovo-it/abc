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
    python3 setup_database.py create-fts          # Build FTS5 full-text index
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

    def __init__(self, db_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "books.db")):
        self.db_path = db_path
        self._init_db()
        # Caches for fast lookups
        self._authors_cache = None
        self._publishers_cache = None
        self._imprints_cache = None
        self._has_fts_cache = None
        # Persistent read-only connection for queries (avoids repeated connect on 18GB DB)
        self._read_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._read_conn.execute("PRAGMA query_only = ON")
        self._read_conn.execute("PRAGMA mmap_size = 268435456")  # 256MB mmap for faster reads
        self._read_conn.execute("PRAGMA case_sensitive_like = ON")  # Enable index use for LIKE prefix%

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
        """
        Fuzzy match title against database (memory efficient).
        Uses SQL queries (FTS5 + LIKE) to narrow candidates, then scores with SequenceMatcher.
        """
        query_norm = self.normalize(query)
        if not query_norm:
            return []

        candidates = []

        # Strategy 1: FTS5 keyword search (fastest, best recall)
        words = query_norm.split()
        if self.has_fts_index() and words:
            fts_results = self.search_title_fts(words, limit=100)
            candidates.extend(fts_results)

        # Strategy 2: LIKE prefix on first significant word
        sig_words = [w for w in words if len(w) >= 3]
        if sig_words:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA case_sensitive_like = ON")
            cursor = conn.cursor()
            for word in sig_words[:2]:
                cursor.execute('''
                    SELECT id, title, title_normalized, author, author_normalized,
                           publisher, isbn, year, language
                    FROM books WHERE title_normalized LIKE ?
                    LIMIT 50
                ''', (f'{word}%',))
                candidates.extend(cursor.fetchall())
            # Also try full prefix
            prefix = ' '.join(sig_words[:3])
            cursor.execute('''
                SELECT id, title, title_normalized, author, author_normalized,
                       publisher, isbn, year, language
                FROM books WHERE title_normalized LIKE ?
                LIMIT 50
            ''', (f'{prefix}%',))
            candidates.extend(cursor.fetchall())
            conn.close()

        # Deduplicate by id
        seen = set()
        unique = []
        for row in candidates:
            if isinstance(row, tuple) and len(row) >= 9 and row[0] not in seen:
                seen.add(row[0])
                unique.append(row)

        # Score with SequenceMatcher
        matches = []
        for row in unique:
            ratio = SequenceMatcher(None, query_norm, row[2]).ratio()
            if ratio >= threshold:
                book = Book(title=row[1], author=row[3], publisher=row[5],
                           isbn=row[6], year=row[7], language=row[8])
                matches.append((book, ratio))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]

    def fuzzy_match_words(self, words: List[str], threshold: float = 0.7, limit: int = 5) -> List[Tuple[Book, float]]:
        """
        Match OCR words against book titles (memory efficient).
        Uses SQL queries (FTS5 + LIKE) to narrow candidates, then scores.
        """
        combined = ' '.join(words)
        combined_norm = self.normalize(combined)
        if not combined_norm:
            return []

        stopwords = {'the', 'a', 'an', 'of', 'and', 'in', 'on', 'at', 'to',
                      'il', 'la', 'lo', 'gli', 'le', 'di', 'da'}

        # Clean words for search
        sig_words = [w for w in combined_norm.split() if len(w) >= 3 and w not in stopwords]
        if not sig_words:
            return []

        candidates = []

        # Strategy 1: FTS5 keyword search
        if self.has_fts_index():
            fts_results = self.search_title_fts(sig_words, limit=100)
            candidates.extend(fts_results)

        # Strategy 2: LIKE prefix on individual significant words (indexed with case_sensitive_like)
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA case_sensitive_like = ON")
        cursor = conn.cursor()
        for word in sig_words[:3]:
            cursor.execute('''
                SELECT id, title, title_normalized, author, author_normalized,
                       publisher, isbn, year, language
                FROM books WHERE title_normalized LIKE ?
                LIMIT 50
            ''', (f'{word}%',))
            candidates.extend(cursor.fetchall())
        conn.close()

        # Deduplicate by id
        seen = set()
        unique = []
        for row in candidates:
            if isinstance(row, tuple) and len(row) >= 9 and row[0] not in seen:
                seen.add(row[0])
                unique.append(row)

        # Score candidates
        query_words = set(combined_norm.split()) - stopwords
        matches = []

        for row in unique:
            title_norm = row[2]

            # Direct similarity
            ratio1 = SequenceMatcher(None, combined_norm, title_norm).ratio()

            # Word overlap (order-independent)
            title_words = set(title_norm.split()) - stopwords
            if title_words and query_words:
                overlap = len(title_words & query_words)
                ratio2 = overlap / len(title_words)
            else:
                ratio2 = 0

            best_ratio = max(ratio1, ratio2)

            if best_ratio >= threshold:
                book = Book(title=row[1], author=row[3], publisher=row[5],
                           isbn=row[6], year=row[7], language=row[8])
                matches.append((book, best_ratio))

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
        """Check if author is known (SQL query, no memory load)"""
        if not name:
            return False
        cursor = self._read_conn.cursor()
        name_norm = self.normalize(name)
        cursor.execute('SELECT 1 FROM authors WHERE name_normalized = ? LIMIT 1', (name_norm,))
        return cursor.fetchone() is not None

    def search_author(self, name: str, limit: int = 5) -> List[str]:
        """Search authors by name (SQL LIKE query)"""
        if not name or len(name) < 2:
            return []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        name_norm = self.normalize(name)
        cursor.execute(
            'SELECT name FROM authors WHERE name_normalized LIKE ? ORDER BY book_count DESC LIMIT ?',
            (f'%{name_norm}%', limit)
        )
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def fuzzy_match_author_sql(self, name: str, threshold: float = 0.8) -> Optional[str]:
        """
        Fuzzy match author name using SQL (memory efficient).
        Returns best match if above threshold, None otherwise.
        """
        if not name or len(name) < 3:
            return None

        cursor = self._read_conn.cursor()
        name_norm = self.normalize(name)

        # First try exact match (uses idx_author_name)
        cursor.execute('SELECT name FROM authors WHERE name_normalized = ? LIMIT 1', (name_norm,))
        result = cursor.fetchone()
        if result:
            return result[0]

        # Try prefix match for OCR errors at end of word (uses idx_author_name with case_sensitive_like)
        if len(name_norm) >= 4:
            prefix = name_norm[:len(name_norm)-1]
            cursor.execute(
                'SELECT name FROM authors WHERE name_normalized LIKE ? ORDER BY book_count DESC LIMIT 10',
                (f'{prefix}%',)
            )
            candidates = cursor.fetchall()
            name_upper = name.upper()
            for (candidate,) in candidates:
                ratio = SequenceMatcher(None, name_upper, candidate.upper()).ratio()
                if ratio >= threshold:
                    return candidate

        return None

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
        """Check if publisher is known (SQL query, no memory load)"""
        if not name:
            return False
        cursor = self._read_conn.cursor()
        name_norm = self.normalize(name)
        cursor.execute('SELECT 1 FROM publishers WHERE name_normalized = ? LIMIT 1', (name_norm,))
        return cursor.fetchone() is not None

    def search_publisher(self, name: str, limit: int = 5) -> List[str]:
        """Search publishers by name (SQL LIKE query)"""
        if not name or len(name) < 2:
            return []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        name_norm = self.normalize(name)
        cursor.execute(
            'SELECT name FROM publishers WHERE name_normalized LIKE ? ORDER BY book_count DESC LIMIT ?',
            (f'%{name_norm}%', limit)
        )
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def fuzzy_match_publisher_sql(self, name: str, threshold: float = 0.8) -> Optional[str]:
        """
        Fuzzy match publisher name using SQL (memory efficient).
        Returns best match if above threshold, None otherwise.
        """
        if not name or len(name) < 3:
            return None

        cursor = self._read_conn.cursor()
        name_norm = self.normalize(name)

        # First try exact match (uses idx_publisher_name)
        cursor.execute('SELECT name FROM publishers WHERE name_normalized = ? LIMIT 1', (name_norm,))
        result = cursor.fetchone()
        if result:
            return result[0]

        # Try prefix match for OCR errors at end of word (uses idx_publisher_name with case_sensitive_like)
        if len(name_norm) >= 4:
            prefix = name_norm[:len(name_norm)-1]
            cursor.execute(
                'SELECT name FROM publishers WHERE name_normalized LIKE ? ORDER BY book_count DESC LIMIT 10',
                (f'{prefix}%',)
            )
            candidates = cursor.fetchall()
            name_upper = name.upper()
            for (candidate,) in candidates:
                ratio = SequenceMatcher(None, name_upper, candidate.upper()).ratio()
                if ratio >= threshold:
                    return candidate

        return None

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
    # FTS5 FULL-TEXT SEARCH
    # =========================================================================

    def _create_fts_index(self):
        """
        Create FTS5 virtual table on title_normalized for fast keyword search.
        One-time operation (~20-40 min on 55M rows). Idempotent.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if FTS table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books_fts'")
        if cursor.fetchone():
            print("FTS5 index already exists. Rebuilding...")
            cursor.execute("DROP TABLE books_fts")

        print("Creating FTS5 virtual table...")
        cursor.execute('''
            CREATE VIRTUAL TABLE books_fts USING fts5(
                title_normalized,
                content='books',
                content_rowid='id'
            )
        ''')

        print("Populating FTS5 index (this may take a while)...")
        cursor.execute('''
            INSERT INTO books_fts(rowid, title_normalized)
            SELECT id, title_normalized FROM books
        ''')

        conn.commit()
        conn.close()
        print("FTS5 index created successfully.")

    def has_fts_index(self) -> bool:
        """Check if FTS5 index exists (cached)"""
        if self._has_fts_cache is not None:
            return self._has_fts_cache
        cursor = self._read_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books_fts'")
        self._has_fts_cache = cursor.fetchone() is not None
        return self._has_fts_cache

    def search_title_fts(self, words: List[str], limit: int = 50,
                         use_and: bool = False) -> List[Tuple]:
        """
        Fast FTS5 keyword search on title_normalized.
        use_and=True: all words must match (high precision)
        use_and=False: any word matches (broad recall)
        """
        if not words:
            return []

        cursor = self._read_conn.cursor()

        # Build FTS5 query: each word as prefix match
        fts_terms = []
        for w in words:
            w_clean = re.sub(r'[^\w]', '', w.lower())
            if len(w_clean) >= 3:
                fts_terms.append(f'"{w_clean}"*')

        if not fts_terms:
            return []

        joiner = ' AND ' if use_and else ' OR '
        fts_query = joiner.join(fts_terms)

        try:
            cursor.execute('''
                SELECT b.id, b.title, b.title_normalized, b.author, b.author_normalized,
                       b.publisher, b.isbn, b.year, b.language
                FROM books_fts f
                JOIN books b ON b.id = f.rowid
                WHERE books_fts MATCH ?
                LIMIT ?
            ''', (fts_query, limit))
            results = cursor.fetchall()
        except Exception:
            results = []

        return results

    # =========================================================================
    # BOOK IDENTIFICATION (CASCADING SEARCH)
    # =========================================================================

    def identify_book(self, title: str, author: str, publisher: str,
                      raw_words: List[str], language: str = None) -> dict:
        """
        Identify a book from OCR data using progressive refinement.

        Strategy:
        1. Author exact match by name (indexed)
        2. Author + title prefix (indexed)
        3. FTS5 keyword search on raw OCR words
        4. Resolve author name → OL key via FTS candidates, then expand search
        5. Score all candidates with title + author + publisher + raw_words

        Returns: {matched, book, match_confidence, alternatives}
        """
        result = {
            'matched': False,
            'book': None,
            'match_confidence': 0.0,
            'alternatives': []
        }

        title_norm = self.normalize(title) if title and title != '[not identified]' else ''
        author_norm = self.normalize(author) if author and author != '[not identified]' else ''
        publisher_norm = self.normalize(publisher) if publisher and publisher != '[not identified]' else ''

        # Clean raw words (for FTS and scoring)
        raw_words_clean = [w.lower() for w in raw_words if len(w) >= 3]

        # Collect all author name candidates (parsed author + cross-field from publisher)
        author_candidates = []
        if author_norm:
            author_candidates.append(author_norm)
        if publisher_norm and publisher_norm != author_norm:
            author_candidates.append(publisher_norm)

        candidates = set()

        def _add_rows(rows):
            for r in rows:
                if isinstance(r, tuple) and len(r) >= 9:
                    candidates.add(r)

        cursor = self._read_conn.cursor()

        # --- Step 1: Author exact match by name (indexed, instant) ---
        for auth in author_candidates:
            cursor.execute('''
                SELECT id, title, title_normalized, author, author_normalized,
                       publisher, isbn, year, language
                FROM books WHERE author_normalized = ? LIMIT 50
            ''', (auth,))
            _add_rows(cursor.fetchall())

        # --- Step 2: Author + title prefix (indexed, instant) ---
        title_words = title_norm.split() if title_norm else []
        for auth in author_candidates:
            if title_words:
                _add_rows(self._search_author_title(auth, title_norm))
                for tw in title_words:
                    if len(tw) >= 4:
                        _add_rows(self._search_author_title(auth, tw))

        # --- Step 3: FTS5 keyword search (fast, broad recall) ---
        sig_words = [w for w in raw_words_clean if len(w) >= 4]
        if raw_words_clean and self.has_fts_index():
            from itertools import combinations
            if len(sig_words) >= 2:
                for w1, w2 in combinations(sig_words[:8], 2):
                    _add_rows(self.search_title_fts([w1, w2], limit=30, use_and=True))
            if len(candidates) < 5:
                _add_rows(self.search_title_fts(sig_words[:5], limit=50, use_and=False))

        # --- Step 4: Resolve author OL key from FTS candidates ---
        # Books in the DB have OL keys as author (e.g. "OL30765A" = Rick Riordan).
        # Infer the OL key by finding the most common author among FTS candidates,
        # then search for more books by that author + our keywords.
        resolved_ol_keys = set()
        if candidates and author_norm:
            from collections import Counter
            author_counter = Counter()
            for row in candidates:
                auth_val = row[4]  # author_normalized
                if self._OL_KEY_RE.match(auth_val):
                    author_counter[auth_val] += 1
            # Use the top OL keys (most common among candidates)
            for ol_key, count in author_counter.most_common(3):
                if count >= 2 or len(author_counter) == 1:
                    resolved_ol_keys.add(ol_key)

            # Search for more books by resolved OL keys + title keywords
            for ol_key in resolved_ol_keys:
                cursor.execute('''
                    SELECT id, title, title_normalized, author, author_normalized,
                           publisher, isbn, year, language
                    FROM books WHERE author_normalized = ? LIMIT 100
                ''', (ol_key,))
                _add_rows(cursor.fetchall())
                # Also try OL key + title keyword prefix
                for tw in sig_words[:5]:
                    if len(tw) >= 4:
                        _add_rows(self._search_author_title(ol_key, tw))

        # --- Step 5: Publisher-filtered FTS (if publisher is known) ---
        # Use publisher as additional filter to prefer local editions
        if publisher_norm and candidates:
            publisher_filtered = [
                r for r in candidates
                if publisher_norm in self.normalize(r[5] or '')
            ]
            # If we have publisher-filtered results, give them priority later in scoring

        # --- Language filter (if specified) ---
        if language:
            candidates = {r for r in candidates if r[8] == language}

        if not candidates:
            return result

        # --- Step 6: Score all candidates ---
        scored = []
        for row in candidates:
            book = Book(
                title=row[1], author=row[3], publisher=row[5],
                isbn=row[6], year=row[7], language=row[8]
            )
            score = self._score_match(
                book, title_norm, author_norm, publisher_norm, raw_words_clean,
                resolved_ol_keys=resolved_ol_keys
            )
            if score > 0.20:
                scored.append((book, score))

        if not scored:
            return result

        scored.sort(key=lambda x: x[1], reverse=True)

        best_book, best_score = scored[0]
        result['matched'] = best_score >= 0.40
        result['book'] = best_book
        result['match_confidence'] = best_score
        result['alternatives'] = scored[1:4]

        # Replace OL key author with the human-readable OCR name
        if author_norm and result['book']:
            if self._OL_KEY_RE.match(self.normalize(result['book'].author)):
                result['book'].author = author
            for alt_book, _ in result['alternatives']:
                if self._OL_KEY_RE.match(self.normalize(alt_book.author)):
                    alt_book.author = author

        return result

    def _search_author_title(self, author_norm: str, title_norm: str,
                              limit: int = 20) -> List[Tuple]:
        """Search by exact author + title prefix (both indexed, instant)"""
        cursor = self._read_conn.cursor()

        title_prefix = title_norm.split()[0] if title_norm else ''
        if not title_prefix or len(title_prefix) < 3:
            return []

        cursor.execute('''
            SELECT id, title, title_normalized, author, author_normalized,
                   publisher, isbn, year, language
            FROM books
            WHERE author_normalized = ? AND title_normalized LIKE ?
            LIMIT ?
        ''', (author_norm, f'{title_prefix}%', limit))

        return cursor.fetchall()

    _OL_KEY_RE = re.compile(r'^ol\d+a$', re.IGNORECASE)

    def _score_match(self, book: 'Book', title_norm: str, author_norm: str,
                     publisher_norm: str, raw_words: List[str],
                     resolved_ol_keys: Set[str] = None) -> float:
        """
        Score a candidate book match.

        When book author is an OL key, checks if it matches a resolved key
        (from FTS candidate analysis). This bridges OCR author names to OL keys.

        Weights: raw_words 0.40, title 0.15, author 0.20, publisher 0.25
        OL key:  raw_words 0.50, title 0.15, author(resolved) 0.10, publisher 0.25
        """
        score = 0.0
        book_title_norm = self.normalize(book.title)
        book_author_norm = self.normalize(book.author)
        book_publisher_norm = self.normalize(book.publisher)

        # Check if book author is an OL key (not a real name)
        author_is_ol_key = bool(self._OL_KEY_RE.match(book_author_norm))

        # Check if OL key matches our resolved keys (author name → OL key bridge)
        ol_key_matched = (resolved_ol_keys and book_author_norm in resolved_ol_keys)

        if author_is_ol_key:
            if ol_key_matched:
                # We resolved the author: OL key match acts as author confirmation
                w_title, w_raw, w_author, w_publisher = 0.15, 0.45, 0.15, 0.25
            else:
                w_title, w_raw, w_author, w_publisher = 0.15, 0.55, 0.0, 0.30
        else:
            w_title, w_raw, w_author, w_publisher = 0.15, 0.35, 0.20, 0.30

        # --- Title similarity (parsed title - may be inaccurate from OCR) ---
        if title_norm and book_title_norm:
            title_sim = SequenceMatcher(None, title_norm, book_title_norm).ratio()
            score += title_sim * w_title

        # --- Raw words overlap with book title (most reliable signal) ---
        if raw_words and book_title_norm:
            book_title_words = set(book_title_norm.split())
            book_sig_words = {w for w in book_title_words if len(w) >= 3}
            # Exclude author/publisher words from raw_words for title matching
            exclude_words = set()
            if author_norm:
                exclude_words |= set(author_norm.split())
            if publisher_norm:
                exclude_words |= set(publisher_norm.split())
            raw_title_words = set(raw_words) - exclude_words
            if book_sig_words and raw_title_words:
                overlap = len(book_sig_words & raw_title_words)
                overlap_ratio = overlap / len(book_sig_words)
                abs_bonus = min(overlap / 3.0, 1.0)
                combined = overlap_ratio * 0.5 + abs_bonus * 0.5
                score += combined * w_raw

        # --- Author match ---
        if w_author > 0:
            if ol_key_matched:
                # OL key resolved and matches → full author score
                score += 1.0 * w_author
            elif author_norm and book_author_norm:
                author_sim = SequenceMatcher(None, author_norm, book_author_norm).ratio()
                score += author_sim * w_author
            elif publisher_norm and book_author_norm:
                cross_sim = SequenceMatcher(None, publisher_norm, book_author_norm).ratio()
                score += cross_sim * (w_author * 0.8)

        # --- Publisher match ---
        if publisher_norm and book_publisher_norm:
            pub_sim = SequenceMatcher(None, publisher_norm, book_publisher_norm).ratio()
            score += pub_sim * w_publisher
        elif author_norm and book_publisher_norm:
            cross_sim = SequenceMatcher(None, author_norm, book_publisher_norm).ratio()
            score += cross_sim * (w_publisher * 0.7)

        return score

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


def cleanup_temp_files():
    """Remove temporary files created by database operations"""
    temp_files = ['download.log']
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def main():
    cleanup_temp_files()

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

    elif cmd == 'create-fts':
        db = BookDatabase('books.db')
        print("Building FTS5 full-text search index...")
        start = datetime.now()
        db._create_fts_index()
        elapsed = (datetime.now() - start).total_seconds()
        print(f"Done in {elapsed:.1f}s")

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

    cleanup_temp_files()


if __name__ == "__main__":
    main()
