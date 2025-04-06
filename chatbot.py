# chatbot.py

import streamlit as st
import random
import time
import pandas as pd
import sqlite3
import os
from datetime import datetime
from db_utils import get_db_connection, log_activity
import google.generativeai as genai  # Import Google's Gemini API

# Hardcoded API key - Replace with your actual Gemini API key
GEMINI_API_KEY =os.getenv("GEMINI_API_KEY")

# Get API key function returns the hardcoded key
def get_gemini_api_key():
    return GEMINI_API_KEY

# Initialize Gemini client
def init_gemini_client():
    api_key = get_gemini_api_key()
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

# Generate response using Gemini API
# Simple function to directly call the Gemini API with minimal code
def get_ai_response(prompt, context="", max_tokens=800):
    try:
        # Always configure the API with the hardcoded key - do this every time to ensure it's set
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Create the most basic model instance possible
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        
        # Add context to the prompt if available
        if context:
            full_prompt = f"Context: {context}\n\nQuestion: {prompt}"
        else:
            full_prompt = prompt
        
        # Make the API call with minimal parameters
        response = model.generate_content(full_prompt)
        
        # Return the text directly
        return response.text
    except Exception as e:
        # Print error for debugging
        print(f"Gemini API error: {e}")
        return f"I encountered an error: {str(e)}. Please try a different question."

# Fallback response system when Gemini is not available
def get_fallback_response(query):
    # Educational-themed responses
    general_responses = [
        "That's an interesting question! Have you tried looking at tutorial videos on this topic?",
        "Great question! This concept might be covered in the learning modules under the related topic.",
        "I recommend breaking this problem down into smaller steps. What's the first part you're stuck on?",
        "Let's approach this systematically. What have you tried so far?",
        "This seems like a good opportunity to collaborate with peers who might have insights.",
        "Have you checked the resources section? There might be helpful guides on this topic."
    ]
    
    # Topic-specific responses
    if "python" in query.lower() or "code" in query.lower() or "programming" in query.lower():
        return random.choice([
            "For Python questions, remember to check the official documentation at python.org.",
            "When debugging code, print statements can help you understand what's happening at each step.",
            "Consider using a debugger to step through your code line by line.",
            "Python has many built-in functions that might help with this task.",
            "The error message usually contains hints about what went wrong in your code."
        ])
    
    elif "math" in query.lower() or "equation" in query.lower() or "formula" in query.lower():
        return random.choice([
            "For math problems, try writing out each step clearly.",
            "Check if there's a formula or theorem that applies to this type of problem.",
            "Sometimes drawing a diagram can help clarify mathematical concepts.",
            "Make sure your units are consistent throughout the problem.",
            "Try working with a simpler version of the problem first, then build up."
        ])
    
    elif "study" in query.lower() or "learn" in query.lower() or "remember" in query.lower():
        return random.choice([
            "Active recall is one of the most effective study techniques. Try explaining the concept in your own words.",
            "Spaced repetition helps with long-term retention. Review the material at increasing intervals.",
            "Teaching others is a great way to reinforce your own understanding.",
            "Taking short breaks during study sessions can actually improve focus and retention.",
            "Consider creating flashcards for key concepts and formulas."
        ])
    
    else:
        return random.choice(general_responses)

# Save chat history to database
def save_chat_to_db(user_id, query, response):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO chatbot_interactions (user_id, query, response, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, query, response, timestamp))
        
        conn.commit()
        conn.close()
        
        # Log the activity
        log_activity(user_id, "chatbot_interaction", {"query_length": len(query)})
        
        return True
    except Exception as e:
        st.error(f"Error saving chat: {e}")
        return False

