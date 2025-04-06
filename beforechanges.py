import streamlit as st
import sys
import os

# Ensure the current directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions from your existing files
from g_video_gen import (
    setup_gemini_api, generate_script, generate_manim_code, 
    render_manim_animation, generate_audio, merge_video_audio
)
from s_quiz import (
    generate_mcqs, start_assessment, submit_answer, restart,
    analyze_performance, display_performance_charts, get_feedback_and_resources
)

# Set page config for the entire app
st.set_page_config(
    page_title="Python Learning Platform",
    page_icon="🐍",
    layout="wide"
)

# Initialize session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = "video_generator"

# Session state initialization for video generator
if 'script' not in st.session_state:
    st.session_state.script = None
if 'manim_code' not in st.session_state:
    st.session_state.manim_code = None
if 'video_path' not in st.session_state:
    st.session_state.video_path = None
if 'audio_path' not in st.session_state:
    st.session_state.audio_path = None
if 'final_video_path' not in st.session_state:
    st.session_state.final_video_path = None
if 'api_key_valid' not in st.session_state:
    st.session_state.api_key_valid = False

# Session state initialization for quiz generator
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'completed' not in st.session_state:
    st.session_state.completed = False
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'topic' not in st.session_state:
    st.session_state.topic = ""
if 'question_categories' not in st.session_state:
    st.session_state.question_categories = {}
if 'time_taken' not in st.session_state:
    st.session_state.time_taken = {}

# Navigation functions
def navigate_to_video_generator():
    st.session_state.page = "video_generator"

def navigate_to_quiz_generator():
    st.session_state.page = "quiz_generator"

# Sidebar for navigation and configuration
with st.sidebar:
    st.title("Python Learning Platform")
    st.markdown("---")
    
    # Navigation buttons
    st.header("Navigation")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📹 Video Generator", use_container_width=True, 
                    help="Create educational Python tutorial videos"):
            navigate_to_video_generator()
    with col2:
        if st.button("📝 Quiz Generator", use_container_width=True,
                    help="Test your Python knowledge with adaptive quizzes"):
            navigate_to_quiz_generator()
    
    st.markdown("---")
    
    # Configuration section
    st.header("Configuration")
    
    # API Key input
    api_key = st.text_input("Gemini API Key", type="password", help="Get your Gemini API key from Google AI Studio")
    
    if st.button("Validate API Key"):
        if api_key:
            if setup_gemini_api(api_key):
                st.session_state.api_key_valid = True
                st.success("API key is valid!")
            else:
                st.session_state.api_key_valid = False
                st.error("Invalid API key. Please check and try again.")
        else:
            st.warning("Please enter an API key.")
    
    # Topic input - shared between both tools
    topic = st.text_input("Python Topic",  help="Enter a Python topic (e.g., 'Python Lists', 'Recursion', 'For Loops')")
    
    # Conditional buttons based on the current page
    if st.session_state.page == "video_generator":
        generate_button = st.button("Generate Tutorial", disabled=not (st.session_state.api_key_valid and topic), use_container_width=True)
    else:
        if st.button("Start Assessment", 
                    disabled=not (st.session_state.api_key_valid and topic),
                    use_container_width=True):
            st.session_state.topic = topic
            start_assessment()

