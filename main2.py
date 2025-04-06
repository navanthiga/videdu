# main.py
import streamlit as st
import sys
import os
import datetime
import json
import builtins
import re
from db_utils import log_activity, log_video_watched, log_quiz_attempt
from chatbot import get_ai_response, get_fallback_response, get_user_learning_context, init_chatbot_db, save_chat_to_db
from forum import community_forum_page, init_forum_db
from db_utils import init_challenges_tables, migrate_challenges_tables
from learning_path import learning_path_page, inject_custom_css, load_nltk_resources
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
from chatbot import init_chatbot_db

# Store original print and markdown functions
original_print = builtins.print
original_markdown = st.markdown

# Function to hide API keys in print output
def safe_print(*args, **kwargs):
    # Check if any of the args contain API key pattern
    filtered_args = []
    for arg in args:
        if isinstance(arg, str) and re.search(r'(api[_-]?key|apikey|key)[=:]\s*[\w\-]+', arg, re.IGNORECASE):
            # Replace the API key with asterisks
            filtered_arg = re.sub(r'(api[_-]?key|apikey|key)[=:]\s*([\w\-]+)', r'\1=********', arg, flags=re.IGNORECASE)
            filtered_args.append(filtered_arg)
        else:
            filtered_args.append(arg)
    
    # Call the original print with filtered args
    return original_print(*filtered_args, **kwargs)

# Function to hide API keys in markdown
def safe_markdown(text, **kwargs):
    if isinstance(text, str):
        # Hide API key related messages
        if re.search(r'(api[_-]?key|apikey|key)[=:]\s*[\w\-]+', text, re.IGNORECASE) or "Using API" in text:
            return
    return original_markdown(text, **kwargs)

# Replace built-in print and markdown functions with safe versions
builtins.print = safe_print
st.markdown = safe_markdown

