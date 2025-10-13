#!/usr/bin/env python3
"""
Auto Export Photos - A tool for automatically exporting photos and videos from macOS Photos app.

Copyright (C) 2023 James Mathews

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

This script exports photos and videos from the macOS Photos app that were taken since a specified date.
It can export original, edited, raw, and live photo versions of media items, organizing them into
a directory structure based on the date the photo was taken (YYYY/MM/YYYY-MM-DD).

The script keeps track of the last export date in a file called 'last_export.txt' in the export directory,
which is used as the default threshold date for subsequent runs if no date is specified.

Usage:
    python export.py [--threshold-date YYYY-MM-DD] [--export-dir PATH] [-v]

Options:
    --threshold-date  Date to export photos from (default: read from last_export.txt or current date)
    --export-dir      Base directory for exported photos (default: ~/Pictures)
    -v, --verbose     Increase verbosity level (-v for WARNING, -vv for INFO, -vvv for DEBUG)
"""
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

DEFAULT_EXPORT_BASE_DIR = os.path.expanduser('~/Pictures')


def parse_args():
    """
    Parse command line arguments for the script.

    Returns:
        argparse.Namespace: An object containing the parsed command line arguments.
            - threshold_date: Date string to export photos from (default: None, read from last_export.txt or current date)
            - export_dir: Base directory for exported photos (default: ~/Pictures)
            - verbose: Integer indicating verbosity level (0=ERROR, 1=WARNING, 2=INFO, 3+=DEBUG)
    """
    parser = argparse.ArgumentParser(description='Export photos and videos from Photos.app using osxphotos.')
    parser.add_argument('--threshold-date', default=None,
                        help=f'Export photos and videos taken since this date (default: read from last_export.txt or now)')
    parser.add_argument('--export-dir', default=DEFAULT_EXPORT_BASE_DIR,
                        help=f'Base directory for exported photos and videos (default: {DEFAULT_EXPORT_BASE_DIR})')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Increase verbosity level (-v for WARNING, -vv for INFO, -vvv for DEBUG)')
    return parser.parse_args()


def setup_logging(verbose_level):
    """
    Set up logging based on the verbosity level.

    Configures the logging level for both the root logger and the script's logger
    based on the verbosity level specified in the command line arguments.

    Args:
        verbose_level (int): The verbosity level:
            - 0: ERROR (default)
            - 1: WARNING
            - 2: INFO
            - 3+: DEBUG (also enables osxphotos debug mode)
    """
    if verbose_level >= 3:
        osxphotos.set_debug(True)
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
    """
    Parse the threshold date string into a timezone-aware datetime object.

    Attempts to parse the date string using two different formats:
    1. ISO format (e.g., '2023-01-01T12:00:00')
    2. Custom format (e.g., '2023-01-01 12:00:00')

    If the parsed datetime is naive (has no timezone), the local timezone is added.

    Args:
        date_str (str): The date string to parse

    Returns:
        datetime: A timezone-aware datetime object

    Raises:
        SystemExit: If the date string cannot be parsed in either format
    """
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
    """
    Generate export path based on photo date.

    Creates a directory structure in the format: base_dir/yyyy/mm/yyyy-mm-dd
    For example: ~/Pictures/2023/01/2023-01-15

    The function ensures the directory exists, creating it if necessary.

    Args:
        photo_date (datetime): The date the photo was taken
        base_dir (str): The base directory for exports

    Returns:
        str: The full path to the export directory
    """
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
    """
    Export the original version of a media item.

    Exports the original version of a photo or video to the specified export path.
    Skips export if the file already exists or if the item has a raw version that will be exported separately.

    Args:
        item (osxphotos.PhotoInfo): The photo or video to export
        export_path (str): The directory to export to
        filename_base (str): The base filename without extension
        filename_ext (str): The file extension including the dot (e.g., '.jpg')
        is_video (bool): Whether the item is a video
        media_type (str): The type of media ('photo' or 'video')

    Returns:
        tuple: A tuple containing (exported_count, skipped_count)
            - exported_count (int): 1 if the file was exported, 0 otherwise
            - skipped_count (int): 1 if the file was skipped, 0 otherwise

    Raises:
        RuntimeError: If the export fails
    """
    original_filename = f"{filename_base}{filename_ext}"
    original_path = os.path.join(export_path, original_filename)

    if os.path.exists(original_path):
        logger.debug(f"Skipping export of original {media_type} {original_filename} - file already exists")
        return 0, 1  # (exported, skipped)
    else:
        try:
            if is_video:
                exported_files = item.export(filename=original_filename, dest=export_path, use_photos_export=True)
                if not exported_files:
                    error_msg = f"Failed to export original video {original_filename}"
                    log_export_error(os.path.dirname(export_path), item, original_filename, error_msg)
                    raise RuntimeError(error_msg)
            elif item.has_raw or item.israw:
                logger.debug(
                    f"Skipping export of original {media_type} {original_filename} - it will be exported as raw")
                return 0, 1  # (exported, skipped)
            else:
                # Note: We need separate calls to item.export() for each variation (original, edited, raw, live)
                # because we need different filenames for each variation, and item.export() only accepts a single filename.
                exported_files = item.export(filename=original_filename, dest=export_path, use_photos_export=True,
                                             edited=False, live_photo=False, raw_photo=False)
                if not exported_files:
                    error_msg = f"Failed to export original photo {original_filename}"
                    log_export_error(os.path.dirname(export_path), item, original_filename, error_msg)
                    raise RuntimeError(error_msg)
            return 1, 0  # (exported, skipped)
        except Exception as e:
            if not isinstance(e, RuntimeError):  # Only log if not already logged
                log_export_error(os.path.dirname(export_path), item, original_filename, str(e))
            raise