# Main content area - conditional rendering based on current page
if st.session_state.page == "video_generator":
    # Video Generator Interface
    st.title("🐍 Python Tutorial Video Generator")
    st.markdown("""
    This application generates educational Python tutorial videos using AI. 
    It creates a script, Manim animation, and voice narration for any Python topic you choose.
    """)
    
    # Handle video generation logic
    if 'generate_button' in locals() and generate_button and topic:
        # Reset session state for a new generation
        st.session_state.script = None
        st.session_state.manim_code = None
        st.session_state.video_path = None
        st.session_state.audio_path = None
        st.session_state.final_video_path = None
        
        # Step 1: Generate script
        st.header("Step 1: Generate Script")
        st.session_state.script = generate_script(topic)
        
        if st.session_state.script:
            st.success("Script generated successfully!")
            st.subheader("Generated Script")
            st.text_area("Script", st.session_state.script, height=300)
            
            # Step 2: Generate Manim code
            st.header("Step 2: Generate Animation Code")
            st.session_state.manim_code = generate_manim_code(topic, st.session_state.script)
            
            if st.session_state.manim_code:
                st.success("Animation code generated successfully!")
                st.subheader("Generated Manim Code")
                st.code(st.session_state.manim_code, language="python")
                
                # Step 3: Render animation
                st.header("Step 3: Render Animation")
                st.session_state.video_path = render_manim_animation(st.session_state.manim_code, topic)
                
                if st.session_state.video_path:
                    st.success("Animation rendered successfully!")
                    st.subheader("Generated Animation")
                    st.video(st.session_state.video_path)
                    
                    # Step 4: Generate audio
                    st.header("Step 4: Generate Voice Narration")
                    st.session_state.audio_path = generate_audio(st.session_state.script, topic)
                    
                    if st.session_state.audio_path:
                        st.success("Voice narration generated successfully!")
                        st.subheader("Generated Audio")
                        st.audio(st.session_state.audio_path)
                        
                        # Step 5: Merge video and audio
                        st.header("Step 5: Create Final Tutorial")
                        st.session_state.final_video_path = merge_video_audio(
                            st.session_state.video_path, 
                            st.session_state.audio_path, 
                            topic
                        )
                        
                        if st.session_state.final_video_path:
                            st.success("🎉 Tutorial video created successfully!")
                            st.subheader("Final Tutorial Video")
                            st.video(st.session_state.final_video_path)
                            
                            # Download button
                            with open(st.session_state.final_video_path, "rb") as file:
                                st.download_button(
                                    label="Download Tutorial Video",
                                    data=file,
                                    file_name=f"{topic.replace(' ', '_')}_tutorial.mp4",
                                    mime="video/mp4"
                                )
                            
                            # Quiz suggestion
                            st.info("Want to test your knowledge on this topic? Try our quiz generator!")
                            if st.button("Generate Quiz on This Topic"):
                                st.session_state.topic = topic
                                navigate_to_quiz_generator()
                                start_assessment()
                                st.rerun()
                        else:
                            st.error("Failed to merge video and audio.")
                    else:
                        st.error("Failed to generate audio narration.")
                else:
                    st.error("Failed to render animation.")
            else:
                st.error("Failed to generate animation code.")
        else:
            st.error("Failed to generate script.")

    # If nothing has been generated yet, show instructions
    if not st.session_state.script:
        st.info("""
        ### How to use this app:
        1. Enter your Gemini API key in the sidebar
        2. Enter a Python topic you want to learn about
        3. Click 'Generate Tutorial' to create your custom tutorial video
        4. Wait for the process to complete (it may take a few minutes)
        5. Download your finished tutorial video
        
        This app will create a complete educational video with:
        - A detailed script explaining the Python topic
        - Animated visualizations created with Manim
        - Professional voice narration
        """)

