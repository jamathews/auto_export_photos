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
    parser = argparse.ArgumentParser(description='Export photos and videos from Photos.app using osxphotos.')
    parser.add_argument('--threshold-date', default=DEFAULT_THRESHOLD_DATE,
                        help=f'Export photos and videos taken since this date (default: {DEFAULT_THRESHOLD_DATE})')
    parser.add_argument('--export-dir', default=DEFAULT_EXPORT_BASE_DIR,
                        help=f'Base directory for exported photos and videos (default: {DEFAULT_EXPORT_BASE_DIR})')
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

def export_original(item, export_path, filename_base, filename_ext, is_video, media_type):
    """Export the original version of a media item."""
    original_filename = f"{filename_base}_original{filename_ext}"
    original_path = os.path.join(export_path, original_filename)

    if os.path.exists(original_path):
        logger.debug(f"Skipping export of original {media_type} {original_filename} - file already exists")
        return (0, 1)  # (exported, skipped)
    else:
        if is_video:
            item.export(filename=original_filename, dest=export_path, use_photos_export=True)
        else:
            item.export(filename=original_filename, dest=export_path, use_photos_export=False, edited=False, live_photo=False, raw_photo=False)
        return (1, 0)  # (exported, skipped)

def export_edited(item, export_path, filename_base, filename_ext, media_type):
    """Export the edited version of a media item if edits exist."""
    if not item.hasadjustments:
        return (0, 0)  # (exported, skipped) - No export attempted

    edited_filename = f"{filename_base}_edited{filename_ext}"
    edited_path = os.path.join(export_path, edited_filename)

    if os.path.exists(edited_path):
        logger.debug(f"Skipping export of edited {media_type} {edited_filename} - file already exists")
        return (0, 1)  # (exported, skipped)
    else:
        item.export(filename=edited_filename, dest=export_path, use_photos_export=False, edited=True, live_photo=False, raw_photo=False)
        return (1, 0)  # (exported, skipped)

def export_raw(item, export_path, filename_base, filename_ext, is_photo, is_video):
    """Export the raw version of a photo if it has a raw version."""
    if not is_photo:
        if is_video:
            logger.debug(f"Skipping export of raw version for video {item.filename} - not applicable for videos")
        return (0, 0)  # (exported, skipped) - No export attempted

    if not (item.has_raw or item.israw):
        logger.debug(f"Skipping export of raw photo for {item.filename} - no raw version available")
        return (0, 0)  # (exported, skipped) - No export attempted

    raw_filename = f"{filename_base}_raw{filename_ext}"
    raw_path = os.path.join(export_path, raw_filename)

    if os.path.exists(raw_path):
        logger.debug(f"Skipping export of raw photo {raw_filename} - file already exists")
        return (0, 1)  # (exported, skipped)
    else:
        try:
            item.export(filename=raw_filename, dest=export_path, use_photos_export=False, edited=False, live_photo=False, raw_photo=True)
            return (1, 0)  # (exported, skipped)
        except Exception as e:
            logger.debug(f"Could not export raw photo for {item.filename}: {e}")
            return (0, 0)  # (exported, skipped) - Export failed

def export_live(item, export_path, filename_base, filename_ext, is_photo, is_video):
    """Export the live version of a photo."""
    if not is_photo:
        if is_video:
            logger.debug(f"Skipping export of live version for video {item.filename} - not applicable for videos")
        return (0, 0)  # (exported, skipped) - No export attempted

    live_filename = f"{filename_base}_live{filename_ext}"
    live_path = os.path.join(export_path, live_filename)

    if os.path.exists(live_path):
        logger.debug(f"Skipping export of live photo {live_filename} - file already exists")
        return (0, 1)  # (exported, skipped)
    else:
        try:
            item.export(filename=live_filename, dest=export_path, use_photos_export=False, edited=False, live_photo=True, raw_photo=False)
            return (1, 0)  # (exported, skipped)
        except Exception as e:
            logger.debug(f"Could not export live photo for {item.filename}: {e}")
            return (0, 0)  # (exported, skipped) - Export failed

def export_media(threshold_date, export_base_dir):
    """Export photos and videos from Photos.app that were taken since the threshold date."""
    logger.info(f"Exporting photos and videos taken since {threshold_date}")

    # Initialize osxphotos PhotosDB
    try:
        photosdb = osxphotos.PhotosDB()
    except Exception as e:
        logger.error(f"Error accessing Photos library: {e}")
        sys.exit(1)

    # Get all media (photos and videos) from the library
    media_items = photosdb.photos()
    logger.info(f"Found {len(media_items)} total media items in library")

    # Filter media by date
    filtered_media = [p for p in media_items if p.date >= threshold_date]
    logger.info(f"Found {len(filtered_media)} media items taken since {threshold_date}")

    # Count photos and videos
    photos_count = sum(1 for p in filtered_media if p.isphoto)
    videos_count = sum(1 for p in filtered_media if p.ismovie)
    logger.info(f"Media breakdown: {photos_count} photos and {videos_count} videos")

    # Export media items (photos and videos)
    exported_count = 0
    skipped_count = 0
    processed_count = 0
    for item in filtered_media:
        try:
            # Get media date
            item_date = item.date

            # Generate export path
            export_path = get_export_path(item_date, export_base_dir)

            # Get base filename without extension
            filename_base, filename_ext = os.path.splitext(item.original_filename)

            # Determine if this is a photo or video
            is_photo = item.isphoto
            is_video = item.ismovie
            media_type = "photo" if is_photo else "video" if is_video else "unknown"

            # Export each version
            original_exported, original_skipped = export_original(item, export_path, filename_base, filename_ext, is_video, media_type)
            edited_exported, edited_skipped = export_edited(item, export_path, filename_base, filename_ext, media_type)
            raw_exported, raw_skipped = export_raw(item, export_path, filename_base, filename_ext, is_photo, is_video)
            live_exported, live_skipped = export_live(item, export_path, filename_base, filename_ext, is_photo, is_video)

            # Accumulate counts
            exported_count += original_exported + edited_exported + raw_exported + live_exported
            skipped_count += original_skipped + edited_skipped + raw_skipped + live_skipped

            processed_count += 1
            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count}/{len(filtered_media)} media items, exported {exported_count} files")

        except Exception as e:
            logger.error(f"Error exporting {media_type} {item.filename}: {e}")

    logger.info(f"Successfully exported {exported_count} files from {processed_count} media items, skipped {skipped_count} already existing files")

def main():
    args = parse_args()

    # Set up logging based on verbosity
    setup_logging(args.verbose)

    # Parse threshold date
    threshold_date = parse_threshold_date(args.threshold_date)
    logger.info(f"Using threshold date: {threshold_date}")

    # Export photos and videos
    export_media(threshold_date, args.export_dir)

    logger.info("Export completed successfully")

if __name__ == "__main__":
    main()
