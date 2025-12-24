"""Frame processing module for video frame extraction and analysis via STT."""
import cv2
import logging

def stt_extractor_worker(video_path, tasks, result_queue, lang='eng'):
    """Worker process for extracting frames and performing initial OCR analysis."""
    from ocr import extract_full_ocr_results
    cap = cv2.VideoCapture(video_path)
    for frame_num, stt_text in tasks:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            ocr_results = []
            try:
                ocr_results = extract_full_ocr_results(frame, lang)
            except Exception as e:
                logging.error(f"OCR error on frame {frame_num}: {e}")
            
            # Send frame and results to saver. OCR results contain bboxes and text.
            result_queue.put((frame_num, frame, {"stt_text": stt_text, "ocr_results": ocr_results}))
    
    cap.release()
