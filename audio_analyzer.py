# backend/content_generator/audio_analyzer.py
import math
import os

def analyze_audio(audio_path):
    """
    A simple audio analyzer that estimates segments based on text length.
    """
    # For simplicity, we'll divide the audio into 3-5 segments
    # A more advanced implementation would analyze the audio file
    
    # Estimate duration: gTTS typically reads at ~150 words per minute
    with open(audio_path, 'rb') as f:
        # Get file size in MB as a rough estimate of length
        file_size = os.path.getsize(audio_path) / (1024 * 1024)
        
    # Rough estimate: 1MB of MP3 ~ 1 minute of audio
    estimated_duration = max(file_size * 60, 60)  # At least 60 seconds
    
    # Create segments (roughly dividing the content into 3-5 parts)
    num_segments = min(max(3, math.ceil(estimated_duration / 20)), 5)
    segment_duration = estimated_duration / num_segments
    
    segments = []
    for i in range(num_segments):
        start_time = i * segment_duration
        end_time = (i + 1) * segment_duration if i < num_segments - 1 else estimated_duration
        segments.append({
            "start": start_time,
            "end": end_time,
            "duration": end_time - start_time
        })
    
    return {
        "duration": estimated_duration,
        "segments": segments
    }