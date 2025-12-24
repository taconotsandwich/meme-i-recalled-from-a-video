"""Main video processor module that orchestrates frame extraction and processing."""
import cv2
import time
import multiprocessing
import os
import logging
from tqdm import tqdm
from config import *
from frame_processing import stt_extractor_worker
from frame_saver import saver
from stt import extract_audio, transcribe_audio


class VideoProcessor:
    """Main video processor class that handles video frame extraction via STT."""

    def __init__(self, text_similarity_threshold=DEFAULT_TEXT_SIMILARITY_THRESHOLD,
                 batch_size=DEFAULT_BATCH_SIZE, num_workers=DEFAULT_NUM_WORKERS):
        self.text_similarity_threshold = text_similarity_threshold
        self.batch_size = batch_size
        self.num_workers = num_workers

    def process_video(self, video_path, output_dir, ocr_lang='eng',
                     whisper_model=DEFAULT_WHISPER_MODEL,
                     stt_lang=DEFAULT_STT_LANG, max_duration=None):
        """
        Process a video file to extract and analyze frames based ONLY on STT.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Get video info
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        cap.release()

        # Adjust total frames if duration limit is set
        if max_duration:
            total_frames = min(total_frames, int(max_duration * fps))

        logging.info(f"Processing video: {video_name}")
        logging.info(f"Total frames to examine: {total_frames}, FPS: {fps}")

        # --- STT EXTRACTION ---
        start_time = time.time()
        audio_path = os.path.join(output_dir, f"{video_name}.mp3")
        
        if not extract_audio(video_path, audio_path, duration=max_duration):
            raise RuntimeError("Failed to extract audio for STT")

        # Transcription
        segments = transcribe_audio(audio_path, model_size=whisper_model, lang=stt_lang)
        
        # Filter segments to stay within max_duration if any exceed it due to whisper behavior
        if max_duration:
            segments = [s for s in segments if s['start'] < max_duration]
        
        # Setup multiprocessing
        result_queue = multiprocessing.Queue()
        
        total_segments = len(segments)
        # Start saver. It now handles global region detection.
        saver_process = multiprocessing.Process(
            target=saver,
            args=(result_queue, total_segments, ocr_lang,
                    output_dir, fps, video_name, self.num_workers,
                    False)
        )
        saver_process.start()
        
        # Divide extraction tasks
        extraction_num_workers = min(self.num_workers, 4)
        tasks_per_worker = [[] for _ in range(extraction_num_workers)]
        for i, segment in enumerate(segments):
            mid_time = (segment['start'] + segment['end']) / 2
            frame_num = int(mid_time * fps)
            if frame_num < total_frames:
                tasks_per_worker[i % extraction_num_workers].append((frame_num, segment['text']))

        # Start extraction workers
        extraction_workers = []
        print(f"Extracting {total_segments} frames using {extraction_num_workers} workers...")
        for i in range(extraction_num_workers):
            p = multiprocessing.Process(
                target=stt_extractor_worker,
                args=(video_path, tasks_per_worker[i], result_queue,
                        ocr_lang)
            )
            p.start()
            extraction_workers.append(p)

        for p in extraction_workers:
            p.join()
        
        for _ in range(self.num_workers):
            result_queue.put("__STOP__")
            
        saver_process.join()
        
        if os.path.exists(audio_path):
            os.remove(audio_path)

        end_time = time.time()
        processing_time = end_time - start_time
            
        return {
            'success': True, 
            'frames_saved': total_segments, 
            'video_name': video_name, 
            'output_dir': output_dir,
            'video_path': video_path,
            'fps': fps,
            'processing_time': processing_time
        }


def process_multiple_videos(processor, video_paths, output_base_dir, **kwargs):
    results = []
    for video_path in video_paths:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        video_output_dir = os.path.join(output_base_dir, video_name)
        try:
            result = processor.process_video(video_path, video_output_dir, **kwargs)
            results.append(result)
        except Exception as e:
            logging.error(f"Error processing {video_path}: {e}")
            results.append({'video_path': video_path, 'error': str(e), 'success': False})
    return results
