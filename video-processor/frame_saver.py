"""Frame saving module for handling frame deduplication and saving."""
import os
import cv2
import json
import logging
from datetime import datetime
from tqdm import tqdm
from ocr import (normalize_text, is_text_significantly_different, 
                 has_meaningful_text, calculate_region_from_coords, 
                 filter_ocr_results_by_region)


def save_frame_with_metadata(frame, frame_number, stt_text, ocr_text, saved_count, video_output_dir, fps):
    """Save a frame with its associated metadata."""
    frame_filename = f"frame_{saved_count:06d}.jpg"
    frame_path = os.path.join(video_output_dir, frame_filename)

    try:
        cv2.imwrite(frame_path, frame)
        timestamp = frame_number / fps
        frame_info = {
            'frame_number': frame_number,
            'timestamp': timestamp,
            'filename': frame_filename,
            'ocr_text': ocr_text,
            'stt_text': stt_text,
            'saved_count': saved_count
        }
        return frame_info, True
    except Exception as e:
        logging.error(f"Error saving frame {frame_number}: {e}")
        return None, False


def should_save_frame(ocr_text, stt_text, last_text_data, only_with_text=False):
    """Determine if a frame should be saved based on text deduplication."""
    if only_with_text and not has_meaningful_text(ocr_text) and not stt_text:
        return False

    primary_text = ocr_text if ocr_text.strip() else stt_text
    last_primary_text = last_text_data.get('ocr_text', '') if last_text_data.get('ocr_text', '').strip() else last_text_data.get('stt_text', '')

    norm_text = normalize_text(primary_text)
    norm_last_text = normalize_text(last_primary_text)

    return not norm_text or is_text_significantly_different(norm_text, norm_last_text) or not last_text_data.get('stt_text')


def saver(result_queue, total_frames, lang, video_output_dir, fps, video_name, num_workers, only_with_text=False):
    """Main saver function that handles collection, region detection, and final saving."""
    logging.info(f"Saver process started. Collecting all frames to detect subtitle region...")
    finished_workers = 0
    all_frames = []
    y_coords = []
    img_h = 0

    # 1. Collect everything
    with tqdm(total=total_frames, desc=f"Collecting frames {video_name}",
              mininterval=0.5, dynamic_ncols=True, position=1) as pbar:
        while finished_workers < num_workers:
            item = result_queue.get()
            if item == "__STOP__":
                finished_workers += 1
                continue
            
            frame_number, frame, data = item
            if img_h == 0:
                img_h = frame.shape[0]
            
            ocr_results = data.get('ocr_results', [])
            # Collect y-coordinates for region detection from ALL frames
            for (bbox, text, prob) in ocr_results:
                if prob > 0.5:
                    y_min = min(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
                    y_max = max(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
                    y_coords.append((y_min, y_max))
            
            all_frames.append((frame_number, frame, data))
            pbar.update(1)

    # 2. Detect Region using all collected coordinates
    logging.info(f"Analyzing {len(y_coords)} text blocks across all frames...")
    detected_region = calculate_region_from_coords(y_coords, img_h)
    logging.info(f"Final auto-detected subtitle region: {detected_region}")

    # 3. Sort and Save
    all_frames.sort(key=lambda x: x[0])
    last_text_data = {"ocr_text": "", "stt_text": ""}
    saved_count = 0
    frame_infos = []

    logging.info(f"Filtering OCR text and saving {len(all_frames)} potential frames...")
    with tqdm(total=len(all_frames), desc=f"Saving {video_name}",
              mininterval=0.5, dynamic_ncols=True, position=1) as pbar:
        for frame_number, frame, data in all_frames:
            # Filter the OCR results using the globally detected region
            ocr_results = data.get('ocr_results', [])
            ocr_text = filter_ocr_results_by_region(ocr_results, detected_region, lang)
            stt_text = data.get('stt_text', '')

            # ONLY save if OCR text was actually found
            if ocr_text.strip():
                if should_save_frame(ocr_text, stt_text, last_text_data, only_with_text):
                    frame_info, success = save_frame_with_metadata(
                        frame, frame_number, stt_text, ocr_text, saved_count, video_output_dir, fps)

                    if success and frame_info:
                        frame_infos.append(frame_info)
                        last_text_data = {"ocr_text": ocr_text, "stt_text": stt_text}
                        saved_count += 1
            pbar.update(1)

    # 4. Save metadata
    metadata_path = os.path.join(video_output_dir, "metadata.json")
    metadata = {
        'video_name': video_name,
        'total_frames_processed': len(all_frames),
        'frames_saved': saved_count,
        'detected_region': detected_region,
        'language': lang,
        'fps': fps,
        'timestamp': datetime.now().isoformat(),
        'frames': frame_infos
    }

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return saved_count, frame_infos