# backend/content_generator/audio_gen.py
from gtts import gTTS
import os

def generate_audio(script, output_path):
    """Generate an audio file from the given script."""
    tts = gTTS(text=script, lang='en', slow=False)
    tts.save(output_path)
    return output_path