"""Configuration module for video processor."""
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Suppress FFmpeg warnings in environment
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'

# Default configuration values
DEFAULT_TEXT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_BATCH_SIZE = 8
DEFAULT_NUM_WORKERS = 4
DEFAULT_FRAME_INTERVAL = 30
DEFAULT_SCENE_THRESHOLD = 30.0
DEFAULT_MIN_SCENE_LEN = 15
DEFAULT_KEYFRAMES_PER_SCENE = 3
DEFAULT_ONLY_WITH_TEXT = True
DEFAULT_OCR_ENGINE = "easyocr"
DEFAULT_WHISPER_MODEL = "mlx-community/whisper-large-v3-mlx"
DEFAULT_STT_LANG = "en"