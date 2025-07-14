import os
import re
import logging
import argparse

# --- GLOBAL CONFIGURATION ---
# List of video formats to process. You can add or remove extensions here.
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')


def setup_console_logging():
    """Sets up a simple logger that only writes to the console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
    )


def clean_filename(filename: str) -> str:
    """
    Applies a series of cleaning rules to a filename.
    It removes tags, formats spaces, and handles hyphens to standardize the names.

    Args:
        filename (str): The original filename (with extension).

    Returns:
        str: The new, cleaned filename according to the rules.
    """
    # Separate the filename from its extension to avoid modifying it
    name, ext = os.path.splitext(filename)
    
    # Recursively remove tags like [Subs] or (1080p) from the start or end of the name
    while True:
        stripped_name = name.strip()
        pattern = r"^\s*(\[.*?\]|\(.*?\))\s*|\s*(\[.*?\]|\(.*?\))\s*$"
        name = re.sub(pattern, '', stripped_name)
        # If no more changes are made, exit the loop
        if name == stripped_name:
            break
            
    # Replace underscores, which are often used instead of spaces
    name = name.replace('_', ' ')
    
    # --- Smart hyphen handling ---
    # 1. Add spaces for episode separators (e.g., "Series-S01" -> "Series - S01").
    #    The lookahead (?=...) checks if the hyphen is followed by S, E, or a digit.
    name = re.sub(r'\s*-\s*(?=[SE\d])', ' - ', name)
    
    # 2. Remove spaces around hyphens used within a name (e.g., "hanako - kun" -> "hanako-kun").
    #    The negative lookahead (?!...) ensures it's NOT an episode separator.
    name = re.sub(r'\s+-\s+(?![SE\d])', '-', name)
    
    # Clean up any double spaces created and trim leading/trailing whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Reassemble the final name with its original extension
    return f"{name}{ext}"


def process_directory(root_dir: str, dry_run: bool = True):
    """
    Recursively scans a directory and renames only video files.
    It applies the `clean_filename` rules to each video file found.

    Args:
        root_dir (str): The path to the directory to start scanning from.
        dry_run (bool): If True, only simulates the operations without modifying any files.
    """
    if dry_run:
        logging.warning("--- RUNNING IN DRY-RUN MODE (SIMULATION) ---")
        logging.info(f"Will only look for files with these extensions: {VIDEO_EXTENSIONS}")
        logging.warning("No files will be renamed. Use --force to apply changes.")
    else:
        logging.info("--- STARTING REAL PROCESSING ---")
        logging.info(f"Processing only files with extensions: {VIDEO_EXTENSIONS}")
        
    # Initialize counters for the final summary
    counters = {'processed_videos': 0, 'to_rename': 0, 'skipped_other_files': 0, 'errors': 0}

    # os.walk is the most efficient way to recursively traverse a directory structure
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude hidden directories (like .git) from the scan for cleanliness and performance
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]

        for filename in filenames:
            # Check if the file has one of the allowed video extensions
            is_video = filename.lower().endswith(VIDEO_EXTENSIONS)
            
            # Skip the file if it's not a video or if it's a hidden/system file (e.g., .DS_Store)
            if filename.startswith('.') or not is_video:
                counters['skipped_other_files'] += 1
                continue

            # If the file is a video, process it
            counters['processed_videos'] += 1
            old_filepath = os.path.join(dirpath, filename)
            
            try:
                new_filename = clean_filename(filename)
                
                # If the name is already correct, do nothing and move to the next file
                if filename == new_filename:
                    continue
                
                # If we get here, the file needs to be renamed
                counters['to_rename'] += 1
                
                logging.info(f"[{'DRY-RUN' if dry_run else 'RENAME'}]")
                logging.info(f"  Old: {filename}")
                logging.info(f"  New: {new_filename}")
                
                # Only perform the rename if not in dry-run mode
                if not dry_run:
                    new_filepath = os.path.join(dirpath, new_filename)
                    if os.path.exists(new_filepath):
                        logging.error(f"  -> ERROR: File '{new_filename}' already exists. Skipping.")
                        counters['errors'] += 1
                        counters['to_rename'] -= 1 # Remove from count because it wasn't renamed
                    else:
                        os.rename(old_filepath, new_filepath)

            except Exception as e:
                # Catch any other unexpected error to prevent the script from crashing
                logging.error(f"  -> UNEXPECTED ERROR on {old_filepath}: {e}")
                counters['errors'] += 1
                if counters['to_rename'] > 0: counters['to_rename'] -= 1

    # Print the final summary with the correct counts
    logging.info("--- PROCESSING COMPLETE ---")
    unchanged_videos = counters['processed_videos'] - counters['to_rename'] - counters['errors']
    
    if dry_run:
        logging.info(f"Video files scanned: {counters['processed_videos']}")
        logging.info(f"Files that would be renamed: {counters['to_rename']}")
        logging.info(f"Video files already correct: {unchanged_videos}")
    else:
        actually_renamed = counters['to_rename']
        logging.info(f"Video files actually renamed: {actually_renamed}")
        logging.info(f"Video files not modified: {unchanged_videos}")
    
    logging.info(f"Total files ignored (non-video, system files): {counters['skipped_other_files']}")
    if counters['errors'] > 0:
        logging.warning(f"Errors encountered: {counters['errors']}")


# --- SCRIPT ENTRY POINT ---
# This block runs only when the script is executed directly
if __name__ == "__main__":
    # 1. Set up console logging
    setup_console_logging()

    # 2. Configure the parser for command-line arguments
    parser = argparse.ArgumentParser(
        description="Renames anime video files. Runs in simulation mode by default.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Define the 'directory' argument, making it optional.
    # If not provided, it defaults to the current working directory (os.getcwd()).
    parser.add_argument("directory", nargs='?', default=os.getcwd(), help="Optional: The path to scan. Defaults to the current directory.")
    
    # Define the --force flag, which is required to confirm a real run
    parser.add_argument("--force", action="store_true", help="Performs the actual renaming. USE WITH CAUTION.")

    args = parser.parse_args()
    
    # The default mode is dry-run. is_dry_run will be True unless --force is used.
    is_dry_run = not args.force
    
    # 3. Start the main processing function
    process_directory(args.directory, dry_run=is_dry_run)
