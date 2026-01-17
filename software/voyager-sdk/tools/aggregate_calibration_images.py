#!/usr/bin/env python3
# Copyright Axelera AI, 2025
# Script to aggregate calibration images from multiple text files into a zip file

import argparse
import logging
import os
from pathlib import Path
import shutil
from typing import List, Set
import zipfile

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)


def read_calibration_images_from_file(file_path: Path) -> Set[str]:
    """Read image paths from a calibration images text file.

    Args:
        file_path: Path to the text file containing image paths

    Returns:
        Set of unique image paths
    """
    image_paths = set()
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    image_paths.add(line)
        LOG.info(f"Read {len(image_paths)} image paths from {file_path}")
    except Exception as e:
        LOG.error(f"Error reading {file_path}: {e}")

    return image_paths


def find_calibration_files(
    directory: Path, pattern: str = "*calibration_images.txt"
) -> List[Path]:
    """Find all calibration images text files in a directory.

    Args:
        directory: Directory to search in
        pattern: File pattern to match

    Returns:
        List of paths to calibration images files
    """
    files = list(directory.glob(pattern))
    LOG.info(f"Found {len(files)} calibration image files in {directory}")
    return files


def aggregate_images_from_files(calibration_files: List[Path]) -> Set[str]:
    """Aggregate unique image paths from multiple calibration files.

    Args:
        calibration_files: List of paths to calibration image files

    Returns:
        Set of all unique image paths
    """
    all_images = set()

    for file_path in calibration_files:
        images = read_calibration_images_from_file(file_path)
        all_images.update(images)

    LOG.info(f"Total unique images across all files: {len(all_images)}")
    return all_images


def copy_images_to_zip(
    image_paths: Set[str], output_zip: Path, preserve_structure: bool = True
) -> int:
    """Copy images to a zip file.

    Args:
        image_paths: Set of image paths to copy
        output_zip: Path to the output zip file
        preserve_structure: Whether to preserve directory structure in the zip

    Returns:
        Number of successfully copied images
    """
    successful_copies = 0
    failed_copies = 0

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img_path in image_paths:
            img_path_obj = Path(img_path)

            if not img_path_obj.exists():
                LOG.warning(f"Image not found: {img_path}")
                failed_copies += 1
                continue

            try:
                if preserve_structure:
                    # Keep the full path structure in the zip
                    arcname = str(img_path_obj)
                else:
                    # Just use the filename
                    arcname = img_path_obj.name

                # Avoid duplicate filenames when not preserving structure
                if not preserve_structure:
                    counter = 1
                    original_arcname = arcname
                    while arcname in [info.filename for info in zf.infolist()]:
                        name_parts = original_arcname.rsplit('.', 1)
                        if len(name_parts) == 2:
                            arcname = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                        else:
                            arcname = f"{original_arcname}_{counter}"
                        counter += 1

                zf.write(img_path_obj, arcname)
                successful_copies += 1

                if successful_copies % 100 == 0:
                    LOG.info(f"Copied {successful_copies} images...")

            except Exception as e:
                LOG.error(f"Error copying {img_path}: {e}")
                failed_copies += 1

    LOG.info(f"Successfully copied {successful_copies} images to {output_zip}")
    if failed_copies > 0:
        LOG.warning(f"Failed to copy {failed_copies} images")

    return successful_copies


def create_image_list_file(image_paths: Set[str], output_file: Path) -> None:
    """Create a text file with all unique image paths.

    Args:
        image_paths: Set of image paths
        output_file: Path to the output text file
    """
    try:
        with open(output_file, 'w') as f:
            for img_path in sorted(image_paths):
                f.write(f"{img_path}\n")
        LOG.info(f"Created image list file: {output_file}")
    except Exception as e:
        LOG.error(f"Error creating image list file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate calibration images from multiple text files into a zip file"
    )
    parser.add_argument(
        "input_dir", type=str, help="Directory containing calibration images text files"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="aggregated_calibration_images.zip",
        help="Output zip file path (default: aggregated_calibration_images.zip)",
    )
    parser.add_argument(
        "-p",
        "--pattern",
        type=str,
        default="*calibration_images.txt",
        help="File pattern to match (default: *calibration_images.txt)",
    )
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        default=True,
        help="Preserve directory structure in zip (default: false)",
    )
    parser.add_argument(
        "--create-list",
        action="store_true",
        help="Also create a text file with all unique image paths",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_dir = Path(args.input_dir)
    output_zip = Path(args.output)

    # Validate input directory
    if not input_dir.exists():
        LOG.error(f"Input directory does not exist: {input_dir}")
        return 1

    if not input_dir.is_dir():
        LOG.error(f"Input path is not a directory: {input_dir}")
        return 1

    # Find calibration files
    calibration_files = find_calibration_files(input_dir, args.pattern)

    if not calibration_files:
        LOG.error(f"No calibration files found matching pattern '{args.pattern}' in {input_dir}")
        return 1

    # Aggregate image paths
    all_images = aggregate_images_from_files(calibration_files)

    if not all_images:
        LOG.error("No images found in any calibration files")
        return 1

    # Create output directory if it doesn't exist
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    # Copy images to zip
    copied_count = copy_images_to_zip(all_images, output_zip, args.preserve_structure)

    if copied_count == 0:
        LOG.error("No images were successfully copied")
        return 1

    # Create image list file if requested
    if args.create_list:
        list_file = output_zip.with_suffix('.txt')
        create_image_list_file(all_images, list_file)

    LOG.info(f"Successfully created aggregated zip: {output_zip}")
    LOG.info(f"Total files processed: {len(calibration_files)}")
    LOG.info(f"Unique images found: {len(all_images)}")
    LOG.info(f"Images successfully copied: {copied_count}")

    return 0


if __name__ == "__main__":
    exit(main())