# Get user's learning context based on recent activity
def get_user_learning_context(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_attempts'")
        quiz_table_exists = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos_watched'")
        videos_table_exists = cursor.fetchone() is not None
        
        recent_quiz_topics = []
        recent_video_topics = []
        
        # Get recent quiz topics if table exists
        if quiz_table_exists:
            cursor.execute("""
                SELECT topic FROM quiz_attempts
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 3
            """, (user_id,))
            
            recent_quiz_topics = [row[0] for row in cursor.fetchall()]
        
        # Get recent video topics if table exists
        if videos_table_exists:
            cursor.execute("""
                SELECT topic FROM videos_watched
                WHERE user_id = ?
                ORDER BY last_watched DESC
                LIMIT 3
            """, (user_id,))
            
            recent_video_topics = [row[0] for row in cursor.fetchall()]
        
        # Alternative: try video_watched table if videos_watched doesn't exist
        if not videos_table_exists:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_watched'")
            if cursor.fetchone() is not None:
                cursor.execute("""
                    SELECT topic FROM video_watched
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 3
                """, (user_id,))
                
                recent_video_topics = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Combine and remove duplicates
        all_topics = recent_quiz_topics + recent_video_topics
        if all_topics:
            return ", ".join(list(dict.fromkeys(all_topics)))
        else:
            return "Python programming (general)"
    except Exception as e:
        # Return a default context on error
        return "Python programming (general)"

# Get previous chat history for the user
def get_chat_history(user_id, limit=10):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT query, response, timestamp FROM chatbot_interactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        chat_history = [{"query": row[0], "response": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
        conn.close()
        
        return chat_history
    except Exception as e:
        st.error(f"Error getting chat history: {e}")
        return []

# Main chatbot interface using Streamlit components
def chatbot_widget():
    """
    Displays a chat interface for the AI assistant
    """
    api_key = get_gemini_api_key()
    if api_key:
        masked_key = api_key[:4] + "..." + api_key[-4:]
        st.sidebar.text(f"Using API key: {masked_key}")
    else:
        st.sidebar.error("No API key found!")
    # Create a container for the chat interface
    chat_container = st.container()
    
    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi there! I'm your Python learning assistant. How can I help you today?"}
        ]
    
    # Display existing messages
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
    # Chat input
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([8, 2])
        with col1:
            user_input = st.text_input("Ask me anything about Python...", 
                                     key="user_input", 
                                     label_visibility="collapsed")
        with col2:
            submit_button = st.form_submit_button("Send")
    
    # Process input and generate response
    if submit_button and user_input:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get user context if authenticated
        user_id = st.session_state.user["id"] if "user" in st.session_state else 0
        context = get_user_learning_context(user_id) if user_id > 0 else ""
        
        try:
            # Generate AI response
            response = get_ai_response(user_input, context)
            
            # Add assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Save to database if authenticated
            if user_id > 0:
                save_chat_to_db(user_id, user_input, response)
                
        except Exception as e:
            # Fallback response
            fallback = get_fallback_response(user_input)
            st.session_state.messages.append({"role": "assistant", "content": fallback})
            if user_id > 0:
                save_chat_to_db(user_id, user_input, fallback)
        
        # Rerun to update the chat display with new messages
        st.rerun()

# Get suggestion based on recent topics and student activity
def get_proactive_suggestions(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent quiz performance
        cursor.execute("""
            SELECT topic, AVG(score * 100.0 / max_score) as avg_score
            FROM quiz_attempts
            WHERE user_id = ?
            GROUP BY topic
            ORDER BY avg_score ASC
            LIMIT 1
        """, (user_id,))
        
        lowest_score_topic = cursor.fetchone()
        
        # Get most watched topic
        cursor.execute("""
            SELECT topic, SUM(watch_count) as total_watches
            FROM videos_watched
            WHERE user_id = ?
            GROUP BY topic
            ORDER BY total_watches DESC
            LIMIT 1
        """, (user_id,))
        
        most_watched_topic = cursor.fetchone()
        
        conn.close()
        
        suggestions = []
        
        # Add suggestion based on quiz performance
        if lowest_score_topic and lowest_score_topic[1] < 70:
            suggestions.append(f"I notice you might be having difficulty with {lowest_score_topic[0]}. Do you have any specific questions about it?")
        
        # Add suggestion based on most watched topic
        if most_watched_topic:
            suggestions.append(f"Want to discuss something about {most_watched_topic[0]}? I'm here to help!")
        
        # Add general suggestion if no specific ones
        if not suggestions:
            suggestions = [
                "Need help with a difficult Python concept? Ask me anything!",
                "Stuck on a coding problem? I can help break it down.",
                "Want to review a Python topic? Just let me know what you're studying."
            ]
        
        return random.choice(suggestions)
    except Exception as e:
        return "How can I help with your Python learning today?"

# Stand-alone function to initialize DB tables
def init_chatbot_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chatbot_user_time
            ON chatbot_interactions (user_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"Error initializing chatbot database: {e}")
        return False

# Function to set up the chatbot
def setup_chatbot():
    """
    Initializes the chatbot by setting up the database and chat widget
    """
    # Initialize database tables
    init_chatbot_db()
    
    # Configure Gemini API with hardcoded key
    init_gemini_client()
    
    # Display the chat interface
    chatbot_widget()

if __name__ == "__main__":
    st.set_page_config(page_title="Gemini Learning Assistant", page_icon="❓")
    
    # For testing only - create mock user
    if "user" not in st.session_state:
        st.session_state.user = {"id": 1, "username": "test_user"}
    
    # Stand-alone test page
    st.title("Gemini Learning Assistant")
    st.write("This is a test page for the AI learning assistant chatbot powered by Gemini.")
    
    # Initialize database
    init_chatbot_db()
    
    # Configure API
    init_gemini_client()
    
    # Show chatbot
    chatbot_widget()