def export_edited(item, export_path, filename_base, filename_ext, media_type):
    """
    Export the edited version of a media item if edits exist.

    Exports the edited version of a photo or video to the specified export path
    if the item has adjustments (edits). Skips export if the file already exists.

    Args:
        item (osxphotos.PhotoInfo): The photo or video to export
        export_path (str): The directory to export to
        filename_base (str): The base filename without extension
        filename_ext (str): The file extension including the dot (e.g., '.jpg')
        media_type (str): The type of media ('photo' or 'video')

    Returns:
        tuple: A tuple containing (exported_count, skipped_count)
            - exported_count (int): 1 if the file was exported, 0 otherwise
            - skipped_count (int): 1 if the file was skipped, 0 otherwise

    Raises:
        RuntimeError: If the export fails
    """
    if not item.hasadjustments:
        return 0, 0  # (exported, skipped) - No export attempted

    edited_filename = f"{filename_base}_edited{filename_ext}"
    edited_path = os.path.join(export_path, edited_filename)

    if os.path.exists(edited_path):
        logger.debug(f"Skipping export of edited {media_type} {edited_filename} - file already exists")
        return 0, 1  # (exported, skipped)
    else:
        try:
            # Note: We need separate calls to item.export() for each variation (original, edited, raw, live)
            # because we need different filenames for each variation, and item.export() only accepts a single filename.
            exported_files = item.export(filename=edited_filename, dest=export_path, use_photos_export=True,
                                         edited=True, live_photo=False, raw_photo=False)
            if not exported_files:
                error_msg = f"Failed to export edited {media_type} {edited_filename}"
                log_export_error(os.path.dirname(export_path), item, edited_filename, error_msg)
                raise RuntimeError(error_msg)
            return 1, 0  # (exported, skipped)
        except Exception as e:
            if not isinstance(e, RuntimeError):  # Only log if not already logged
                log_export_error(os.path.dirname(export_path), item, edited_filename, str(e))
            raise


def export_raw(item, export_path, filename_base, filename_ext, is_photo, is_video):
    """
    Export the raw version of a photo if it has a raw version.

    Exports the raw version of a photo to the specified export path if the item
    has a raw version. Skips export for videos and photos without raw versions.
    Also skips export if the file already exists.

    Args:
        item (osxphotos.PhotoInfo): The photo or video to export
        export_path (str): The directory to export to
        filename_base (str): The base filename without extension
        filename_ext (str): The file extension including the dot (e.g., '.jpg')
        is_photo (bool): Whether the item is a photo
        is_video (bool): Whether the item is a video

    Returns:
        tuple: A tuple containing (exported_count, skipped_count)
            - exported_count (int): 1 if the file was exported, 0 otherwise
            - skipped_count (int): 1 if the file was skipped, 0 otherwise
    """
    if not is_photo:
        if is_video:
            logger.debug(f"Skipping export of raw version for video {item.filename} - not applicable for videos")
        return 0, 0  # (exported, skipped) - No export attempted

    if not (item.has_raw or item.israw):
        logger.debug(f"Skipping export of raw photo for {item.filename} - no raw version available")
        return 0, 0  # (exported, skipped) - No export attempted

    raw_filename = f"{filename_base}_raw{filename_ext}"
    raw_path = os.path.join(export_path, raw_filename)

    if os.path.exists(raw_path):
        logger.debug(f"Skipping export of raw photo {raw_filename} - file already exists")
        return 0, 1  # (exported, skipped)
    else:
        try:
            # Note: We need separate calls to item.export() for each variation (original, edited, raw, live)
            # because we need different filenames for each variation, and item.export() only accepts a single filename.
            exported_files = item.export(filename=raw_filename, dest=export_path, use_photos_export=True, edited=False,
                                         live_photo=False, raw_photo=True)
            if not exported_files:
                error_msg = f"Failed to export raw photo {raw_filename}"
                log_export_error(os.path.dirname(export_path), item, raw_filename, error_msg)
                raise RuntimeError(error_msg)
            return 1, 0  # (exported, skipped)
        except Exception as e:
            logger.debug(f"Could not export raw photo for {item.filename}: {e}")
            log_export_error(os.path.dirname(export_path), item, raw_filename, str(e))
            return 0, 0  # (exported, skipped) - Export failed