else:
    # Quiz Generator Interface
    st.title(f"📚 Adaptive Python Quiz Generator")
    
    if not st.session_state.questions:
        st.markdown("""
        Test your knowledge with our adaptive Python quiz generator.
        
        1. Enter a Python topic in the sidebar
        2. Click 'Start Assessment' to generate quiz questions
        3. Answer the questions to test your understanding
        4. Receive personalized feedback and performance analysis
        """)
    
    # Display quiz content
    if st.session_state.questions:
        st.title(f"📚 Adaptive Assessment: {st.session_state.topic}")
        
        if not st.session_state.completed:
            # Display current question
            q_idx = st.session_state.current_question
            question_data = st.session_state.questions[q_idx]
            
            st.subheader(f"Question {q_idx + 1} of {len(st.session_state.questions)}")
            st.write(question_data["question"])
            
            # Display category
            category = question_data.get("category", "General")
            st.caption(f"Category: {category}")
            
            # Create a unique key for each radio button
            radio_key = f"radio_{q_idx}"
            
            # Initialize the answer in session state if not present
            if radio_key not in st.session_state:
                st.session_state[radio_key] = None
                
            # Display options
            selected_option = st.radio(
                "Select your answer:",
                question_data["options"],
                key=radio_key
            )
            
            # Store the answer in session state
            st.session_state.answers[q_idx] = selected_option
            
            # Submit button
            if st.button("Submit Answer", key=f"submit_{q_idx}"):
                submit_answer(q_idx)
                st.rerun()
                
            # Display progress
            progress = (q_idx + 1) / len(st.session_state.questions)
            st.progress(progress)
            
        else:
            # Quiz completed - show results
            st.success("### Assessment Complete! 🎉")
            st.write(f"Your score: {st.session_state.score}/{len(st.session_state.questions)}")
            
            percentage = (st.session_state.score / len(st.session_state.questions)) * 100
            
            if percentage == 100:
                st.balloons()
                st.success("🎯 Perfect Score! Excellent work!")
            elif percentage >= 70:
                st.info("👍 Good job! Keep practicing!")
            else:
                st.warning("📚 You might need more practice on this topic.")
                
            # Analyze performance by category
            performance, strengths, weaknesses = analyze_performance()
            
            # Display performance charts
            st.subheader("📊 Performance Analysis")
            display_performance_charts(performance)
            
            # Generate personalized feedback
            feedback = get_feedback_and_resources(strengths, weaknesses, st.session_state.topic)
            st.markdown(feedback)
            
            # Review answers
            st.subheader("📝 Review Your Answers")
            for i, q in enumerate(st.session_state.questions):
                with st.expander(f"Question {i+1} - {q.get('category', 'General')}"):
                    st.write(q["question"])
                    user_answer = st.session_state.answers.get(i, "Not answered")
                    
                    if user_answer == q["correct_answer"]:
                        st.success(f"Your answer: {user_answer} ✅")
                    else:
                        st.error(f"Your answer: {user_answer} ❌")
                        st.info(f"Correct answer: {q['correct_answer']}")
            
            # Navigation options
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start New Assessment", key="main_new_assessment"):
                    restart()
                    st.rerun()
            with col2:
                if st.button("Create Tutorial Video on This Topic"):
                    navigate_to_video_generator()
                    st.rerun()

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit, Gemini AI, Manim, and gTTS")
#\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

# main.py
import streamlit as st
import sys
import os
import datetime
import json

# Ensure the current directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions from your existing files
from g_video_gen import (
    setup_gemini_api, generate_script, generate_manim_code, 
    render_manim_animation, generate_audio, merge_video_audio
)
from s_quiz import (
    generate_mcqs, start_assessment, submit_answer, restart,
    analyze_performance, display_performance_charts, get_feedback_and_resources
)
from auth import login_page
from dashboard import dashboard_page
from db_utils import log_activity, log_video_watched, log_quiz_attempt

# Set page config for the entire app
st.set_page_config(
    page_title="Python Learning Platform",
    page_icon="🐍",
    layout="wide"
)

# Initialize session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = "dashboard"  # Default to dashboard

# Session state initialization for video generator
if 'script' not in st.session_state:
    st.session_state.script = None
if 'manim_code' not in st.session_state:
    st.session_state.manim_code = None
if 'video_path' not in st.session_state:
    st.session_state.video_path = None
if 'audio_path' not in st.session_state:
    st.session_state.audio_path = None
if 'final_video_path' not in st.session_state:
    st.session_state.final_video_path = None
if 'api_key_valid' not in st.session_state:
    st.session_state.api_key_valid = False

# Session state initialization for quiz generator
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'completed' not in st.session_state:
    st.session_state.completed = False
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'topic' not in st.session_state:
    st.session_state.topic = ""
