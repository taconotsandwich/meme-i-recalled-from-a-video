#!/usr/bin/env python3
"""
Main entry point for the video processor application.
"""
import argparse
import sys
import os
import json
import logging
from dotenv import load_dotenv
from video_processor import VideoProcessor, process_multiple_videos
from generate_sql import generate_d1_sql
from config import *

# Load environment variables from .env file
load_dotenv()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Video Processor and Cloudflare D1 SQL Generator')
    
    # Input/Output
    parser.add_argument('input', help='Path to video file or directory containing videos')
    parser.add_argument('-o', '--output', default=os.getenv('OUTPUT_DIR', 'output'),
                               help='Output directory for frames and metadata (default: output)')
    parser.add_argument('--sql-file', help='Output path for the generated SQL file (default: d1_import.sql inside output directory)')

    # Extraction
    parser.add_argument('-i', '--interval', type=int, default=DEFAULT_FRAME_INTERVAL,
                               help=f'Frame extraction interval (default: {DEFAULT_FRAME_INTERVAL})')
    parser.add_argument('--scene-detection', action='store_true',
                               help='Use scene detection for intelligent frame extraction')
    parser.add_argument('--scene-threshold', type=float, default=DEFAULT_SCENE_THRESHOLD,
                               help=f'Scene detection threshold (default: {DEFAULT_SCENE_THRESHOLD})')
    parser.add_argument('--min-scene-len', type=int, default=DEFAULT_MIN_SCENE_LEN,
                               help=f'Minimum scene length in frames (default: {DEFAULT_MIN_SCENE_LEN})')
    parser.add_argument('--keyframes-per-scene', type=int, default=DEFAULT_KEYFRAMES_PER_SCENE,
                               help=f'Keyframes per scene (default: {DEFAULT_KEYFRAMES_PER_SCENE})')
    
    # OCR & Analysis
    parser.add_argument('--text-region', choices=['all', 'top', 'bottom'], default='all',
                               help='Text region to analyze (default: all)')
    parser.add_argument('--lang', default='eng',
                               help='OCR language code (default: eng)')
    parser.add_argument('--ocr-engine', choices=['tesseract', 'easyocr'], default='tesseract',
                               help='OCR engine to use (default: tesseract)')
    
    # Deduplication
    parser.add_argument('--dedup-mode', choices=['ssim', 'text', 'both'], default='both',
                               help='Deduplication mode (default: both)')
    parser.add_argument('--ssim-threshold', type=float, default=DEFAULT_SSIM_THRESHOLD,
                               help=f'SSIM threshold for frame similarity (default: {DEFAULT_SSIM_THRESHOLD})')
    
    # Performance
    parser.add_argument('--workers', type=int, default=DEFAULT_NUM_WORKERS,
                               help=f'Number of worker processes (default: {DEFAULT_NUM_WORKERS})')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                               help=f'Batch size for OCR processing (default: {DEFAULT_BATCH_SIZE})')

    # URL Formatting
    parser.add_argument('--r2-public-url', default=os.getenv('R2_PUBLIC_URL'),
                        help='Public base URL for the R2 bucket (used for generating SQL links)')

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

        processor = VideoProcessor(
            ssim_threshold=args.ssim_threshold,
            batch_size=args.batch_size,
            num_workers=args.workers
        )

        results = process_multiple_videos(
            processor=processor,
            video_paths=video_files,
            output_base_dir=args.output,
            frame_interval=args.interval,
            dedup_mode=args.dedup_mode,
            text_region=args.text_region,
            lang=args.lang,
            ocr_engine=args.ocr_engine,
            use_scene_detection=args.scene_detection,
            scene_threshold=args.scene_threshold,
            min_scene_len=args.min_scene_len,
            keyframes_per_scene=args.keyframes_per_scene
        )

        successful_videos = sum(1 for r in results if 'error' not in r)
        print(f"\nProcessing completed: {successful_videos}/{len(results)} videos processed successfully")

        # 2. Generate SQL
        if successful_videos > 0:
            print("\nGenerating Cloudflare D1 SQL import files...")
            for result in results:
                if 'error' not in result:
                    video_output_dir = result['output_dir']
                    # Default SQL path is now inside the movie folder
                    sql_path = os.path.join(video_output_dir, 'd1_import.sql')
                    generate_d1_sql(video_output_dir, sql_path, args.r2_public_url)
                    print(f"  - SQL generated: {sql_path}")
            
            print("\nDone! You can now use the root deploy script to push these results to Cloudflare.")
        else:
            print("\nNo videos were processed successfully.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