def export_live(item, export_path, filename_base, filename_ext, is_photo, is_video):
    """
    Export the live version of a photo if it's a live photo.

    Exports the live version of a photo to the specified export path if the item
    is a live photo. Skips export for videos and non-live photos.
    Also skips export if the file already exists.

    Args:
        item (osxphotos.PhotoInfo): The photo or video to export
        export_path (str): The directory to export to
        filename_base (str): The base filename without extension
        filename_ext (str): The file extension including the dot (e.g., '.jpg')
        is_photo (bool): Whether the item is a photo
        is_video (bool): Whether the item is a video

    Returns:
        tuple: A tuple containing (exported_count, skipped_count)
            - exported_count (int): 1 if the file was exported, 0 otherwise
            - skipped_count (int): 1 if the file was skipped, 0 otherwise
    """
    if not is_photo:
        if is_video:
            logger.debug(f"Skipping export of live version for video {item.filename} - not applicable for videos")
        return 0, 0  # (exported, skipped) - No export attempted

    live_filename = f"{filename_base}_live{filename_ext}"
    live_path = os.path.join(export_path, live_filename)

    if os.path.exists(live_path):
        logger.debug(f"Skipping export of live photo {live_filename} - file already exists")
        return 0, 1  # (exported, skipped)
    else:
        try:
            if item.live_photo:
                # Note: We need separate calls to item.export() for each variation (original, edited, raw, live)
                # because we need different filenames for each variation, and item.export() only accepts a single filename.
                exported_files = item.export(filename=live_filename, dest=export_path, use_photos_export=True,
                                             edited=False, live_photo=True, raw_photo=False)
                if not exported_files:
                    error_msg = f"Failed to export live photo {live_filename}"
                    log_export_error(os.path.dirname(export_path), item, live_filename, error_msg)
                    raise RuntimeError(error_msg)
                return 1, 0  # (exported, skipped)
            return 0, 0  # (exported, skipped) - Live photo not available for this photo
        except Exception as e:
            logger.debug(f"Could not export live photo for {item.filename}: {e}")
            log_export_error(os.path.dirname(export_path), item, live_filename, str(e))
            return 0, 0  # (exported, skipped) - Export failed


def export_media(threshold_date, export_base_dir):
    """
    Export photos and videos from Photos.app that were taken since the threshold date.

    This is the main export function that:
    1. Connects to the Photos library
    2. Retrieves all media items
    3. Filters them by date
    4. Exports each item (original, edited, raw, and live versions as applicable)
    5. Organizes them into date-based directories

    The function logs progress and handles errors during the export process.

    Args:
        threshold_date (datetime): The date to filter media by (only export media taken on or after this date)
        export_base_dir (str): The base directory to export media to

    Returns:
        datetime: The creation date of the most recent exported photo or video, or None if no media was exported

    Raises:
        SystemExit: If there's an error accessing the Photos library
    """
    # Note: In response to the question "can all variations be exported using a single call to item.export()?":
    # It's not possible to export all variations (original, edited, raw, live) with a single call to item.export().
    # The method only accepts a single filename parameter, and we need different filenames for each variation.
    # Additionally, the parameters edited, live_photo, and raw_photo control which version to export,
    # and they can't all be set to True at the same time to export all variations.
    # Therefore, we need separate calls to item.export() for each variation.
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
    most_recent_date = None
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
            original_exported, original_skipped = export_original(item, export_path, filename_base, filename_ext,
                                                                  is_video, media_type)
            edited_exported, edited_skipped = export_edited(item, export_path, filename_base, filename_ext, media_type)
            raw_exported, raw_skipped = export_raw(item, export_path, filename_base, filename_ext, is_photo, is_video)
            live_exported, live_skipped = export_live(item, export_path, filename_base, filename_ext, is_photo,
                                                      is_video)

            # Accumulate counts
            exported_count += original_exported + edited_exported + raw_exported + live_exported
            skipped_count += original_skipped + edited_skipped + raw_skipped + live_skipped

            # Update most recent date if any file was exported
            if original_exported + edited_exported + raw_exported + live_exported > 0:
                if most_recent_date is None or item_date > most_recent_date:
                    most_recent_date = item_date

            processed_count += 1
            if processed_count % 10 == 0:
                logger.info(
                    f"Processed {processed_count}/{len(filtered_media)} media items, exported {exported_count} files")

        except Exception as e:
            logger.error(f"Error exporting {item.filename}: {e}")
            log_export_error(export_base_dir, item, item.filename, str(e))

    logger.info(
        f"Successfully exported {exported_count} files from {processed_count} media items, skipped {skipped_count} already existing files")

    if most_recent_date:
        logger.debug(f"Most recent exported photo date: {most_recent_date}")

    return most_recent_date


