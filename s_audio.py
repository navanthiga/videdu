import os
import re
import streamlit as st
from gtts import gTTS
from pydub import AudioSegment
import google.generativeai as genai
from config import API_KEY

# Set page config
st.set_page_config(
    page_title="Python Tutorial Generator",
    page_icon="🐍",
    layout="wide"
)

# App title and description
st.title("🐍 Python Tutorial Video Generator")
st.markdown("""
This application generates educational Python tutorial videos using AI. 
It creates a script, Manim animation, and voice narration for any Python topic you choose.
""")

# Configure Gemini API
def setup_gemini_api(api_key):
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {str(e)}")
        return False


# Generate script using Gemini API
def generate_script(topic):
    try:
        with st.spinner("Generating script with Gemini..."):
            model = genai.GenerativeModel('gemini-1.5-pro')
            generation_config = {
                "temperature": 0.2,
                "max_output_tokens": 8192
            }

            prompt = f"""
            Create a comprehensive educational script about {topic} for a Python educational video.

            Format the script exactly like this example:

            Welcome to Python Lists! ...

            Lists are ordered collections of items in Python.
            They can store multiple values of different types in a single variable.

            In Python, a list looks like this: ...

            numbers = [10, 20, 30, 40]

            Here, numbers is a list containing four values.
            We use square brackets [] to define a list.

            Lists are mutable, meaning you can change their content after creation.
            Let's explore lists in more detail!

            You can access elements in a list using their index position.
            Python uses zero-based indexing, so the first element is at index 0.

            [Continue with detailed explanation, examples, and use cases]

            Great job! ...

            Today, we learned:
            ✔ How to create and access lists
            ✔ How to modify list contents
            ✔ Common list operations and methods
            ✔ When to use lists in your programs

            Keep practicing, and you'll master Python in no time!

            Make sure the script:
            1. Has a clear introduction to the concept
            2. Provides code examples with explanations
            3. Covers all important aspects of {topic}
            4. Has a summary with 4-5 key points at the end
            5. Is detailed enough for a 5-7 minute educational video
            6. Uses simple language suitable for beginners
            7. Includes encouragement and motivation
            """

            response = model.generate_content(prompt, generation_config=generation_config)
            return response.text
    except Exception as e:
        st.error(f"Failed to generate script: {str(e)}")
        return f"Error generating script for {topic}. Please try again."


# Function to clean script for TTS
def clean_text_for_tts(text):
    # Remove common markdown symbols and other unwanted characters
    clean_text = re.sub(r'[\`#*~_>]', '', text)  # Removes backticks, #, *, ~, _, >
    clean_text = re.sub(r'\[.?\]\(.?\)', '', clean_text)  # Removes Markdown links
    clean_text = re.sub(r'.*?', '', clean_text, flags=re.S)  # Removes code blocks
    clean_text = re.sub(r'.*?', '', clean_text)  # Removes inline code
    return clean_text.strip()

# Function to split script into sections for TTS
def split_script_into_sections(script):
    paragraphs = [p for p in script.split('\n\n') if p.strip()]
    return {f"part{i+1}": section for i, section in enumerate(paragraphs)}

# Function to generate TTS audio from script
def generate_audio(script, topic):
    try:
        with st.spinner("Generating voice narration..."):
            audio_dir = "audio"
            os.makedirs(audio_dir, exist_ok=True)

            # Split the script into sections
            sections = split_script_into_sections(script)

            audio_files = []
            progress_bar = st.progress(0)
            total_sections = len(sections)

            for i, (section_name, section_text) in enumerate(sections.items()):
                section_filename = f"{audio_dir}/{topic.replace(' ', '')}{section_name}.mp3"

                # Clean the text for TTS
                clean_text = clean_text_for_tts(section_text)

                # Generate the audio
                tts = gTTS(text=clean_text, lang='en', slow=False)
                tts.save(section_filename)
                audio_files.append(section_filename)

                # Update progress
                progress_bar.progress((i + 1) / total_sections)

            # Combine all audio files
            combined_audio = AudioSegment.empty()
            for audio_file in audio_files:
                sound = AudioSegment.from_mp3(audio_file)
                combined_audio += sound

            # Export the combined audio
            final_audio_path = f"{audio_dir}/{topic.replace(' ', '_')}_complete.mp3"
            combined_audio.export(final_audio_path, format="mp3")

            # Display audio player and download button
            st.audio(final_audio_path, format="audio/mp3")
            st.download_button(
                label="Download Audio",
                data=open(final_audio_path, "rb"),
                file_name=f"{topic.replace(' ', '_')}_complete.mp3",
                mime="audio/mp3"
            )

            return final_audio_path

    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None