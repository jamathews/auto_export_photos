#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from datetime import datetime
import osxphotos

# --- CONFIG ---
# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD_DATE = "2025-10-09 00:00:00"
DEFAULT_EXPORT_BASE_DIR = "./Pictures"

def parse_args():
    parser = argparse.ArgumentParser(description='Export photos from Photos.app using osxphotos.')
    parser.add_argument('--threshold-date', default=DEFAULT_THRESHOLD_DATE,
                        help=f'Export photos taken since this date (default: {DEFAULT_THRESHOLD_DATE})')
    parser.add_argument('--export-dir', default=DEFAULT_EXPORT_BASE_DIR,
                        help=f'Base directory for exported photos (default: {DEFAULT_EXPORT_BASE_DIR})')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Increase verbosity level (-v for INFO, -vv for DEBUG)')
    return parser.parse_args()

def setup_logging(verbose_level):
    """Set up logging based on the verbosity level."""
    if verbose_level >= 3:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("DEBUG logging enabled")
    elif verbose_level == 2:
        logger.setLevel(logging.INFO)
        logging.getLogger().setLevel(logging.INFO)
        logger.info("INFO logging enabled")
    elif verbose_level == 1:
        logger.setLevel(logging.WARNING)
        logging.getLogger().setLevel(logging.WARNING)
        logger.info("WARNING logging enabled")
    elif verbose_level == 0:
        logger.setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.ERROR)
        logger.info("ERROR logging enabled")
    else:
        logger.setLevel(logging.CRITICAL)
        logging.getLogger().setLevel(logging.CRITICAL)
        logger.info("CRITICAL logging enabled")

def parse_threshold_date(date_str):
    """Parse the threshold date string into a timezone-aware datetime object."""
    try:
        # Parse the date and make it timezone-aware with local timezone
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.astimezone()  # Add local timezone
        return dt
    except ValueError:
        try:
            # Parse the date and make it timezone-aware with local timezone
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            if dt.tzinfo is None:
                dt = dt.astimezone()  # Add local timezone
            return dt
        except ValueError as e:
            logger.error(f"Invalid threshold date format: {date_str}. Expected format: YYYY-MM-DD HH:MM:SS")
            sys.exit(1)

def get_export_path(photo_date, base_dir):
    """Generate export path based on photo date: ./Pictures/yyyy/mm/yyyy-mm-dd"""
    year = photo_date.year
    month = photo_date.month
    day = photo_date.day

    # Create directory structure: ./Pictures/yyyy/mm/yyyy-mm-dd
    date_dir = f"{year:04d}-{month:02d}-{day:02d}"
    export_path = os.path.join(base_dir, f"{year:04d}", f"{month:02d}", date_dir)

    # Ensure the directory exists
    os.makedirs(export_path, exist_ok=True)

    return export_path

def export_photos(threshold_date, export_base_dir):
    """Export photos from Photos.app that were taken since the threshold date."""
    logger.info(f"Exporting photos taken since {threshold_date}")

    # Initialize osxphotos PhotosDB
    try:
        photosdb = osxphotos.PhotosDB()
    except Exception as e:
        logger.error(f"Error accessing Photos library: {e}")
        sys.exit(1)

    # Get all photos from the library
    photos = photosdb.photos()
    logger.info(f"Found {len(photos)} total photos in library")

    # Filter photos by date
    filtered_photos = [p for p in photos if p.date >= threshold_date]
    logger.info(f"Found {len(filtered_photos)} photos taken since {threshold_date}")

    # Export photos
    exported_count = 0
    for photo in filtered_photos:
        try:
            # Get photo date
            photo_date = photo.date

            # Generate export path
            export_path = get_export_path(photo_date, export_base_dir)

            # Get base filename without extension
            filename_base, filename_ext = os.path.splitext(photo.original_filename)

            # Export original version
            photo.export(filename=f"{filename_base}_original{filename_ext}", dest=export_path, use_photos_export=False, edited=False, live_photo=False, raw_photo=False)

            # Export edited version (if edits exist)
            if photo.hasadjustments:
                photo.export(filename=f"{filename_base}_edited{filename_ext}", dest=export_path, use_photos_export=False, edited=True, live_photo=False, raw_photo=False)

            # Try to export raw version
            try:
                photo.export(filename=f"{filename_base}_raw{filename_ext}", dest=export_path, use_photos_export=False, edited=False, live_photo=False, raw_photo=True)
            except Exception as e:
                logger.debug(f"Could not export raw photo for {photo.filename}: {e}")

            # Try to export live version
            try:
                photo.export(filename=f"{filename_base}_live{filename_ext}", dest=export_path, use_photos_export=False, edited=False, live_photo=True, raw_photo=False)
            except Exception as e:
                logger.debug(f"Could not export live photo for {photo.filename}: {e}")

            exported_count += 1
            if exported_count % 10 == 0:
                logger.info(f"Exported {exported_count}/{len(filtered_photos)} photos")

        except Exception as e:
            logger.error(f"Error exporting photo {photo.filename}: {e}")

    logger.info(f"Successfully exported {exported_count} photos")

def main():
    args = parse_args()

    # Set up logging based on verbosity
    setup_logging(args.verbose)

    # Parse threshold date
    threshold_date = parse_threshold_date(args.threshold_date)
    logger.info(f"Using threshold date: {threshold_date}")

    # Export photos
    export_photos(threshold_date, args.export_dir)

    logger.info("Export completed successfully")

if __name__ == "__main__":
    main()