def get_threshold_date(args):
    """
    Determine the threshold date based on command line arguments or last_export.txt.

    This function determines the threshold date for filtering media items by:
    1. Using the date provided in command line arguments, if any
    2. Otherwise, reading from the last_export.txt file, if it exists
    3. Falling back to the current date and time if neither of the above is available

    Args:
        args (argparse.Namespace): The parsed command line arguments

    Returns:
        tuple: A tuple containing:
            - threshold_date (datetime): A datetime object representing the threshold date
            - timestamp_file (str): The path to the last_export.txt file
    """
    threshold_date_str = args.threshold_date
    timestamp_file = os.path.join(args.export_dir, "last_export.txt")

    # If threshold_date not provided on command line, try to read from last_export.txt
    if threshold_date_str is None:
        try:
            if os.path.exists(timestamp_file):
                with open(timestamp_file, "r") as f:
                    threshold_date_str = f.readline().strip()
                logger.debug(f"Read threshold date from {timestamp_file}: {threshold_date_str}")
            else:
                logger.debug(f"No last_export.txt found at {timestamp_file}, using default threshold date")
                threshold_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"Failed to read from {timestamp_file}: {e}, using default threshold date")
            threshold_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Parse threshold date
    threshold_date = parse_threshold_date(threshold_date_str)
    logger.info(f"Using threshold date: {threshold_date}")

    return threshold_date, timestamp_file


def save_export_timestamp(timestamp_file, timestamp):
    """
    Save the timestamp to the last_export.txt file.

    This function writes the timestamp to a file, which will be used
    as the default threshold date for the next run of the script if no date
    is specified on the command line. The timestamp is typically the creation date
    of the most recent exported photo or video.

    Args:
        timestamp_file (str): The path to the file where the timestamp will be saved
        timestamp (str): The timestamp string to save (format: YYYY-MM-DD HH:MM:SS)

    Returns:
        None
    """

    try:
        with open(timestamp_file, "w") as f:
            f.write(timestamp + "\n")
        logger.debug(f"Saved export timestamp to {timestamp_file}")
    except Exception as e:
        logger.error(f"Failed to save export timestamp to {timestamp_file}: {e}")


def log_export_error(export_dir, item, filename, error_message):
    """
    Log export errors to export_dir/last_export_errors.log.

    This function writes error information to a log file when an export operation fails.
    The log includes details about the media item that failed to export, such as its
    filename, original filename, date, and the error message.

    Args:
        export_dir (str): The directory where the log file will be created
        item (osxphotos.PhotoInfo): The photo or video that failed to export
        filename (str): The filename that was being exported
        error_message (str): The error message describing what went wrong

    Returns:
        None
    """
    error_log_file = os.path.join(export_dir, "last_export_errors.log")

    try:
        with open(error_log_file, "a") as f:
            f.write(f"Filename: {filename}\n")
            f.write(f"Original filename: {item.original_filename}\n")
            f.write(f"Date: {item.date}\n")
            f.write(f"Error: {error_message}\n")
            f.write("-" * 50 + "\n")
        logger.debug(f"Logged export error to {error_log_file}")
    except Exception as e:
        logger.error(f"Failed to log export error to {error_log_file}: {e}")


def main():
    """
    Main entry point for the script.

    This function orchestrates the entire export process:
    1. Parses command line arguments
    2. Sets up logging based on verbosity level
    3. Determines the threshold date for filtering media
    4. Exports photos and videos taken since the threshold date
    5. Saves the creation date of the most recent exported photo for the next run

    Returns:
        None
    """
    args = parse_args()

    # Set up logging based on verbosity
    setup_logging(args.verbose)

    # Get threshold date and timestamp file path
    threshold_date, timestamp_file = get_threshold_date(args)
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Export photos and videos
    most_recent_date = export_media(threshold_date, args.export_dir)

    # Save the most recent photo date for next run, or current timestamp if no photos were exported
    if most_recent_date:
        timestamp_to_save = most_recent_date.strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp_to_save = current_timestamp
        logger.debug("No photos exported, using current timestamp")

    save_export_timestamp(timestamp_file, timestamp_to_save)

    logger.info("Export completed successfully")


if __name__ == "__main__":
    main()
