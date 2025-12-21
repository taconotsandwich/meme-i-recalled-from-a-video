"""Scene detection module for video analysis."""
import os
import logging
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector


def detect_scenes(video_path, threshold=30.0, min_scene_len=15):
    """
    Detect scene changes in a video using PySceneDetect.

    Args:
        video_path (str): Path to the video file
        threshold (float): Threshold for scene detection sensitivity (default: 30.0)
        min_scene_len (int): Minimum scene length in frames (default: 15)

    Returns:
        list: List of (start_frame, end_frame) tuples for each scene
    """
    logging.info(f"Detecting scenes in {os.path.basename(video_path)}")

    # Open video
    video = open_video(video_path)
    scene_manager = SceneManager()

    # Add content detector
    scene_manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))

    # Detect scenes
    scene_manager.detect_scenes(video)

    # Get a scene list
    scene_list = scene_manager.get_scene_list()

    # Convert to frame numbers
    scenes = []
    for scene in scene_list:
        start_frame = scene[0].get_frames()
        end_frame = scene[1].get_frames()
        scenes.append((start_frame, end_frame))

    logging.info(f"Detected {len(scenes)} scenes")
    return scenes


def calculate_scene_keyframes(scenes, keyframes_per_scene=3, fps=30):
    """
    Calculate key frames for each scene to extract.

    Args:
        scenes (list): List of (start_frame, end_frame) tuples
        keyframes_per_scene (int): Number of keyframes to extract per scene
        fps (float): Video frame rate

    Returns:
        list: List of frame numbers to extract
    """
    keyframes = []

    for start_frame, end_frame in scenes:
        scene_length = end_frame - start_frame

        if scene_length <= keyframes_per_scene:
            # If a scene is short, extract all frames
            keyframes.extend(range(start_frame, end_frame))
        else:
            # Extract keyframes at regular intervals within the scene
            interval = scene_length // keyframes_per_scene
            for i in range(keyframes_per_scene):
                frame_num = start_frame + (i * interval)
                if frame_num < end_frame:
                    keyframes.append(frame_num)

    return sorted(keyframes)