if 'question_categories' not in st.session_state:
    st.session_state.question_categories = {}
if 'time_taken' not in st.session_state:
    st.session_state.time_taken = {}

# Navigation functions
def navigate_to_dashboard():
    st.session_state.page = "dashboard"

def navigate_to_video_generator():
    st.session_state.page = "video_generator"

def navigate_to_quiz_generator():
    st.session_state.page = "quiz_generator"

# First, check if the user is authenticated
is_authenticated = login_page()

# Only show the main content if the user is authenticated
if is_authenticated:
    # Sidebar for navigation and configuration
    with st.sidebar:
        st.title("Python Learning Platform")
        st.markdown("---")
        
        # User info
        st.write(f"Logged in as: **{st.session_state.user['username']}**")
        
        # Navigation buttons
        st.header("Navigation")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 Dashboard", use_container_width=True, 
                        help="View your learning progress"):
                navigate_to_dashboard()
        with col2:
            if st.button("📹 Videos", use_container_width=True, 
                        help="Create educational Python tutorial videos"):
                navigate_to_video_generator()
        with col3:
            if st.button("📝 Quizzes", use_container_width=True,
                        help="Test your Python knowledge with adaptive quizzes"):
                navigate_to_quiz_generator()
        
        st.markdown("---")
        
        # Configuration section
        st.header("Configuration")
        
        # API Key input
        api_key = st.text_input("Gemini API Key", type="password", 
                               help="Get your Gemini API key from Google AI Studio")
        
        if st.button("Validate API Key"):
            if api_key:
                if setup_gemini_api(api_key):
                    st.session_state.api_key_valid = True
                    st.success("API key is valid!")
                else:
                    st.session_state.api_key_valid = False
                    st.error("Invalid API key. Please check and try again.")
            else:
                st.warning("Please enter an API key.")
        
        # Topic input - shared between both tools
        topic = st.text_input("Python Topic", 
                             help="Enter a Python topic (e.g., 'Python Lists', 'Recursion', 'For Loops')")
        
        # Conditional buttons based on the current page
        if st.session_state.page == "video_generator":
            generate_button = st.button("Generate Tutorial", 
                                       disabled=not (st.session_state.api_key_valid and topic),
                                       use_container_width=True)
        elif st.session_state.page == "quiz_generator":
            if st.button("Start Assessment", 
                        disabled=not (st.session_state.api_key_valid and topic),
                        use_container_width=True):
                st.session_state.topic = topic
                start_assessment()
                # Log the quiz start
                log_activity(
                    st.session_state.user['id'], 
                    "quiz_started", 
                    {"topic": topic}
                )
        
        # Logout button
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            # Log logout activity
            if 'user' in st.session_state:
                log_activity(st.session_state.user['id'], "logout")
            
            # Clear session state
            st.session_state.user = None
            for key in list(st.session_state.keys()):
                if key != "auth_status":
                    del st.session_state[key]
            
            st.rerun()

    # Main content area - conditional rendering based on current page
    if st.session_state.page == "dashboard":
        dashboard_page()
        
    elif st.session_state.page == "video_generator":
        # Video Generator Interface
        st.title("🐍 Python Tutorial Video Generator")
        st.markdown("""
        This application generates educational Python tutorial videos using AI. 
        It creates a script, Manim animation, and voice narration for any Python topic you choose.
        """)
        
        # Handle video generation logic
        if 'generate_button' in locals() and generate_button and topic:
            # Log video generation started
            log_activity(
                st.session_state.user['id'], 
                "video_generation_started", 
                {"topic": topic}
            )
            
            # Reset session state for a new generation
            st.session_state.script = None
            st.session_state.manim_code = None
            st.session_state.video_path = None
            st.session_state.audio_path = None
            st.session_state.final_video_path = None
            
            # Step 1: Generate script
            st.header("Step 1: Generate Script")
            st.session_state.script = generate_script(topic)
            
            if st.session_state.script:
                st.success("Script generated successfully!")
                st.subheader("Generated Script")
                st.text_area("Script", st.session_state.script, height=300)
                
                # Step 2: Generate Manim code
                st.header("Step 2: Generate Animation Code")
                st.session_state.manim_code = generate_manim_code(topic, st.session_state.script)
                
                if st.session_state.manim_code:
                    st.success("Animation code generated successfully!")
                    st.subheader("Generated Manim Code")
                    st.code(st.session_state.manim_code, language="python")
                    
                    # Step 3: Render animation
                    st.header("Step 3: Render Animation")
                    st.session_state.video_path = render_manim_animation(st.session_state.manim_code, topic)
                    
                    if st.session_state.video_path:
                        st.success("Animation rendered successfully!")
                        st.subheader("Generated Animation")
                        st.video(st.session_state.video_path)
                        
                        # Step 4: Generate audio
                        st.header("Step 4: Generate Voice Narration")
                        st.session_state.audio_path = generate_audio(st.session_state.script, topic)
                        
                        if st.session_state.audio_path:
                            st.success("Voice narration generated successfully!")
                            st.subheader("Generated Audio")
                            st.audio(st.session_state.audio_path)
                            
                            # Step 5: Merge video and audio
                            st.header("Step 5: Create Final Tutorial")
                            st.session_state.final_video_path = merge_video_audio(
                                st.session_state.video_path, 
                                st.session_state.audio_path, 
                                topic
                            )
                            
                            if st.session_state.final_video_path:
                                st.success("🎉 Tutorial video created successfully!")
                                st.subheader("Final Tutorial Video")
                                st.video(st.session_state.final_video_path)
                                
                                # Log video completion in database
                                log_video_watched(
                                    st.session_state.user['id'],
                                    topic,
                                    100
                                )
                                
                                # Download button
                                with open(st.session_state.final_video_path, "rb") as file:
                                    st.download_button(
                                        label="Download Tutorial Video",
                                        data=file,
                                        file_name=f"{topic.replace(' ', '_')}_tutorial.mp4",
                                        mime="video/mp4"
                                    )
                                
                                # Quiz suggestion
                                st.info("Want to test your knowledge on this topic? Try our quiz generator!")
                                if st.button("Generate Quiz on This Topic"):
                                    st.session_state.topic = topic
                                    navigate_to_quiz_generator()
                                    start_assessment()
                                    st.rerun()
                            else:
                                st.error("Failed to merge video and audio.")
                        else:
                            st.error("Failed to generate audio narration.")
                    else:
                        st.error("Failed to render animation.")
                else:
                    st.error("Failed to generate animation code.")
            else:
                st.error("Failed to generate script.")

        # If nothing has been generated yet, show instructions
        if not st.session_state.script:
            st.info("""
            ### How to use this app:
            1. Enter your Gemini API key in the sidebar
            2. Enter a Python topic you want to learn about
            3. Click 'Generate Tutorial' to create your custom tutorial video
            4. Wait for the process to complete (it may take a few minutes)
            5. Download your finished tutorial video
            
            This app will create a complete educational video with:
            - A detailed script explaining the Python topic
            - Animated visualizations created with Manim
            - Professional voice narration
            """)

    else:  # quiz_generator page
        # Quiz Generator Interface
        st.title(f"📚 Adaptive Python Quiz Generator")
        
        if not st.session_state.questions:
            st.markdown("""
            Test your knowledge with our adaptive Python quiz generator.
            
            1. Enter a Python topic in the sidebar
            2. Click 'Start Assessment' to generate quiz questions
            3. Answer the questions to test your understanding
            4. Receive personalized feedback and performance analysis
            """)
        
        # Display quiz content
        if st.session_state.questions:
            st.title(f"📚 Adaptive Assessment: {st.session_state.topic}")
            
            if not st.session_state.completed:
                # Display current question
                q_idx = st.session_state.current_question
                question_data = st.session_state.questions[q_idx]
                
                st.subheader(f"Question {q_idx + 1} of {len(st.session_state.questions)}")
                st.write(question_data["question"])
                
                # Display category
                category = question_data.get("category", "General")
                st.caption(f"Category: {category}")
                
                # Create a unique key for each radio button
                radio_key = f"radio_{q_idx}"
                
                # Initialize the answer in session state if not present
                if radio_key not in st.session_state:
                    st.session_state[radio_key] = None
                    
                # Track time for this question
                if 'question_start_time' not in st.session_state:
                    st.session_state.question_start_time = datetime.datetime.now()
                    
                # Display options
                selected_option = st.radio(
                    "Select your answer:",
                    question_data["options"],
                    key=radio_key
                )
                
                # Store the answer in session state
                st.session_state.answers[q_idx] = selected_option
                
                # Submit button
                if st.button("Submit Answer", key=f"submit_{q_idx}"):
                    # Calculate time taken for this question
                    end_time = datetime.datetime.now()
                    time_taken = (end_time - st.session_state.question_start_time).total_seconds()
                    st.session_state.time_taken[q_idx] = time_taken
                    
                    # Reset timer for next question
                    st.session_state.question_start_time = datetime.datetime.now()
                    
                    submit_answer(q_idx)
                    
                    # Check if this was the last question
                    if q_idx == len(st.session_state.questions) - 1:
                        # Log quiz completion
                        log_quiz_attempt(
                            st.session_state.user['id'],
                            st.session_state.topic,
                            st.session_state.score,
                            len(st.session_state.questions),
                            {
                                "questions": [q for q in st.session_state.questions],
                                "answers": {str(k): v for k, v in st.session_state.answers.items()},
                                "categories": {str(k): v for k, v in st.session_state.question_categories.items()},
                                "time_taken": {str(k): v for k, v in st.session_state.time_taken.items()}
                            }
                        )
                    
                    st.rerun()
                    
                # Display progress
                progress = (q_idx + 1) / len(st.session_state.questions)
                st.progress(progress)
                
            else:
                # Quiz completed - show results
                st.success("### Assessment Complete! 🎉")
                st.write(f"Your score: {st.session_state.score}/{len(st.session_state.questions)}")
                
                percentage = (st.session_state.score / len(st.session_state.questions)) * 100
                
                if percentage == 100:
                    st.balloons()
                    st.success("🎯 Perfect Score! Excellent work!")
                elif percentage >= 70:
                    st.info("👍 Good job! Keep practicing!")
                else:
                    st.warning("📚 You might need more practice on this topic.")
                    
                # Analyze performance by category
                performance, strengths, weaknesses = analyze_performance()
                
                # Display performance charts
                st.subheader("📊 Performance Analysis")
                display_performance_charts(performance)
                
                # Generate personalized feedback
                feedback = get_feedback_and_resources(strengths, weaknesses, st.session_state.topic)
                st.markdown(feedback)
                
                # Review answers
                st.subheader("📝 Review Your Answers")
                for i, q in enumerate(st.session_state.questions):
                    with st.expander(f"Question {i+1} - {q.get('category', 'General')}"):
                        st.write(q["question"])
                        user_answer = st.session_state.answers.get(i, "Not answered")
                        
                        if user_answer == q["correct_answer"]:
                            st.success(f"Your answer: {user_answer} ✅")
                        else:
                            st.error(f"Your answer: {user_answer} ❌")
                            st.info(f"Correct answer: {q['correct_answer']}")
                
                # Navigation options
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Start New Assessment", key="main_new_assessment"):
                        restart()
                        st.rerun()
                with col2:
                    if st.button("Create Tutorial Video on This Topic"):
                        navigate_to_video_generator()
                        st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("Made with ❤️ using Streamlit, Gemini AI, Manim, and gTTS")