# Auto Export Photos

A tool for automatically exporting photos and videos from macOS Photos app.

## Description

This script exports photos and videos from the macOS Photos app that were taken since a specified date. It can export original, edited, raw, and live photo versions of media items, organizing them into a directory structure based on the date the photo was taken (YYYY/MM/YYYY-MM-DD).

The script keeps track of the last export date in a file called 'last_export.txt' in the export directory, which is used as the default threshold date for subsequent runs if no date is specified.

## Features

- Export photos and videos from macOS Photos app
- Filter media by date taken
- Export multiple versions of each media item:
  - Original version
  - Edited version (if edits exist)
  - Raw version (for photos with raw data)
  - Live photo version (for live photos)
- Organize exported files into a date-based directory structure
- Skip already exported files
- Detailed logging with configurable verbosity levels
- Error logging for failed exports

## Requirements

- macOS with Photos app
- Python 3.13
- osxphotos library

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/jamathews/auto_export_photos.git
   cd auto_export_photos
   ```

2. Install dependencies using pipenv:
   ```
   pipenv install
   ```

   Or using pip:
   ```
   pip install osxphotos
   ```

## Usage

### Basic Usage

Run the script with default settings:

```
python export.py
```

This will export all photos and videos taken since the last export (or today if no previous export) to the default directory (`~/Pictures`).

### Command Line Options

```
python export.py [--threshold-date YYYY-MM-DD] [--export-dir PATH] [-v]
```

Options:
- `--threshold-date`: Date to export photos from (default: read from last_export.txt or current date)
- `--export-dir`: Base directory for exported photos (default: ~/Pictures)
- `-v, --verbose`: Increase verbosity level (-v for WARNING, -vv for INFO, -vvv for DEBUG)

### Examples

Export photos taken since January 1, 2023:
```
python export.py --threshold-date 2023-01-01
```

Export photos to a custom directory:
```
python export.py --export-dir ~/Documents/Photos
```

Export with detailed logging:
```
python export.py -vvv
```

## Output Structure

Exported files are organized in the following directory structure:
```
export_dir/
├── YYYY/
│   ├── MM/
│   │   ├── YYYY-MM-DD/
│   │   │   ├── photo1.jpg
│   │   │   ├── photo1_edited.jpg
│   │   │   ├── photo1_raw.jpg
│   │   │   ├── photo1_live.jpg
│   │   │   ├── video1.mp4
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── last_export.txt
└── last_export_errors.log
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project uses the [osxphotos](https://github.com/RhetTbull/osxphotos) library by Rhet Turnbull.
