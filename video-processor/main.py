#!/usr/bin/env python3
"""
Main entry point for the video processor application (STT-only extraction).
"""
import argparse
import sys
import os
import logging
import re
from dotenv import load_dotenv
from video_processor import VideoProcessor, process_multiple_videos
from generate_sql import generate_d1_sql
from config import *

# Load environment variables from .env file
load_dotenv()

def parse_duration(duration_str):
    """Parse duration string like 1h2m3s into total seconds."""
    if not duration_str:
        return None
    
    pattern = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
    match = pattern.match(duration_str)
    if not match or not any(match.groups()):
        raise ValueError(f"Invalid duration format: {duration_str}. Use e.g., 1h30m or 45s")
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    return hours * 3600 + minutes * 60 + seconds

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Video Processor (STT-only) and Cloudflare D1 SQL Generator')
    
    # Input/Output
    parser.add_argument('input', help='Path to video file or directory containing videos')
    parser.add_argument('-o', '--output', default=os.getenv('OUTPUT_DIR', 'output'),
                               help='Output directory for frames and metadata (default: output)')
    parser.add_argument('--sql-file', help='Output path for the generated SQL file (default: d1_import.sql inside movie folder)')
    parser.add_argument('--length', help='Limit processing to the first X duration (e.g., 1h30m, 45s)')

    # OCR & Analysis
    parser.add_argument('--ocr-lang', default='eng',
                               help='OCR language code for EasyOCR (default: eng)')
    
    # STT (Speech to Text)
    parser.add_argument('--whisper-model', default=DEFAULT_WHISPER_MODEL,
                        help=f'Whisper model size (default: {DEFAULT_WHISPER_MODEL})')
    parser.add_argument('--stt-lang', default=DEFAULT_STT_LANG,
                        help=f'Language code for STT (default: {DEFAULT_STT_LANG})')
    
    # Performance
    parser.add_argument('--workers', type=int, default=DEFAULT_NUM_WORKERS,
                               help=f'Number of worker processes (default: {DEFAULT_NUM_WORKERS})')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                               help=f'Batch size for processing (default: {DEFAULT_BATCH_SIZE})')

    return parser.parse_args()


def get_video_files(input_path):
    """Get list of video files from input path."""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}

    if os.path.isfile(input_path):
        if os.path.splitext(input_path.lower())[1] in video_extensions:
            return [input_path]
        else:
            raise ValueError(f"File {input_path} is not a supported video format")

    elif os.path.isdir(input_path):
        video_files = []
        for filename in os.listdir(input_path):
            if os.path.splitext(filename.lower())[1] in video_extensions:
                video_files.append(os.path.join(input_path, filename))

        if not video_files:
            raise ValueError(f"No video files found in directory {input_path}")

        return sorted(video_files)

    else:
        raise FileNotFoundError(f"Input path {input_path} does not exist")

def main():
    """Main function."""
    args = parse_arguments()

    try:
        # 1. Process Videos
        video_files = get_video_files(args.input)
        print(f"Found {len(video_files)} video file(s) to process")

        duration_limit = parse_duration(args.length)
        if duration_limit:
            print(f"Processing limit set to: {args.length} ({duration_limit} seconds)")

        processor = VideoProcessor(
            batch_size=args.batch_size,
            num_workers=args.workers
        )

        results = process_multiple_videos(
            processor=processor,
            video_paths=video_files,
            output_base_dir=args.output,
            ocr_lang=args.ocr_lang,
            whisper_model=args.whisper_model,
            stt_lang=args.stt_lang,
            max_duration=duration_limit
        )
        successful_videos = sum(1 for r in results if 'error' not in r)
        print(f"\nProcessing completed: {successful_videos}/{len(results)} videos processed successfully")

        # 2. Generate SQL
        if successful_videos > 0:
            print("\nGenerating Cloudflare D1 SQL import files...")
            for result in results:
                if 'error' not in result:
                    video_output_dir = result['output_dir']
                    sql_path = os.path.join(video_output_dir, 'd1_import.sql')
                    generate_d1_sql(video_output_dir, sql_path)
                    print(f"  - SQL generated: {sql_path}")
            
            print("\nDone! You can now use the root deploy script to push these results to Cloudflare.")
        else:
            print("\nNo videos were processed successfully.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()