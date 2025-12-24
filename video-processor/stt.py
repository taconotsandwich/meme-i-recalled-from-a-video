"""STT module for transcribing audio from video frames."""
import os
import subprocess
import logging
import torch
from tqdm import tqdm
import mlx_whisper
from opencc import OpenCC
from huggingface_hub import snapshot_download

def extract_audio(video_path, audio_output_path, duration=None):
    """Extract audio from video file using ffmpeg."""
    logging.info(f"Extracting audio to {audio_output_path}...")
    try:
        # We use -map 0:a:0 to ensure we only get the first audio stream
        # and -af aresample=async=1 to handle sync issues in corrupted files
        cmd = [
            "ffmpeg", "-y", "-err_detect", "ignore_err", "-i", video_path,
            "-map", "0:a:0", "-vn"
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
            
        cmd.extend([
            "-acodec", "libmp3lame", 
            "-ar", "16000", "-ac", "1", "-af", "aresample=async=1",
            audio_output_path
        ])
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        # Fallback for extremely corrupted files: try to decode without advanced error detection
        logging.warning("Standard extraction failed, trying permissive fallback...")
        try:
            cmd = [
                "ffmpeg", "-y", "-i", video_path, "-vn"
            ]
            if duration:
                cmd.extend(["-t", str(duration)])
            cmd.extend([
                "-ar", "16000", "-ac", "1",
                audio_output_path
            ])
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError as e2:
            logging.error(f"Failed to extract audio: {e2.stderr.decode()}")
            return False

def transcribe_audio(audio_path, model_size="mlx-community/whisper-large-v3-mlx", device=None, lang="zh"):
    """
    Transcribe audio file using mlx-whisper.
    Biased towards Traditional Chinese if lang is 'zh'.
    """
    # model_size for mlx-whisper should usually be a path or repo name
    if model_size == "large-v3":
        model_size = "mlx-community/whisper-large-v3-mlx"
    elif model_size == "turbo":
        model_size = "mlx-community/whisper-large-v3-turbo"

    # Set prompt based on language variety
    initial_prompt = None
    if lang == "zh":
        initial_prompt = "以下是繁體中文的內容："
    elif lang in ["zh-cn", "zh-hans"]:
        initial_prompt = "以下是简体中文的内容："

    logging.info(f"Preparing model: {model_size}...")
    try:
        # This will return the local path if it exists, and only check the network if needed.
        # By getting the local path first, mlx_whisper won't try to download/check it again.
        model_path = snapshot_download(repo_id=model_size, local_files_only=False)
    except Exception as e:
        logging.warning(f"Could not check for model updates, trying to use cache: {e}")
        model_path = snapshot_download(repo_id=model_size, local_files_only=True)

    logging.info(f"Starting transcription with mlx-whisper (Lang: {lang})...")
    
    # We enable verbose to show progress, but hallucinations are filtered later
    output = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_path,
        language=lang,
        verbose=True,
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
        logprob_threshold=-1.0,
        initial_prompt=initial_prompt
    )

    segments = output.get("segments", [])
    results = []
    
    # Setup converter for guaranteed script matching
    converter = None
    if lang == "zh":
        converter = OpenCC('s2t') # Simplified to Traditional
    elif lang in ["zh-cn", "zh-hans"]:
        converter = OpenCC('t2s') # Traditional to Simplified

    last_text = ""
    last_start = -1
    
    for segment in segments:
        text = segment["text"].strip()
        start = segment["start"]
        end = segment["end"]
        duration = end - start
        
        # 1. Filter out zero-duration segments or segments with exact same start as previous
        if duration <= 0 or start == last_start:
            continue
            
        # 2. Detect and break repetitive hallucination loops
        # If the same short text repeats, it's almost certainly a hallucination
        if text == last_text and (duration < 5.0 or len(text) < 5):
            continue

        if converter:
            text = converter.convert(text)
            
        results.append({
            "start": start,
            "end": end,
            "text": text
        })
        last_text = text
        last_start = start
        
    return results