# Expander-based corner chat
def create_corner_chat():
    # Add custom CSS to position and style the expander like a chat button
    st.markdown("""
    <style>
    /* Style the chat expander to look like a floating button */
    div[data-testid="stExpander"] {
        position: fixed !important;
        bottom: 20px !important;
        right: 20px !important;
        width: auto !important;
        min-width: 60px !important;
        max-width: 350px !important;
        background-color: transparent !important;
        border: none !important;
        z-index: 9999 !important;
    }
    
    /* Style the expander header to look like a chat button when collapsed */
    div[data-testid="stExpander"] > div:first-child {
        background-color: #4CAF50 !important;
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
        padding: 0 !important;
    }
    
    /* Style the expander header to look like a chat box header when expanded */
    div[data-testid="stExpander"][aria-expanded="true"] > div:first-child {
        background-color: #4CAF50 !important;
        border-radius: 10px 10px 0 0 !important;
        width: 100% !important;
        height: auto !important;
        padding: 10px 15px !important;
    }
    
    /* Hide the expander chevron icon */
    div[data-testid="stExpander"] svg {
        display: none !important;
    }
    
    /* Style the collapsed button content */
    div[data-testid="stExpander"] > div:first-child p {
        margin: 0 !important;
        font-size: 24px !important;
        color: white !important;
    }
    
    /* Style the expanded header content */
    div[data-testid="stExpander"][aria-expanded="true"] > div:first-child p {
        font-size: 16px !important;
        font-weight: 500 !important;
    }
    
    /* Style the content container when expanded */
    div[data-testid="stExpander"] > div:last-child {
        background-color: white !important;
        border-radius: 0 0 10px 10px !important;
        max-height: 500px !important;
        overflow-y: auto !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
    }
    
    /* Make chat input stick to bottom */
    div[data-testid="stExpander"] .stChatInputContainer {
        position: sticky;
        bottom: 0;
        background-color: white;
        padding: 10px 0;
        border-top: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create an expander that looks like a chat button
    with st.expander("💬"):
        # Initialize messages if not exist
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hi there! How can I help you with Python today?"}
            ]
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Chat input 
        if prompt := st.chat_input("Ask me anything about Python..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get the response
            with st.chat_message("assistant"):
                # Get user's learning context if available
                user_id = st.session_state.user["id"] if "user" in st.session_state else None
                context = get_user_learning_context(user_id) if user_id else ""
                
                # Generate response
                try:
                    with st.spinner("Thinking..."):
                        response = get_ai_response(prompt, context)
                except Exception as e:
                    response = get_fallback_response(prompt)
                
                st.write(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Save to database if user is logged in
            if user_id:
                save_chat_to_db(user_id, prompt, response)

def handle_coding_challenges():
    from code_ch import coding_challenge_page
    
    # Initialize database
    if not init_challenges_tables():
        st.error("Failed to initialize challenges database tables")
        return
    
    if not migrate_challenges_tables():
        st.error("Failed to migrate challenges database tables")
        return
    
    try:
        # Show challenge page
        coding_challenge_page()
    except Exception as e:
        st.error(f"Error loading coding challenges: {str(e)}")
        st.error("Please try refreshing the page.")

# Set page config for the entire app
st.set_page_config(
    page_title="Videdu",
    page_icon="🐍",
    layout="wide"
)

# Custom CSS to hide the login page once logged in and hide the "API key: xxx" display
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hide API key display - comprehensive selectors */
    div.css-1544g2n.e1fqkh3o4 p:first-child,
    div.stMarkdown p:contains("Using API key:"),
    p:contains("Using API key:"),
    p:contains("API key:"),
    div[data-testid="stMarkdownContainer"] p:contains("API key"),
    div[data-testid="stMarkdownContainer"] p:contains("Using API"),
    div.element-container div[data-testid="stMarkdownContainer"] p:contains("Using API key:"),
    div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"] {
        display: none !important;
    }
    
    /* Hide entire blocks that might contain API key */
    div.element-container:has(div[data-testid="stMarkdownContainer"] p:contains("API key")) {
        display: none !important;
    }
    
    /* Logo styling */
    .logo-container {
        display: flex;
        align-items: center;
        padding: 10px 0;
    }
    .logo-container img {
        width: 120px;
        margin-right: 15px;
    }
    .logo-container h2 {
        color: #1E3A8A;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize chatbot database tables
init_chatbot_db()

# Initialize forum database tables
init_forum_db()

# Initialize session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = "dashboard"  # Default to dashboard

# Initialize auth status and user in session state
if 'auth_status' not in st.session_state:
    st.session_state.auth_status = False
if 'user' not in st.session_state:
    st.session_state.user = None

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
if 'api_key_validated' not in st.session_state:
    st.session_state.api_key_validated = False

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

def navigate_to_forum():
    st.session_state.page = "community_forum"

def navigate_to_challenges():
    st.session_state.page = "coding_challenges"

def navigate_to_peer_collaboration():
    st.session_state.page = "peer_collaboration"

# Add this with your other navigation functions
def navigate_to_learning_path():
    st.session_state.page = "learning_path"

# Auto-load and validate the API key (silently)
api_key = os.getenv("GEMINI_API_KEY")
if api_key and not st.session_state.api_key_validated:
    if setup_gemini_api(api_key):
        st.session_state.api_key_valid = True
        st.session_state.api_key_validated = True
    else:
        # We don't show errors here, will handle elsewhere if needed
        st.session_state.api_key_valid = False

# Authentication check and main content
if not st.session_state.auth_status or st.session_state.user is None:
    # Display the welcome page
    st.title("Welcome to Videdu")
    st.markdown("#### Your AI-powered Python learning platform")
    
    # Call the login_page function
    is_authenticated = login_page()
    
    # If authentication is successful, update the session state
    if is_authenticated and st.session_state.user is not None:
        st.session_state.auth_status = True
        st.rerun()
else:
    # Add the corner chat widget instead of setup_chatbot
    create_corner_chat()
    
    # Sidebar for navigation and configuration
    with st.sidebar:
        # Logo and title
        st.markdown("""
        <div class="logo-container">
            <img src="https://raw.githubusercontent.com/your-repo/videdu/main/logo.jpeg" alt="Videdu Logo">
            <h2>Videdu</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # User info
        st.write(f"Logged in as: **{st.session_state.user['username']}**")
        
        # Navigation buttons
        st.header("Navigation")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Dashboard", use_container_width=True, 
                        help="View your learning progress"):
                navigate_to_dashboard()
        with col2:
            if st.button("🚀 Learning Path", use_container_width=True, 
                        help="Get personalized learning recommendations"):
                navigate_to_learning_path()

        col3, col4 = st.columns(2)
        with col3:
            if st.button("📹 Videos", use_container_width=True, 
                        help="Create educational Python tutorial videos"):
                navigate_to_video_generator()
        with col4:
            if st.button("📝 Quizzes", use_container_width=True,
                        help="Test your Python knowledge with adaptive quizzes"):
                navigate_to_quiz_generator()

        # Add a new row for coding challenges and community forum
        col5, col6 = st.columns(2)
        with col5:
            if st.button("🎮 Challenges", use_container_width=True,
                        help="Solve fun coding challenges and earn badges"):
                navigate_to_challenges()
        with col6:
            if st.button("💬 Forum", use_container_width=True,
                        help="Discuss topics with the Python learning community"):
                navigate_to_forum()

        # Add a new row for Peers
        col7, _ = st.columns(2)
        with col7:
            if st.button("👥 Peers", use_container_width=True,
                        help="Collaborate with peers for group study"):
                navigate_to_peer_collaboration()
        
        # Logout button
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            # Log logout activity
            if 'user' in st.session_state:
                log_activity(st.session_state.user['id'], "logout")
            
            # Clear session state
            st.session_state.user = None
            st.session_state.auth_status = False
            for key in list(st.session_state.keys()):
                if key not in ["auth_status"]:
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
        
        # Show warning if API key is invalid
        if not st.session_state.api_key_valid:
            st.error("API key is missing or invalid. Please contact the administrator.")
        
        # Topic input in the main area instead of sidebar
        topic = st.text_input("Python Topic", 
                              help="Enter a Python topic (e.g., 'Python Lists', 'Recursion', 'For Loops')")
        
        # Generate button in the main area
        generate_button = st.button("Generate Tutorial", 
                                 disabled=not (st.session_state.api_key_valid and topic))
        
        # Handle video generation logic
        if generate_button and topic:
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
            1. Enter a Python topic you want to learn about
            2. Click 'Generate Tutorial' to create your custom tutorial video
            3. Wait for the process to complete (it may take a few minutes)
            4. Download your finished tutorial video
            
            This app will create a complete educational video with:
            - A detailed script explaining the Python topic
            - Animated visualizations created with Manim
            - Professional voice narration
            """)

    elif st.session_state.page == "quiz_generator":
        # Quiz Generator Interface
        st.title(f"📚 Adaptive Python Quiz Generator")
        
        if not st.session_state.questions:
            st.markdown("""
            Test your knowledge with our adaptive Python quiz generator.
            
            1. Enter a Python topic below
            2. Click 'Start Assessment' to generate quiz questions
            3. Answer the questions to test your understanding
            4. Receive personalized feedback and performance analysis
            """)
            
            # Topic input and Start button in the main area
            topic = st.text_input("Python Topic", 
                                 help="Enter a Python topic (e.g., 'Python Lists', 'Recursion', 'For Loops')")
            
            if st.button("Start Assessment", disabled=not topic):
                st.session_state.topic = topic
                start_assessment()
                # Log the quiz start
                log_activity(
                    st.session_state.user['id'], 
                    "quiz_started", 
                    {"topic": topic}
                )
                st.rerun()
        
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

    elif st.session_state.page == "peer_collaboration":
        # Import the peer collaboration module
        from peer_collaboration import peer_collaboration_page
        # Display the peer collaboration page
        peer_collaboration_page()

    elif st.session_state.page == "community_forum":
        # Initialize forum database
        init_forum_db()
        
        # Display the community forum
        community_forum_page()

    elif st.session_state.page == "coding_challenges":
        # Handle challenges through the separate function
        handle_coding_challenges()

    # Add this with your other conditional page renders
    elif st.session_state.page == "learning_path":
        # Call the learning path page function
        learning_path_page()

    # Footer
    st.markdown("---")
    st.markdown("<div style='text-align: center;'>Made with ❤️ by Videdu</div>", unsafe_allow_html=True)