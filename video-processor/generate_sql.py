import os
import json
import argparse

def generate_d1_sql(video_output_dir, sql_output_file):
    """
    Generates a SQLite-compatible SQL file for a single movie's metadata.
    Consolidates text fields into a single 'subtitle' column using ONLY OCR text.
    """
    
    # Use DROP and CREATE to ensure a clean state
    sql_content = [
        "DROP TABLE IF EXISTS video_frames;",
        """CREATE TABLE IF NOT EXISTS video_frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    frame_number INTEGER,
    timestamp REAL,
    subtitle TEXT,
    scene_id INTEGER
);"""
    ]

    metadata_path = os.path.join(video_output_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        print(f"Error: Metadata not found at {metadata_path}")
        return False

    video_dir_name = os.path.basename(video_output_dir)

    with open(metadata_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            video_name = data.get('video_name', 'unknown')
            frames = data.get('frames', [])
            
            print(f"Generating SQL for {video_name} ({len(frames)} frames)...")

            for frame in frames:
                filename = frame.get('filename', '')
                filepath = f"{video_dir_name}/{filename}" 
                frame_number = frame.get('frame_number', 0)
                timestamp = frame.get('timestamp', 0.0)
                
                # Use ONLY OCR text for the searchable subtitle field
                subtitle = frame.get('ocr_text', '').strip()
                subtitle = subtitle.replace("'", "''")

                sql = f"INSERT INTO video_frames (filename, filepath, frame_number, timestamp, subtitle) VALUES ('{filename}', '{filepath}', {frame_number}, {timestamp}, '{subtitle}');"
                sql_content.append(sql)
        except json.JSONDecodeError:
            print(f"Error reading {metadata_path}, skipping.")
            return False

    with open(sql_output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_content))

    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate D1 SQL from metadata')
    parser.add_argument('video_dir', help='Directory containing a movie output (with metadata.json)')
    parser.add_argument('--sql-file', help='Output SQL file path')
    args = parser.parse_args()
    
    sql_path = args.sql_file if args.sql_file else os.path.join(args.video_dir, 'd1_import.sql')
    generate_d1_sql(args.video_dir, sql_path)
