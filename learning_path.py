# learning_path.py
import streamlit as st
import pandas as pd
import numpy as np
import traceback
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
import random
import base64

from db_utils import get_db_connection, log_activity
#from code_ch import handle_daily_challenge_completion
#from ch_utils import complete_daily_challenge



# Add debug mode
DEBUG = False  # Set to False in production

def debug_log(message):
    if DEBUG:
        st.sidebar.write(f"DEBUG: {message}")

# Inject all custom CSS at the beginning
def inject_custom_css():
    st.markdown("""
    <style>
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    .achievement-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 20px;
        margin-top: 20px;
    }
    .achievement {
        background-color: #f5f5f5;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        transition: transform 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .achievement:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .achievement.unlocked {
        background: linear-gradient(135deg, #f5f5f5 0%, #e0f7fa 100%);
        border: 1px solid #4db6ac;
    }
    .achievement.locked {
        filter: grayscale(1);
        opacity: 0.7;
    }
    .achievement-icon {
        font-size: 2.5em;
        margin-bottom: 10px;
    }
    .achievement-name {
        font-weight: bold;
        margin-bottom: 5px;
    }
    .achievement-desc {
        font-size: 0.8em;
        color: #666;
    }
    .progress-container {
        background-color: #e0e0e0;
        height: 5px;
        border-radius: 5px;
        margin-top: 10px;
        overflow: hidden;
    }
    .progress-bar {
        height: 100%;
        border-radius: 5px;
        background-color: #4CAF50;
    }
    .progress-bar.mastered {
        background-image: linear-gradient(45deg, rgba(255, 255, 255, 0.15) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0.15) 75%, transparent 75%, transparent);
        background-size: 1rem 1rem;
        animation: progress-bar-stripes 1s linear infinite;
    }
    @keyframes progress-bar-stripes {
        0% { background-position: 1rem 0; }
        100% { background-position: 0 0; }
    }
    .stButton>button.generate-path-btn {
        background: linear-gradient(135deg, #4CAF50 0%, #2196F3 100%);
        color: white;
        font-weight: bold;
        border-radius: 25px;
        padding: 10px 20px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }
    .stButton>button.generate-path-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

# Download NLTK resources with error handling
@st.cache_resource
def load_nltk_resources():
    try:
        nltk.download('vader_lexicon', quiet=True)
        return SentimentIntensityAnalyzer()
    except Exception as e:
        st.warning(f"Could not load NLTK resources: {e}")
        # Provide a simple fallback
        class SimpleSentiment:
            def polarity_scores(self, text):
                return {"compound": 0.0, "neg": 0.0, "neu": 1.0, "pos": 0.0}
        return SimpleSentiment()

# Function to get a fun fact about Python
def get_python_fun_fact():
    fun_facts = [
        "Python is named after the comedy group Monty Python, not the snake!",
        "Python's philosophy emphasizes code readability with its use of significant whitespace.",
        "Python was created by Guido van Rossum and first released in 1991.",
        "The Python Package Index (PyPI) has over 300,000 packages available.",
        "Instagram, YouTube, and Spotify are all built using Python.",
        "Python has been the fastest-growing programming language for several years.",
        "Python's design philosophy is summarized in 'The Zen of Python', which you can read by typing 'import this' in Python.",
        "Python 2.0 was released in 2000, and Python 3.0 was released in 2008.",
        "Python's name isn't about snakes but about the British comedy series 'Monty Python's Flying Circus'.",
        "Python can be used for web development, data analysis, AI, machine learning, and more!"
    ]
    return random.choice(fun_facts)

# Function to generate a base64 encoded image for badges
def get_badge_image(badge_type):
    # Define badge images as base64 for each badge type
    if badge_type == "streak_bronze":
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iI2NkN2YzMiIgLz48dGV4dCB4PSI1MCIgeT0iNTUiIGZvbnQtc2l6ZT0iMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IndoaXRlIj7wn5SBIDM8L3RleHQ+PC9zdmc+"
    elif badge_type == "streak_silver":
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iI2M0YzRjNCIgLz48dGV4dCB4PSI1MCIgeT0iNTUiIGZvbnQtc2l6ZT0iMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IndoaXRlIj7wn5SBIDY8L3RleHQ+PC9zdmc+"
    elif badge_type == "streak_gold":
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iI2ZmZDcwMCIgLz48dGV4dCB4PSI1MCIgeT0iNTUiIGZvbnQtc2l6ZT0iMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IndoaXRlIj7wn5SBIDk8L3RleHQ+PC9zdmc+"
    elif badge_type == "mastery_python":
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iIzRCOEJCRSIgLz48dGV4dCB4PSI1MCIgeT0iNTUiIGZvbnQtc2l6ZT0iMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IndoaXRlIj7wn5OtPC90ZXh0Pjwvc3ZnPg=="
    elif badge_type == "quiz_master":
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iIzlDMjdCMCIgLz48dGV4dCB4PSI1MCIgeT0iNTUiIGZvbnQtc2l6ZT0iMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IndoaXRlIj7wn5OoPC90ZXh0Pjwvc3ZnPg=="
    elif badge_type == "first_goal":
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iIzRDQUY1MCIgLz48dGV4dCB4PSI1MCIgeT0iNTUiIGZvbnQtc2l6ZT0iMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IndoaXRlIj7wn5KpPC90ZXh0Pjwvc3ZnPg=="
    else:
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iIzY2NiIgLz48dGV4dCB4PSI1MCIgeT0iNTUiIGZvbnQtc2l6ZT0iMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IndoaXRlIj7wn6SBPC90ZXh0Pjwvc3ZnPg=="

# Load real video data from SQLite with error handling
def load_video_library():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get video data (both quiz data and tutorial videos)
        cursor.execute("""
            SELECT DISTINCT topic FROM videos_watched
            UNION
            SELECT DISTINCT topic FROM quiz_attempts
        """)
        
        topics = [row[0] for row in cursor.fetchall()]
        
        videos = {}
        
        # For each topic, create a video entry
        for i, topic in enumerate(topics):
            try:
                # Check if there are any video stats for this topic
                cursor.execute("""
                    SELECT AVG(completion_percentage), SUM(watch_count) 
                    FROM videos_watched 
                    WHERE topic = ?
                """, (topic,))
                
                video_stats = cursor.fetchone()
                
                # Check if there are any quiz stats for this topic
                cursor.execute("""
                    SELECT COUNT(*), AVG(score * 100.0 / max_score) 
                    FROM quiz_attempts 
                    WHERE topic = ?
                """, (topic,))
                
                quiz_stats = cursor.fetchone()
                
                # Set difficulty based on quiz performance if available
                difficulty = "Medium"
                if quiz_stats and quiz_stats[0] > 0:
                    avg_score = quiz_stats[1] or 50  # Default to 50 if NULL
                    if avg_score < 40:
                        difficulty = "Hard"
                    elif avg_score > 70:
                        difficulty = "Easy"
                
                # Set views from watch count if available
                views = 1000
                if video_stats and video_stats[1]:
                    views = int(video_stats[1]) * 500  # Scale for display
                
                # Generate semi-realistic video metadata
                videos[f"{topic} Tutorial"] = {
                    "topic": topic,
                    "difficulty": difficulty,
                    "tags": [topic.lower(), difficulty.lower()],
                    "duration": 15 + (i % 3) * 5,  # Varying durations between 15-25 min
                    "views": views,
                    "thumbnail": f"https://picsum.photos/seed/{i+10}/300/200",  # Random thumbnail images
                    "xp_reward": 50 + (10 if difficulty == "Medium" else 20 if difficulty == "Hard" else 0)  # XP rewards
                }
            except Exception as e:
                debug_log(f"Error loading data for topic {topic}: {e}")
                continue
        
        conn.close()
        
        # If no videos in database yet, provide sample data
        if not videos:
            debug_log("No videos found in database, using sample data")
            videos = {
                "Python Basics Tutorial": {"topic": "Python Basics", "difficulty": "Easy", "tags": ["python", "beginner"], "duration": 15, "views": 5000, "thumbnail": "https://picsum.photos/seed/10/300/200", "xp_reward": 50},
                "Function Masterclass": {"topic": "Functions", "difficulty": "Medium", "tags": ["functions", "intermediate"], "duration": 20, "views": 3500, "thumbnail": "https://picsum.photos/seed/11/300/200", "xp_reward": 60},
                "Advanced OOP": {"topic": "Classes", "difficulty": "Hard", "tags": ["classes", "advanced"], "duration": 25, "views": 2000, "thumbnail": "https://picsum.photos/seed/12/300/200", "xp_reward": 70},
                "Data Structures": {"topic": "Lists", "difficulty": "Medium", "tags": ["lists", "dictionaries"], "duration": 18, "views": 4200, "thumbnail": "https://picsum.photos/seed/13/300/200", "xp_reward": 60},
                "Algorithmic Thinking": {"topic": "Algorithms", "difficulty": "Hard", "tags": ["algorithms", "advanced"], "duration": 30, "views": 1800, "thumbnail": "https://picsum.photos/seed/14/300/200", "xp_reward": 70},
            }
        
        return videos
    except Exception as e:
        debug_log(f"Error in load_video_library: {e}")
        debug_log(traceback.format_exc())
        # Return sample data as fallback
        return {
            "Python Basics Tutorial": {"topic": "Python Basics", "difficulty": "Easy", "tags": ["python", "beginner"], "duration": 15, "views": 5000, "thumbnail": "https://picsum.photos/seed/10/300/200", "xp_reward": 50},
            "Function Masterclass": {"topic": "Functions", "difficulty": "Medium", "tags": ["functions", "intermediate"], "duration": 20, "views": 3500, "thumbnail": "https://picsum.photos/seed/11/300/200", "xp_reward": 60},
            "Advanced OOP": {"topic": "Classes", "difficulty": "Hard", "tags": ["classes", "advanced"], "duration": 25, "views": 2000, "thumbnail": "https://picsum.photos/seed/12/300/200", "xp_reward": 70},
        }

# Load student data from SQLite with error handling
def load_student_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute("SELECT id, username, full_name FROM users")
        users = cursor.fetchall()
        
        data = []
        
        for user in users:
            try:
                user_id = user[0]
                username = user[1]
                full_name = user[2] or username
                
                # Get quiz performance by topic
                cursor.execute("""
                    SELECT topic, AVG(score * 100.0 / max_score) as avg_score
                    FROM quiz_attempts
                    WHERE user_id = ?
                    GROUP BY topic
                """, (user_id,))
                
                quiz_results = cursor.fetchall()
                quiz_scores = {}
                for topic, score in quiz_results:
                    safe_topic = topic.replace(' ', '_')
                    quiz_scores[f"Quiz_Score_{safe_topic}"] = score
                
                # Get video watch time by topic
                cursor.execute("""
                    SELECT topic, SUM(watch_count) as total_watches
                    FROM videos_watched
                    WHERE user_id = ?
                    GROUP BY topic
                """, (user_id,))
                
                watch_results = cursor.fetchall()
                watch_times = {}
                for topic, count in watch_results:
                    safe_topic = topic.replace(' ', '_')
                    # Estimate watch time based on count (10 minutes per watch)
                    watch_times[f"Watch_Time_{safe_topic}"] = count * 10 if count else 0
                
                # Determine preference based on most watched or highest score
                preference = None
                if watch_results:
                    preference = max(watch_results, key=lambda x: x[1])[0]
                elif quiz_results:
                    preference = max(quiz_results, key=lambda x: x[1])[0]
                
                # Get last active time
                cursor.execute("""
                    SELECT MAX(timestamp) FROM activity_logs WHERE user_id = ?
                """, (user_id,))
                
                last_active_result = cursor.fetchone()
                last_active = datetime.now()
                if last_active_result and last_active_result[0]:
                    try:
                        last_active = datetime.fromisoformat(str(last_active_result[0]).replace('Z', '+00:00'))
                    except:
                        pass
                
                # Create student entry
                student_entry = {
                    "Student": full_name,
                    "User_ID": user_id,
                    "Preference": preference,
                    "Last_Active": last_active
                }
                student_entry.update(quiz_scores)
                student_entry.update(watch_times)
                
                data.append(student_entry)
            except Exception as e:
                debug_log(f"Error processing user {user[1]}: {e}")
                continue
        
        conn.close()
        
        # If no user data yet, provide sample data
        if not data:
            debug_log("No user data found, using sample data")
            data = [
                {"Student": "Alice", "User_ID": 999, "Quiz_Score_Python": 85, "Quiz_Score_Functions": 70, "Watch_Time_Python": 120, "Watch_Time_Functions": 90, "Preference": "Python", "Last_Active": datetime.now() - timedelta(days=1)},
                {"Student": "Bob", "User_ID": 998, "Quiz_Score_Python": 65, "Quiz_Score_Lists": 80, "Watch_Time_Python": 60, "Watch_Time_Lists": 150, "Preference": "Lists", "Last_Active": datetime.now() - timedelta(days=2)},
                {"Student": "Charlie", "User_ID": 997, "Quiz_Score_Functions": 90, "Quiz_Score_Classes": 85, "Watch_Time_Functions": 180, "Watch_Time_Classes": 100, "Preference": "Functions", "Last_Active": datetime.now() - timedelta(days=0)}
            ]
        
        return pd.DataFrame(data)
    except Exception as e:
        debug_log(f"Error in load_student_data: {e}")
        debug_log(traceback.format_exc())
        # Return sample data as fallback
        return pd.DataFrame([
            {"Student": "Alice", "User_ID": 999, "Quiz_Score_Python": 85, "Quiz_Score_Functions": 70, "Watch_Time_Python": 120, "Watch_Time_Functions": 90, "Preference": "Python", "Last_Active": datetime.now() - timedelta(days=1)},
            {"Student": "Bob", "User_ID": 998, "Quiz_Score_Python": 65, "Quiz_Score_Lists": 80, "Watch_Time_Python": 60, "Watch_Time_Lists": 150, "Preference": "Lists", "Last_Active": datetime.now() - timedelta(days=2)},
        ])

# Get user's learning stats and achievements
def get_user_stats(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total quiz attempts
        cursor.execute("SELECT COUNT(*) FROM quiz_attempts WHERE user_id = ?", (user_id,))
        quiz_count = cursor.fetchone()[0] or 0
        
        # Get total video watches
        cursor.execute("SELECT SUM(watch_count) FROM videos_watched WHERE user_id = ?", (user_id,))
        video_count = cursor.fetchone()[0] or 0
        
        # Get average quiz score
        cursor.execute("""
            SELECT AVG(score * 100.0 / max_score) 
            FROM quiz_attempts 
            WHERE user_id = ?
        """, (user_id,))
        avg_score = cursor.fetchone()[0] or 0
        
        # Get streak data
        cursor.execute("""
            SELECT date(timestamp) as activity_date
            FROM activity_logs
            WHERE user_id = ? AND timestamp >= date('now', '-30 days')
            GROUP BY activity_date
            ORDER BY activity_date DESC
        """, (user_id,))
        
        activity_dates = [row[0] for row in cursor.fetchall()]
        
        # Calculate current streak
        streak = 0
        today = datetime.now().date()
        
        for i in range(30):  # Check up to 30 days back
            check_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            if check_date in activity_dates:
                if i == 0 or streak > 0:  # Today or continuing streak
                    streak += 1
            else:
                if i == 0:  # Today has no activity but might have been active yesterday
                    continue
                else:
                    break  # Streak broken
                    
        # Get completed topics (topics with quiz score above 70%)
        cursor.execute("""
            SELECT topic
            FROM quiz_attempts
            WHERE user_id = ? AND (score * 100.0 / max_score) >= 70
            GROUP BY topic
        """, (user_id,))
        
        mastered_topics = [row[0] for row in cursor.fetchall()]
        
        # Calculate XP (experience points)
        # Formula: (quiz_count * 10) + (video_count * 5) + (streak * 20) + (len(mastered_topics) * 50)
        xp = (quiz_count * 10) + (video_count * 5) + (streak * 20) + (len(mastered_topics) * 50)
        
        # Calculate level
        level = 1 + (xp // 100)  # Level up every 100 XP
        
        # Get badges
        badges = []
        
        # Streak badges
        if streak >= 9:
            badges.append({"name": "Gold Streak", "type": "streak_gold", "description": "9+ day learning streak!"})
        elif streak >= 6:
            badges.append({"name": "Silver Streak", "type": "streak_silver", "description": "6+ day learning streak!"})
        elif streak >= 3:
            badges.append({"name": "Bronze Streak", "type": "streak_bronze", "description": "3+ day learning streak!"})
            
        # Topic mastery badges
        if len(mastered_topics) >= 3:
            badges.append({"name": "Python Master", "type": "mastery_python", "description": f"Mastered {len(mastered_topics)} Python topics!"})
            
        # Quiz badges
        if quiz_count >= 10 and avg_score >= 80:
            badges.append({"name": "Quiz Master", "type": "quiz_master", "description": "Completed 10+ quizzes with 80%+ average!"})
            
        # Check if user has set goals
        cursor.execute("""
            SELECT COUNT(*) FROM activity_logs 
            WHERE user_id = ? AND activity_type = 'goal_set'
        """, (user_id,))
        
        goals_count = cursor.fetchone()[0] or 0
        if goals_count > 0:
            badges.append({"name": "Goal Setter", "type": "first_goal", "description": "Set your first learning goal!"})
        
        conn.close()
        
        return {
            "quiz_count": quiz_count,
            "video_count": video_count,
            "avg_score": avg_score,
            "streak": streak,
            "mastered_topics": mastered_topics,
            "xp": xp,
            "level": level,
            "badges": badges,
            "next_level_xp": (level * 100) - xp  # XP needed for next level
        }
    except Exception as e:
        debug_log(f"Error getting user stats: {e}")
        # Return default stats
        return {
            "quiz_count": 0,
            "video_count": 0,
            "avg_score": 0,
            "streak": 0,
            "mastered_topics": [],
            "xp": 0,
            "level": 1,
            "badges": [],
            "next_level_xp": 100
        }

# Sentiment analysis with error handling
def analyze_feedback(feedback):
    try:
        sia = load_nltk_resources()
        scores = sia.polarity_scores(feedback)
        return scores
    except Exception as e:
        debug_log(f"Error in sentiment analysis: {e}")
        return {"compound": 0.0, "neg": 0.0, "neu": 1.0, "pos": 0.0}

# Hybrid recommendation system (collaborative + content-based) with error handling
@st.cache_resource
def train_recommendation_model(student_data):
    try:
        # Extract numeric columns for collaborative filtering
        numeric_cols = [col for col in student_data.columns if col.startswith(('Quiz_Score_', 'Watch_Time_'))]
        
        if not numeric_cols or len(student_data) < 2:
            # Not enough data for collaborative filtering
            return None, None, None
        
        # Collaborative filtering with SVD
        interaction_matrix = student_data[numeric_cols].fillna(0)  # Replace NaN with 0
        
        # Handle case where there's insufficient data
        if interaction_matrix.shape[1] < 2:
            return None, None, None
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(interaction_matrix)
        
        # Use minimum between num features and 2 for SVD
        n_components = min(2, min(X_scaled.shape) - 1)
        if n_components < 1:
            return None, None, None
        
        svd = TruncatedSVD(n_components=n_components)
        latent_features = svd.fit_transform(X_scaled)
        
        return scaler, svd, latent_features
    except Exception as e:
        debug_log(f"Error in recommendation model: {e}")
        debug_log(traceback.format_exc())
        return None, None, None

def get_current_user_features(student_data, user_id):
    """Extract current user's features from student data with error handling"""
    try:
        if user_id is None:
            return None
        
        user_row = student_data[student_data['User_ID'] == user_id]
        if user_row.empty:
            return None
        
        numeric_cols = [col for col in student_data.columns if col.startswith(('Quiz_Score_', 'Watch_Time_'))]
        if not numeric_cols:
            return None
            
        return user_row[numeric_cols].fillna(0).values[0].tolist()
    except Exception as e:
        debug_log(f"Error getting user features: {e}")
        return None

def get_recommendations(student_data, current_features, watched_videos, video_library, model_data=None, max_recommendations=3):
    try:
        # Extract the current user's preference
        if st.session_state.get("user") and "preference" in st.session_state:
            user_preference = st.session_state.preference
        else:
            user_preference = "Python"  # Default preference
            debug_log("Using default preference: Python")
        
        # Unpack model data
        scaler, svd, latent_features = model_data if model_data else (None, None, None)
        
        # Content-based recommendations
        recommended_videos = []
        for video, metadata in video_library.items():
            if video not in watched_videos:
                score = 0
                
                # Topic match
                if metadata["topic"] == user_preference:
                    score += 0.5
                
                # Difficulty match - if we have quiz scores
                quiz_scores = [val for key, val in st.session_state.items() if key.startswith('quiz_score_')]
                if quiz_scores:
                    avg_score = sum(quiz_scores) / len(quiz_scores)
                    if metadata["difficulty"] == "Easy" and avg_score < 60:
                        score += 0.3
                    elif metadata["difficulty"] == "Medium" and 60 <= avg_score < 85:
                        score += 0.3
                    elif metadata["difficulty"] == "Hard" and avg_score >= 85:
                        score += 0.3
                
                # Tag match
                user_tags = st.session_state.get("tags", [])
                for tag in metadata["tags"]:
                    if tag in user_tags:
                        score += 0.2
                
                # Add final score
                recommended_videos.append((video, score + np.random.random() * 0.2))  # Add noise for variety
        
        # Sort by combined score and return top N
        recommended_videos.sort(key=lambda x: x[1], reverse=True)
        return [v[0] for v in recommended_videos[:max_recommendations]]
    except Exception as e:
        debug_log(f"Error generating recommendations: {e}")
        debug_log(traceback.format_exc())
        # Return first few videos as fallback
        return list(video_library.keys())[:max_recommendations]

# Draw learning path connection lines
def draw_path_lines(recommendations, video_library):
    path_html = """
    <style>
    .path-container {
        position: relative;
        height: 40px;
        margin: 20px 0;
    }
    .path-line {
        position: absolute;
        top: 20px;
        left: 10%;
        width: 80%;
        height: 4px;
        background: linear-gradient(90deg, #4CAF50, #2196F3);
        border-radius: 2px;
    }
    .path-dot {
        position: absolute;
        top: 12px;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background-color: #FF9800;
        text-align: center;
        line-height: 20px;
        color: white;
        font-weight: bold;
        z-index: 2;
        transition: transform 0.3s;
    }
    .path-dot:hover {
        transform: scale(1.2);
    }
    </style>
    <div class="path-container">
        <div class="path-line"></div>
    """
    
    # Add dots for each recommendation
    for i, video in enumerate(recommendations):
        position = 10 + (i * (80 / (len(recommendations) - 1 if len(recommendations) > 1 else 1)))
        difficulty = video_library[video]["difficulty"]
        color = "#4CAF50" if difficulty == "Easy" else "#2196F3" if difficulty == "Medium" else "#F44336"
        path_html += f"""
        <div class="path-dot" style="left: {position}%; background-color: {color};" title="{video}">
            {i+1}
        </div>
        """
    
    path_html += "</div>"
    
    # Make sure to use components.html for complex HTML
    import streamlit.components.v1 as components
    components.html(path_html, height=60)
    
    # Don't return the HTML - render it directly
    return None

# Celebration animation
def show_celebration():
    celebration_html = """
    <style>
    @keyframes confetti {
        0% { transform: translateY(0) rotate(0); opacity: 1; }
        100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
    }
    .confetti {
        position: fixed;
        animation: confetti 4s ease-out forwards;
        z-index: 1000;
    }
    </style>
    <script>
    function createConfetti() {
        const colors = ['#FF9800', '#4CAF50', '#2196F3', '#F44336', '#9C27B0'];
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.top = '-20px';
            confetti.style.width = '10px';
            confetti.style.height = '10px';
            confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '0';
            confetti.style.animationDelay = Math.random() * 2 + 's';
            document.body.appendChild(confetti);
            
            // Remove after animation completes
            setTimeout(() => {
                document.body.removeChild(confetti);
            }, 6000);
        }
    }
    createConfetti();
    </script>
    """
    return celebration_html

# Daily challenge generator
def get_daily_challenge(user_id, topic_preference):
    # Get the current date as a seed
    today = datetime.now().date()
    seed = int(today.strftime('%Y%m%d')) + user_id
    random.seed(seed)
    
    challenge_types = [
        "Complete a quiz on {topic} and score at least 80%",
        "Watch a tutorial on {topic} from start to finish",
        "Try coding a simple {topic} example",
        "Explain a concept about {topic} to someone else",
        "Find and read an article about {topic}",
        "Solve 3 practice problems related to {topic}"
    ]
    
    if not topic_preference or topic_preference == "Not set":
        topics = ["Python Basics", "Functions", "Classes", "Loops", "Data Structures"]
        topic = random.choice(topics)
    else:
        topic = topic_preference
    
    challenge = random.choice(challenge_types).format(topic=topic)
    xp_reward = random.randint(20, 50)
    
    return {
        "challenge": challenge,
        "topic": topic,
        "xp_reward": xp_reward
    }

def learning_path_page():
    try:
        #from code_ch import coding_challenge_page, handle_daily_challenge_completion
        # Check if user is logged in
        if 'user' not in st.session_state or not st.session_state.user:
            st.warning("Please log in to get personalized learning recommendations.")
            return
        
        # Inject all CSS at the beginning
        inject_custom_css()
        
        # Get user data
        user_id = st.session_state.user['id']
        username = st.session_state.user['username']
        
        # Clear any cached data that might be from another user
        if 'last_user_id' not in st.session_state or st.session_state.last_user_id != user_id:
            # This is either a new session or a different user, so clear cached data
            if 'user_stats' in st.session_state:
                del st.session_state.user_stats
            if 'recommendations' in st.session_state:
                del st.session_state.recommendations
            if 'preference' in st.session_state:
                del st.session_state.preference
                
            # Store the current user_id to check for user switches
            st.session_state.last_user_id = user_id
        
        # Initialize user stats in session state if needed
        if 'user_stats' not in st.session_state:
            st.session_state.user_stats = get_user_stats(user_id)
            
        # Load data
        with st.spinner("Loading your learning data..."):
            student_data = load_student_data()
            video_library = load_video_library()
            user_stats = st.session_state.user_stats
        
        # Find current user in student data
        user_row = student_data[student_data['User_ID'] == user_id]
        if not user_row.empty:
            preference = user_row['Preference'].values[0] if pd.notna(user_row['Preference'].values[0]) else "Not set"
            st.session_state.preference = preference
        else:
            preference = "Not set"
            st.session_state.preference = preference
        
        # Create the main layout
        st.title("🚀 Your Python Learning Adventure")
        
        # Display user stats in a fun card
        col1, col2 = st.columns([3, 1])
        
        with col1:
            quotes = [
                "The only way to learn a new programming language is by writing programs in it.",
                "Programming is the art of telling a computer what to do.",
                "The most disastrous thing you can learn is your first programming language.",
                "Programming is the closest thing we have to a superpower."
            ]
            
            tips = [
                "Tip: Use list comprehensions for cleaner iteration",
                "Did you know? Python's `zip()` can transpose matrices",
                "Pro Tip: `collections.defaultdict` saves key checks",
                "Python fact: `a, b = b, a` swaps variables efficiently"
            ]
            
            st.markdown(f"""
            <div style="background-color: #fff3e0; padding: 20px; border-radius: 15px; 
                        border-left: 5px solid #ffa000; margin-bottom: 20px;">
                <div style="font-style: italic; margin-bottom: 15px;">
                    " {random.choice(quotes)} "
                </div>
                <div style="background-color: #ffecb3; padding: 10px; border-radius: 8px;
                            font-size: 0.9em;">
                    🐍 {random.choice(tips)}
                </div>
            </div>
            """, unsafe_allow_html=True)
                
        with col2:
            # User level card
            progress_to_next = user_stats["xp"] % 100
            progress_percentage = progress_to_next
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color: white; padding: 15px; border-radius: 15px; text-align: center; height: 100%;">
                <h3 style="margin: 0; font-size: 1.5em;">Level {user_stats["level"]}</h3>
                <div style="font-size: 2.5em; margin: 10px 0;">🧙‍♂️</div>
                <div style="background-color: rgba(255,255,255,0.2); border-radius: 10px; height: 10px; margin: 10px 0;">
                    <div style="background-color: #4CAF50; width: {progress_percentage}%; height: 100%; border-radius: 10px;"></div>
                </div>
                <p style="margin: 0; font-size: 0.9em;">{progress_to_next}/100 XP to Level {user_stats["level"]+1}</p>
                <p style="margin: 5px 0 0 0; font-size: 0.9em;">Total: {user_stats["xp"]} XP</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Create tabs with emojis
        tab1, tab2, tab3, tab4 = st.tabs(["✨ Dashboard", "🧠 Learning Path", "📊 Analytics", "🏆 Achievements"])
        
        with tab1:
            st.header("Your Learning Dashboard")
            
            # Streak card with a more visual appeal
            streak = user_stats["streak"]

           
            streak_message = "Keep it up! 🔥" if streak > 0 else "Start your streak today!"
            
            # Start with an empty HTML string
            streak_html = ""
            
            # Open the outer container div
            streak_html += f"""
            <div style="margin: 20px 0; background-color: #f5f5f5; padding: 15px; border-radius: 10px;">
                <h4 style="margin-top: 0;">Current Streak: {streak} days</h4>
            """
            
            # Open the flex container div for streak dots
            streak_html += """
                <div style="display: flex; justify-content: flex-start; margin: 15px 0;">
            """
            
            # Add completed streak dots
            for _ in range(min(streak, 7)):
                streak_html += """
                    <div style="width: 30px; height: 30px; background-color: #FF9800; margin: 0 5px; border-radius: 50%; 
                                display: flex; align-items: center; justify-content: center; animation: pulse 1.5s infinite;" 
                        title="Day completed">
                        <span style="color: white;">🔥</span>
                    </div>
                """

            # Add incomplete streak dots
            for _ in range(max(0, 7 - streak)):
                streak_html += """
                    <div style="width: 30px; height: 30px; background-color: #e0e0e0; margin: 0 5px; border-radius: 50%;" 
                        title="Day not completed">
                    </div>
                """

            # Close the flex container div
            streak_html += """
                </div>
            """
            
            # Add the message paragraph and close the outer container div
            streak_html += f"""
                <p>{streak_message}</p>
            </div>
            """
            
            # Use components.html to render complex HTML
            import streamlit.components.v1 as components
            components.html(streak_html, height=150)
                            


        
            # Quick stats in a row
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; text-align: center;">
                    <h2 style="margin: 0; color: #2E7D32;">{user_stats["quiz_count"]}</h2>
                    <p style="margin: 5px 0 0 0;">Quizzes Completed</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                avg_score = round(user_stats["avg_score"], 1) if user_stats["avg_score"] else 0
                st.markdown(f"""
                <div style="background-color: #e3f2fd; padding: 20px; border-radius: 10px; text-align: center;">
                    <h2 style="margin: 0; color: #0d47a1;">{avg_score}%</h2>
                    <p style="margin: 5px 0 0 0;">Average Quiz Score</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div style="background-color: #fff8e1; padding: 20px; border-radius: 10px; text-align: center;">
                    <h2 style="margin: 0; color: #f57f17;">{user_stats["video_count"]}</h2>
                    <p style="margin: 5px 0 0 0;">Videos Watched</p>
                </div>
                """, unsafe_allow_html=True)
                
            # Display badges - FIXED implementation
            if user_stats["badges"]:
                st.subheader("Your Badges")
                
                # Create a 4-column layout for badges
                badge_cols = st.columns(4)
                
                for i, badge in enumerate(user_stats["badges"]):
                    col_index = i % 4  # Determine which column this badge goes in
                    badge_img = get_badge_image(badge["type"])
                    
                    with badge_cols[col_index]:
                        st.markdown(f"""
                        <div style="text-align: center; padding: 10px;">
                            <img src="{badge_img}" alt="{badge['name']}" title="{badge['description']}" 
                                 style="width: 60px; height: 60px; transition: transform 0.3s;">
                            <p style="margin: 5px 0 0 0; font-size: 0.9em;">{badge["name"]}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Complete quizzes, watch videos, and maintain your streak to earn badges!")
            
            # Activity feed (recent activities)
            st.subheader("Recent Activity")
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT activity_type, activity_details, timestamp
                    FROM activity_logs
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 5
                """, (user_id,))
                
                activities = cursor.fetchall()
                conn.close()
                
                if activities:
                    activity_container = st.container()
                    
                    for activity_type, details, timestamp in activities:
                        # Convert database timestamp to datetime
                        try:
                            activity_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_diff = datetime.now() - activity_time
                            
                            if time_diff.days > 0:
                                time_str = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                            elif time_diff.seconds // 3600 > 0:
                                hours = time_diff.seconds // 3600
                                time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
                            else:
                                minutes = (time_diff.seconds % 3600) // 60
                                time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                        except:
                            time_str = "recently"
                        
                        # Format activity type
                        if activity_type == "quiz_started":
                            icon = "📝"
                            activity_text = "Started a quiz"
                        elif activity_type == "video_watched":
                            icon = "📺"
                            activity_text = "Watched a video"
                        elif activity_type == "generate_learning_path":
                            icon = "🧠"
                            activity_text = "Generated learning path"
                        elif activity_type == "login":
                            icon = "🔑"
                            activity_text = "Logged in"
                        elif activity_type == "goal_set":
                            icon = "🎯"
                            activity_text = "Set a learning goal"
                        else:
                            icon = "🔄"
                            activity_text = activity_type.replace("_", " ").title()
                        
                        # Extract topic if available
                        topic = ""
                        if details:
                            try:
                                import json
                                details_dict = json.loads(details)
                                if "topic" in details_dict:
                                    topic = f" on {details_dict['topic']}"
                            except:
                                pass
                        
                        with activity_container:
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; margin-bottom: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 5px;">
                                <div style="font-size: 24px; margin-right: 15px;">{icon}</div>
                                <div style="flex-grow: 1;">
                                    <div style="font-weight: bold;">{activity_text}{topic}</div>
                                    <div style="font-size: 0.8em; color: #666;">{time_str}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No recent activity. Start learning to see your activity here!")
            except Exception as e:
                debug_log(f"Error loading activity feed: {e}")
                st.info("Start learning to see your activity here!")
        
        with tab2:
            st.header("Your Learning Path")
            
            # Get watched videos for current user
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT topic FROM videos_watched WHERE user_id = ?", (user_id,))
                watched_topics = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                watched_videos = [v for v in video_library.keys() if any(t in v for t in watched_topics)]
            except Exception as e:
                debug_log(f"Error getting watched videos: {e}")
                watched_videos = []
            
            # Train recommendation model
            with st.spinner("Analyzing your learning patterns..."):
                model_data = train_recommendation_model(student_data)
            
            # Get user features
            current_features = get_current_user_features(student_data, user_id)
            
            # Button to generate recommendations
            if st.button("🚀 Generate My Personalized Learning Path", key="generate_path", use_container_width=True):
                with st.spinner("Creating your customized learning adventure..."):
                    # Log this activity
                    try:
                        log_activity(user_id, "generate_learning_path", 
                                  {"preference": st.session_state.get("preference", "Not set")})
                    except Exception as e:
                        debug_log(f"Error logging activity: {e}")
                    
                    # Get recommendations
                    if current_features:
                        recommendations = get_recommendations(
                            student_data, current_features, watched_videos, 
                            video_library, model_data, max_recommendations=4
                        )
                    else:
                        # Fallback if we don't have enough data
                        recommendations = list(video_library.keys())[:4]
                        if watched_videos:
                            recommendations = [r for r in recommendations if r not in watched_videos]
                    
                    if recommendations:
                        # Store recommendations in session state
                        st.session_state.recommendations = recommendations
                        
                        # Show confetti celebration
                        st.markdown(show_celebration(), unsafe_allow_html=True)
                        
                        # Success message with path visualization
                        st.success("Your personalized learning path is ready! Follow this sequence for optimal learning:")
                        
                        # Path connection visualization
                        st.markdown(draw_path_lines(recommendations, video_library), unsafe_allow_html=True)
                        
                        # Create a more engaging card design for recommendations
                        for i, video in enumerate(recommendations):
                            vid_info = video_library[video]
                            
                            # Determine color based on difficulty
                            if vid_info["difficulty"] == "Easy":
                                card_color = "#e8f5e9"
                                border_color = "#4CAF50"
                                icon = "🌱"  # Beginner
                            elif vid_info["difficulty"] == "Medium":
                                card_color = "#e3f2fd"
                                border_color = "#2196F3"
                                icon = "🌿"  # Intermediate
                            else:
                                card_color = "#fce4ec"
                                border_color = "#F44336"
                                icon = "🌲"  # Advanced
                            
                            st.markdown(f"""
                            <div style="background-color: {card_color}; border-left: 5px solid {border_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px; position: relative;">
                                <div style="position: absolute; top: -10px; left: -10px; background-color: {border_color}; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold;">
                                    {i+1}
                                </div>
                                <h3 style="margin-top: 0; color: #333;">{video} {icon}</h3>
                                <div style="display: flex; flex-wrap: wrap; margin-bottom: 10px;">
                                    <div style="background-color: rgba(0,0,0,0.05); padding: 5px 10px; border-radius: 20px; margin-right: 10px; margin-bottom: 5px;">
                                        <span style="font-weight: bold;">Difficulty:</span> {vid_info["difficulty"]}
                                    </div>
                                    <div style="background-color: rgba(0,0,0,0.05); padding: 5px 10px; border-radius: 20px; margin-right: 10px; margin-bottom: 5px;">
                                        <span style="font-weight: bold;">Duration:</span> {vid_info["duration"]} min
                                    </div>
                                    <div style="background-color: rgba(0,0,0,0.05); padding: 5px 10px; border-radius: 20px; margin-bottom: 5px;">
                                        <span style="font-weight: bold;">XP Reward:</span> +{vid_info["xp_reward"]} XP
                                    </div>
                                </div>
                                <p style="margin-bottom: 15px;"><span style="font-weight: bold;">Tags:</span> {', '.join([f'<span style="background-color: rgba(0,0,0,0.05); padding: 2px 8px; border-radius: 10px; margin-right: 5px;">{tag}</span>' for tag in vid_info["tags"]])}</p>
                                <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                                    <button style="background-color: #4CAF50; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; display: flex; align-items: center;">
                                        <span style="margin-right: 5px;">▶️</span> Start Learning
                                    </button>
                                    <button style="background-color: #FF9800; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; display: flex; align-items: center;">
                                        <span style="margin-right: 5px;">📌</span> Save for Later
                                    </button>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Study plan timeline with more engaging visuals
                        st.subheader("Your Learning Schedule 📅")
                        
                        try:
                            # Create a timeline chart
                            timeline_data = []
                            today = datetime.now().date()
                            
                            for i, video in enumerate(recommendations):
                                vid_info = video_library[video]
                                timeline_data.append({
                                    "Video": video,
                                    "Topic": vid_info["topic"],
                                    "Start": today + timedelta(days=i*2),
                                    "End": today + timedelta(days=i*2 + 1),
                                    "Duration": vid_info["duration"],
                                    "Difficulty": vid_info["difficulty"]
                                })
                            
                            df_timeline = pd.DataFrame(timeline_data)
                            
                            # Convert dates to strings for Altair
                            df_timeline["Start_str"] = df_timeline["Start"].apply(lambda x: x.strftime("%Y-%m-%d"))
                            df_timeline["End_str"] = df_timeline["End"].apply(lambda x: x.strftime("%Y-%m-%d"))
                            df_timeline["Day"] = df_timeline["Start"].apply(lambda x: x.strftime("%A, %b %d"))
                            
                            # Create Gantt chart using Altair with custom colors
                            color_scale = alt.Scale(
                                domain=["Easy", "Medium", "Hard"],
                                range=["#4CAF50", "#2196F3", "#F44336"]
                            )
                            
                            chart = alt.Chart(df_timeline).mark_bar().encode(
                                x=alt.X('Start_str:T', title='Date'),
                                x2='End_str:T',
                                y=alt.Y('Video:N', title=None),
                                color=alt.Color('Difficulty:N', scale=color_scale, legend=alt.Legend(title="Difficulty")),
                                tooltip=['Video', 'Topic', 'Duration', 'Day']
                            ).properties(
                                height=200
                            )
                            
                            st.altair_chart(chart, use_container_width=True)
                        except Exception as e:
                            debug_log(f"Error creating timeline chart: {e}")
                            # Fallback to text display
                            st.markdown("### Your Study Schedule")
                            for i, video in enumerate(recommendations):
                                study_date = (today + timedelta(days=i*2)).strftime('%A, %B %d')
                                st.markdown(f"**Day {i+1}:** {video} - *{study_date}*")
                        
                        # Add motivational quote or tip
                        motivational_quotes = [
                            "The expert in anything was once a beginner.",
                            "Code is like humor. When you have to explain it, it's bad.",
                            "First, solve the problem. Then, write the code.",
                            "Programming isn't about what you know; it's about what you can figure out.",
                            "The best error message is the one that never shows up."
                        ]
                        
                        st.markdown(f"""
                        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 10px; margin-top: 20px; text-align: center; font-style: italic;">
                            "{random.choice(motivational_quotes)}"
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add how to use this plan with icons
                        st.markdown("""
                        <div style="background-color: #fff3e0; padding: 20px; border-radius: 10px; margin-top: 20px;">
                            <h4 style="margin-top: 0;">How to Use Your Learning Path:</h4>
                            <ol style="margin-bottom: 0; padding-left: 20px;">
                                <li><b>Follow the sequence</b> - Each topic builds on previous knowledge</li>
                                <li><b>Complete the quizzes</b> after each tutorial to reinforce learning</li>
                                <li><b>Earn XP and badges</b> to track your progress</li>
                                <li><b>Maintain your daily streak</b> for bonus rewards</li>
                                <li><b>Share your achievements</b> to inspire others</li>
                            </ol>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Share button (social sharing)
                        st.markdown("""
                        <div style="text-align: center; margin-top: 20px;">
                            <button style="background-color: #3b5998; color: white; border: none; padding: 8px 15px; border-radius: 5px; margin-right: 10px; cursor: pointer;">
                                Share on Facebook
                            </button>
                            <button style="background-color: #1da1f2; color: white; border: none; padding: 8px 15px; border-radius: 5px; margin-right: 10px; cursor: pointer;">
                                Share on Twitter
                            </button>
                            <button style="background-color: #0e76a8; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer;">
                                Share on LinkedIn
                            </button>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("We don't have enough data to make personalized recommendations yet. Try watching some videos or taking quizzes!")
            
            # If we have recommendations in session state but didn't just generate them
            elif 'recommendations' in st.session_state:
                st.success("Continue with your current learning path:")
                
                # Display the stored recommendations
                recommendations = st.session_state.recommendations
                
                # Path connection visualization
                st.markdown(draw_path_lines(recommendations, video_library), unsafe_allow_html=True)
                
                # Display each recommendation
                for i, video in enumerate(recommendations):
                    vid_info = video_library[video]
                    
                    # Determine color based on difficulty
                    if vid_info["difficulty"] == "Easy":
                        card_color = "#e8f5e9"
                        border_color = "#4CAF50"
                        icon = "🌱"  # Beginner
                    elif vid_info["difficulty"] == "Medium":
                        card_color = "#e3f2fd"
                        border_color = "#2196F3"
                        icon = "🌿"  # Intermediate
                    else:
                        card_color = "#fce4ec"
                        border_color = "#F44336"
                        icon = "🌲"  # Advanced
                    
                    st.markdown(f"""
                    <div style="background-color: {card_color}; border-left: 5px solid {border_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px; position: relative;">
                        <div style="position: absolute; top: -10px; left: -10px; background-color: {border_color}; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold;">
                            {i+1}
                        </div>
                        <h3 style="margin-top: 0; color: #333;">{video} {icon}</h3>
                        <div style="display: flex; flex-wrap: wrap; margin-bottom: 10px;">
                            <div style="background-color: rgba(0,0,0,0.05); padding: 5px 10px; border-radius: 20px; margin-right: 10px; margin-bottom: 5px;">
                                <span style="font-weight: bold;">Difficulty:</span> {vid_info["difficulty"]}
                            </div>
                            <div style="background-color: rgba(0,0,0,0.05); padding: 5px 10px; border-radius: 20px; margin-right: 10px; margin-bottom: 5px;">
                                <span style="font-weight: bold;">Duration:</span> {vid_info["duration"]} min
                            </div>
                            <div style="background-color: rgba(0,0,0,0.05); padding: 5px 10px; border-radius: 20px; margin-bottom: 5px;">
                                <span style="font-weight: bold;">XP Reward:</span> +{vid_info["xp_reward"]} XP
                            </div>
                        </div>
                        <p style="margin-bottom: 15px;"><span style="font-weight: bold;">Tags:</span> {', '.join([f'<span style="background-color: rgba(0,0,0,0.05); padding: 2px 8px; border-radius: 10px; margin-right: 5px;">{tag}</span>' for tag in vid_info["tags"]])}</p>
                        <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                            <button style="background-color: #4CAF50; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; display: flex; align-items: center;">
                                <span style="margin-right: 5px;">▶️</span> Start Learning
                            </button>
                            <button style="background-color: #FF9800; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; display: flex; align-items: center;">
                                <span style="margin-right: 5px;">📌</span> Save for Later
                            </button>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # First time user instructions
                st.markdown("""
                <div style="background-color: #f3e5f5; padding: 20px; border-radius: 10px; border-left: 5px solid #9c27b0;">
                    <h3 style="margin-top: 0; color: #6a1b9a;">Welcome to Your Learning Adventure! 🚀</h3>
                    <p>Click the button above to generate a personalized learning path based on your interests and learning style.</p>
                    <p>Your learning path will:</p>
                    <ul>
                        <li>Adapt to your skill level</li>
                        <li>Focus on topics you're interested in</li>
                        <li>Build knowledge in a logical sequence</li>
                        <li>Help you earn XP and badges</li>
                    </ul>
                    <p>The more you learn, the better your recommendations will become!</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Show sample path preview
                st.markdown("""
                <div style="margin-top: 30px; text-align: center;">
                    <h4>Preview: Sample Learning Path</h4>
                    <img src="https://via.placeholder.com/800x300/e3f2fd/1565c0?text=Sample+Learning+Path+Preview" style="max-width: 100%; border-radius: 10px; margin-top: 10px;">
                </div>
                """, unsafe_allow_html=True)
        
        with tab3:
            st.header("Learning Analytics")
            
            try:
                # Load user's quiz attempts
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Get quiz attempts over time
                cursor.execute("""
                    SELECT topic, score, max_score, timestamp
                    FROM quiz_attempts
                    WHERE user_id = ?
                    ORDER BY timestamp
                """, (user_id,))
                
                quiz_attempts = cursor.fetchall()
                
                # Get video watch patterns
                cursor.execute("""
                    SELECT topic, last_watched, watch_count
                    FROM videos_watched
                    WHERE user_id = ?
                    ORDER BY last_watched
                """, (user_id,))
                
                video_watches = cursor.fetchall()
                
                conn.close()
            except Exception as e:
                debug_log(f"Error fetching analytics data: {e}")
                quiz_attempts = []
                video_watches = []
                st.warning("Could not load your analytics data. Using sample data instead.")
            
            # Tabs for different analytics
            analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["Performance", "Activity", "Focus Areas"])
            
            with analysis_tab1:
                # Quiz performance over time with more engaging visuals
                if quiz_attempts:
                    try:
                        quiz_data = []
                        for topic, score, max_score, timestamp in quiz_attempts:
                            try:
                                date = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00')).date()
                            except:
                                date = datetime.now().date()
                            
                            percentage = (score / max_score) * 100 if max_score else 0
                            quiz_data.append({"Date": date, "Topic": topic, "Score": percentage})
                        
                        if quiz_data:
                            df_quiz = pd.DataFrame(quiz_data)
                            
                            # Create a more engaging line chart
                            fig = px.line(df_quiz, x="Date", y="Score", color="Topic",
                                        title="Quiz Performance Over Time",
                                        labels={"Score": "Score (%)", "Date": "Quiz Date"},
                                        line_shape="spline",  # Smoother lines
                                        markers=True)  # Show markers
                            
                            # Customize the chart
                            fig.update_layout(
                                height=400,
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                plot_bgcolor="white",
                                xaxis=dict(
                                    gridcolor="lightgray",
                                    title_font=dict(size=14),
                                ),
                                yaxis=dict(
                                    gridcolor="lightgray",
                                    range=[0, 105],  # Give some space above 100%
                                    title_font=dict(size=14),
                                ),
                                title_font=dict(size=18),
                                hoverlabel=dict(bgcolor="white", font_size=12),
                            )
                            
                            # Add a horizontal line at 80% (mastery level)
                            fig.add_shape(
                                type="line",
                                x0=df_quiz["Date"].min(),
                                y0=80,
                                x1=df_quiz["Date"].max(),
                                y1=80,
                                line=dict(color="#4CAF50", dash="dash", width=2),
                            )
                            
                            # Add annotation for mastery level
                            fig.add_annotation(
                                x=df_quiz["Date"].max(),
                                y=80,
                                text="Mastery Level",
                                showarrow=False,
                                yshift=10,
                                bgcolor="#4CAF50",
                                font=dict(color="white", size=10),
                                borderpad=4,
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Calculate mastery level with fun indicators
                            topic_mastery = df_quiz.groupby("Topic")["Score"].mean().reset_index()
                            topic_mastery["Mastery Level"] = topic_mastery["Score"].apply(
                                lambda x: "Mastered" if x >= 80 else "Developing" if x >= 60 else "Needs Practice"
                            )
                            
                            # Display mastery levels with progress bars
                            st.subheader("Topic Mastery Levels")
                            
                            # Use columns for responsive layout
                            topic_cols = st.columns(len(topic_mastery) if len(topic_mastery) <= 3 else 3)
                            
                            for i, (_, row) in enumerate(topic_mastery.iterrows()):
                                col_index = i % (3 if len(topic_mastery) > 3 else len(topic_mastery))
                                
                                if row["Mastery Level"] == "Mastered":
                                    emoji = "🏆"
                                    color = "#4CAF50"
                                    progress_class = "mastered"
                                elif row["Mastery Level"] == "Developing":
                                    emoji = "📈"
                                    color = "#FF9800"
                                    progress_class = "developing"
                                else:
                                    emoji = "📚"
                                    color = "#F44336"
                                    progress_class = "practice"
                                
                                with topic_cols[col_index]:
                                    st.markdown(f"""
                                    <div style="background-color: #f9f9f9; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                            <span style="font-weight: bold;">{row["Topic"]}</span>
                                            <span style="font-size: 20px;">{emoji}</span>
                                        </div>
                                        <div style="background-color: #e0e0e0; height: 10px; border-radius: 5px; overflow: hidden;">
                                            <div style="width: {row['Score']}%; height: 100%; background-color: {color};"></div>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                                            <span style="font-size: 0.8em; font-weight: bold; color: {color};">{row["Mastery Level"]}</span>
                                            <span style="font-size: 0.8em;">{row['Score']:.1f}%</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                    except Exception as e:
                        debug_log(f"Error creating quiz performance charts: {e}")
                        st.error("Could not create quiz performance charts. Try refreshing the page.")
                else:
                    st.info("Complete quizzes to see your performance analytics here!")
                    # Show a sample chart for motivation
                    st.markdown("""
                    <div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
                        <p>Sample analytics chart (your data will appear here):</p>
                        <img src="https://via.placeholder.com/800x400/e8f5e9/1b5e20?text=Sample+Performance+Chart" style="max-width: 100%; border-radius: 10px;">
                    </div>
                    """, unsafe_allow_html=True)
            
            with analysis_tab2:
                # Learning activity heatmap with enhanced visuals
                st.subheader("Your Learning Activity Pattern")
                
                try:
                    # Create simulated activity data if real data is insufficient
                    if len(quiz_attempts) + len(video_watches) < 10:
                        # Generate some fake data for a nicer visualization
                        activity_dates = []
                        today = datetime.now().date()
                        for i in range(30):
                            if np.random.random() > 0.7:  # 30% chance of activity on a given day
                                activity_dates.append(today - timedelta(days=i))
                    else:
                        # Use real activity data
                        activity_dates = []
                        for _, _, _, timestamp in quiz_attempts:
                            try:
                                date = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00')).date()
                                activity_dates.append(date)
                            except:
                                pass
                        
                        for _, timestamp, _ in video_watches:
                            try:
                                date = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00')).date()
                                activity_dates.append(date)
                            except:
                                pass
                    
                    if activity_dates:
                        # Count activities per date
                        date_counts = {}
                        for date in activity_dates:
                            if date in date_counts:
                                date_counts[date] += 1
                            else:
                                date_counts[date] = 1
                        
                        # Prepare data for heatmap
                        today = datetime.now().date()
                        start_date = today - timedelta(days=29)  # Last 30 days
                        
                        dates_range = []
                        current = start_date
                        while current <= today:
                            dates_range.append(current)
                            current += timedelta(days=1)
                        
                        # Get weekday and week number for each date
                        heatmap_data = []
                        for date in dates_range:
                            weekday = date.strftime("%a")
                            week = (date - start_date).days // 7
                            count = date_counts.get(date, 0)
                            heatmap_data.append({
                                "Weekday": weekday, 
                                "Week": str(week), 
                                "Activities": count,
                                "Date": date.strftime("%b %d")
                            })
                        
                        df_heatmap = pd.DataFrame(heatmap_data)
                        
                        # Create enhanced heatmap with Altair
                        # Custom color scheme
                        color_scale = alt.Scale(
                            domain=[0, 1, 2, 3, 4],
                            range=["#f5f5f5", "#c8e6c9", "#81c784", "#4caf50", "#2e7d32"]
                        )
                        
                        base = alt.Chart(df_heatmap).encode(
                            x=alt.X('Week:O', title=None, axis=alt.Axis(labelAngle=0)),
                            y=alt.Y('Weekday:O', title=None, sort=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
                            tooltip=['Weekday', 'Date', 'Activities']
                        )
                        
                        heatmap = base.mark_rect().encode(
                            color=alt.Color('Activities:Q', scale=color_scale, legend=alt.Legend(title="Activities")),
                        )
                        
                        # Add text labels for days with activities
                        text = base.mark_text().encode(
                            text=alt.condition(
                                alt.datum.Activities > 0,
                                alt.Text('Activities:Q'),
                                alt.value('')
                            ),
                            color=alt.condition(
                                alt.datum.Activities > 2,
                                alt.value('white'),
                                alt.value('black')
                            )
                        )
                        
                        # Combine the heatmap and text layers
                        chart = (heatmap + text).properties(
                            title="Your Learning Activity Heatmap (Last 30 Days)",
                            width=600,
                            height=250
                        )
                        
                        st.altair_chart(chart, use_container_width=True)
                        
                        # Create a more engaging streak display
                        current_streak = user_stats["streak"]
                        
                        # Get total active days
                        active_days = sum(1 for count in date_counts.values() if count > 0)
                        
                        # Calculate completion rate
                        completion_rate = (active_days / 30) * 100
                        
                        # Create a 3-column metrics display
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown(f"""
                            <div style="background-color: #ffebee; padding: 20px; border-radius: 10px; text-align: center; height: 100%;">
                                <div style="font-size: 2.5em; color: #f44336;">🔥</div>
                                <h2 style="margin: 5px 0; color: #f44336;">{current_streak}</h2>
                                <p style="margin: 0;">Current Streak</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            # Get longest streak from user stats (or calculate from data)
                            longest_streak = 0
                            consecutive_days = 0
                            
                            for i in range(30):
                                check_date = today - timedelta(days=i)
                                if check_date in date_counts:
                                    consecutive_days += 1
                                else:
                                    longest_streak = max(longest_streak, consecutive_days)
                                    consecutive_days = 0
                            
                            longest_streak = max(longest_streak, consecutive_days)
                            
                            st.markdown(f"""
                            <div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; text-align: center; height: 100%;">
                                <div style="font-size: 2.5em; color: #4caf50;">🏆</div>
                                <h2 style="margin: 5px 0; color: #4caf50;">{longest_streak}</h2>
                                <p style="margin: 0;">Longest Streak</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(f"""
                            <div style="background-color: #e3f2fd; padding: 20px; border-radius: 10px; text-align: center; height: 100%;">
                                <div style="font-size: 2.5em; color: #2196f3;">📊</div>
                                <h2 style="margin: 5px 0; color: #2196f3;">{active_days}/30</h2>
                                <p style="margin: 0;">Active Days</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Add a monthly completion bar
                        st.markdown(f"""
                        <div style="margin-top: 20px;">
                            <p style="margin-bottom: 5px; font-weight: bold;">Monthly Completion: {completion_rate:.1f}%</p>
                            <div style="background-color: #e0e0e0; height: 10px; border-radius: 5px; overflow: hidden;">
                                <div style="width: {completion_rate}%; height: 100%; background: linear-gradient(90deg, #9be7ad 0%, #4CAF50 100%);"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add streak motivation message
                        if current_streak == 0:
                            motivation = "Start learning today to build your streak!"
                            icon = "📅"
                            color = "#f44336"
                        elif current_streak < 3:
                            motivation = "You're building momentum! Keep it going!"
                            icon = "🔥"
                            color = "#ff9800"
                        else:
                            motivation = f"Impressive {current_streak}-day streak! You're on fire!"
                            icon = "⚡"
                            color = "#4caf50"
                        
                        st.markdown(f"""
                        <div style="margin-top: 20px; background-color: #f9f9f9; padding: 15px; border-radius: 10px; border-left: 5px solid {color};">
                            <div style="display: flex; align-items: center;">
                                <div style="font-size: 2em; margin-right: 15px;">{icon}</div>
                                <div style="flex-grow: 1;">
                                    <p style="margin: 0; font-weight: bold; color: {color};">{motivation}</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    debug_log(f"Error creating activity heatmap: {e}")
                    st.error("Could not create activity visualization. Try refreshing the page.")
            
            with analysis_tab3:
                # Focus areas - what to work on next
                st.subheader("Your Learning Focus Areas")
                
                try:
                    # Calculate areas that need improvement based on quiz scores
                    if quiz_attempts:
                        df_quiz = pd.DataFrame([
                            {"Topic": topic, "Score": (score / max_score) * 100 if max_score else 0}
                            for topic, score, max_score, _ in quiz_attempts
                        ])
                        
                        # Group by topic and calculate average score
                        topic_scores = df_quiz.groupby("Topic")["Score"].mean().reset_index()
                        
                        # Sort by score ascending (lowest first)
                        topic_scores = topic_scores.sort_values("Score")
                        
                        # Create a horizontal bar chart with custom styling
                        fig = px.bar(
                            topic_scores,
                            x="Score",
                            y="Topic",
                            orientation='h',
                            color="Score",
                            color_continuous_scale=px.colors.sequential.Viridis,
                            range_color=[0, 100],
                            title="Topic Performance (Lowest to Highest)",
                            labels={"Score": "Average Score (%)", "Topic": ""},
                            height=400
                        )
                        
                        # Customize the layout
                        fig.update_layout(
                            plot_bgcolor="white",
                            xaxis=dict(
                                gridcolor="lightgray",
                                range=[0, 100],
                                title_font=dict(size=14),
                            ),
                            yaxis=dict(
                                title_font=dict(size=14),
                            ),
                            coloraxis_colorbar=dict(
                                title="Score (%)",
                            ),
                            title_font=dict(size=18),
                        )
                        
                        # Add a vertical line at 70% (passing threshold)
                        fig.add_shape(
                            type="line",
                            x0=70,
                            y0=-0.5,
                            x1=70,
                            y1=len(topic_scores) - 0.5,
                            line=dict(color="#FF9800", dash="dash", width=2),
                        )
                        
                        # Add annotation for passing threshold
                        fig.add_annotation(
                            x=70,
                            y=len(topic_scores) - 0.5,
                            text="Passing",
                            showarrow=False,
                            xshift=10,
                            textangle=-90,
                            bgcolor="#FF9800",
                            font=dict(color="white", size=10),
                            borderpad=4,
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Generate personalized recommendations
                        weak_areas = topic_scores[topic_scores["Score"] < 70]["Topic"].tolist()
                        strong_areas = topic_scores[topic_scores["Score"] >= 80]["Topic"].tolist()
                        
                        # Generate focus area recommendations
                        st.subheader("Recommended Focus Areas")
                        
                        if weak_areas:
                            st.markdown(f"""
                            <div style="background-color: #fff8e1; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #ffc107;">
                                <h4 style="margin-top: 0; color: #ff8f00;">Areas to Improve 🔍</h4>
                                <p>Based on your quiz performance, focus on improving these topics:</p>
                                <ul style="margin-bottom: 0;">
                                    {"".join([f'<li><b>{area}</b>: {topic_scores[topic_scores["Topic"] == area]["Score"].values[0]:.1f}% - {get_improvement_suggestion(area)}</li>' for area in weak_areas])}
                                </ul>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        if strong_areas:
                            st.markdown(f"""
                            <div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #4caf50;">
                                <h4 style="margin-top: 0; color: #2e7d32;">Your Strengths 💪</h4>
                                <p>You're doing great in these areas:</p>
                                <ul style="margin-bottom: 0;">
                                    {"".join([f'<li><b>{area}</b>: {topic_scores[topic_scores["Topic"] == area]["Score"].values[0]:.1f}%</li>' for area in strong_areas])}
                                </ul>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Learning path suggestion
                        if weak_areas:
                            next_topic = weak_areas[0]
                            st.markdown(f"""
                            <div style="background-color: #e3f2fd; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #2196f3;">
                                <h4 style="margin-top: 0; color: #0d47a1;">Suggested Next Steps 🚀</h4>
                                <ol style="margin-bottom: 0;">
                                    <li>Focus on improving your understanding of <b>{next_topic}</b></li>
                                    <li>Watch tutorial videos on this topic</li>
                                    <li>Practice with coding exercises</li>
                                    <li>Retake quizzes to measure improvement</li>
                                </ol>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("Complete quizzes to see your focus areas and personalized recommendations!")
                except Exception as e:
                    debug_log(f"Error creating focus areas: {e}")
                    st.error("Could not analyze focus areas. Please try again later.")
        
        with tab4:
            st.header("Your Achievements")
            
            # Define all possible achievements
            all_achievements = [
                {"id": "first_day", "name": "First Day", "icon": "🌟", "description": "Complete your first day of learning", "requirement": 1, "stat": user_stats["streak"], "unit": "day"},
                {"id": "three_day_streak", "name": "On Fire", "icon": "🔥", "description": "Maintain a 3-day learning streak", "requirement": 3, "stat": user_stats["streak"], "unit": "days"},
                {"id": "week_streak", "name": "Committed", "icon": "📅", "description": "Maintain a 7-day learning streak", "requirement": 7, "stat": user_stats["streak"], "unit": "days"},
                {"id": "first_quiz", "name": "Quiz Taker", "icon": "📝", "description": "Complete your first quiz", "requirement": 1, "stat": user_stats["quiz_count"], "unit": "quiz"},
                {"id": "quiz_master", "name": "Quiz Master", "icon": "🧠", "description": "Complete 10 quizzes", "requirement": 10, "stat": user_stats["quiz_count"], "unit": "quizzes"},
                {"id": "perfect_score", "name": "Perfect Score", "icon": "💯", "description": "Get 100% on any quiz", "requirement": 100, "stat": user_stats["avg_score"], "unit": "%"},
                {"id": "first_video", "name": "Video Viewer", "icon": "🎬", "description": "Watch your first tutorial video", "requirement": 1, "stat": user_stats["video_count"], "unit": "video"},
                {"id": "video_enthusiast", "name": "Video Enthusiast", "icon": "📺", "description": "Watch 5 tutorial videos", "requirement": 5, "stat": user_stats["video_count"], "unit": "videos"},
                {"id": "first_mastery", "name": "Topic Mastered", "icon": "🏅", "description": "Master your first topic (80%+ score)", "requirement": 1, "stat": len(user_stats["mastered_topics"]), "unit": "topic"},
                {"id": "multi_mastery", "name": "Python Expert", "icon": "👨‍💻", "description": "Master 3 different Python topics", "requirement": 3, "stat": len(user_stats["mastered_topics"]), "unit": "topics"},
                {"id": "level_5", "name": "Level Up", "icon": "⬆️", "description": "Reach level 5", "requirement": 5, "stat": user_stats["level"], "unit": "level"},
                {"id": "level_10", "name": "Coding Veteran", "icon": "🚀", "description": "Reach level 10", "requirement": 10, "stat": user_stats["level"], "unit": "level"},
            ]
            
            # Display achievements in a responsive grid - use Streamlit columns instead of CSS grid
            achievement_cols = st.columns(3)  # Create a 3-column layout for desktop
            
            for i, achievement in enumerate(all_achievements):
                # Determine which column this achievement goes in
                col_index = i % 3
                
                # Check if achievement is unlocked
                unlocked = achievement["stat"] >= achievement["requirement"]
                progress = min(100, (achievement["stat"] / achievement["requirement"]) * 100)
                
                # Format the class and progress text
                status = "Unlocked" if unlocked else "Locked"
                bg_color = "#e0f7fa" if unlocked else "#f5f5f5"
                border = "1px solid #4db6ac" if unlocked else "1px solid #e0e0e0"
                opacity = "1.0" if unlocked else "0.7"
                filter_value = "none" if unlocked else "grayscale(1)"
                progress_text = f"{achievement['stat']}/{achievement['requirement']} {achievement['unit']}"
                
                with achievement_cols[col_index]:
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; border-radius: 10px; padding: 15px; text-align: center; 
                                transition: transform 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: {border}; 
                                opacity: {opacity}; filter: {filter_value}; margin-bottom: 20px;">
                        <div style="font-size: 2.5em; margin-bottom: 10px;">{achievement["icon"]}</div>
                        <div style="font-weight: bold; margin-bottom: 5px;">{achievement["name"]}</div>
                        <div style="font-size: 0.8em; color: #666; margin-bottom: 10px;">{achievement["description"]}</div>
                        <div style="background-color: #e0e0e0; height: 5px; border-radius: 5px; margin-top: 10px; overflow: hidden;">
                            <div style="height: 100%; border-radius: 5px; background-color: #4CAF50; width: {progress}%;"></div>
                        </div>
                        <div style="font-size: 0.8em; margin-top: 5px;">{progress_text} ({status})</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # XP History chart
            st.subheader("XP History")
            
            # Create a fake XP history for visualization
            # In a real app, you'd store and retrieve this from a database
            xp_dates = []
            xp_values = []
            today = datetime.now().date()
            
            # Start with a base XP value
            current_xp = max(0, user_stats["xp"] - 500)  # Subtract some XP to show growth
            
            # Generate XP history for last 30 days
            for i in range(30, 0, -1):
                date = today - timedelta(days=i)
                xp_dates.append(date)
                
                # Add some randomness to XP growth
                if i % 3 == 0:  # Every 3rd day has significant growth
                    current_xp += random.randint(20, 50)
                else:
                    current_xp += random.randint(0, 15)
                
                xp_values.append(current_xp)
            
            # Ensure the final value matches current XP
            xp_values[-1] = user_stats["xp"]
            
            # Create XP history dataframe
            xp_df = pd.DataFrame({"Date": xp_dates, "XP": xp_values})
            
            # Create a beautiful area chart with Plotly
            fig = px.area(
                xp_df, 
                x="Date", 
                y="XP", 
                title="Your XP Growth Over Time",
                labels={"XP": "Experience Points", "Date": ""},
                color_discrete_sequence=["#673ab7"]
            )
            
            # Customize the chart
            fig.update_layout(
                height=350,
                plot_bgcolor="white",
                xaxis=dict(
                    gridcolor="lightgray",
                    title_font=dict(size=14),
                ),
                yaxis=dict(
                    gridcolor="lightgray",
                    title_font=dict(size=14),
                ),
                title_font=dict(size=18),
                hoverlabel=dict(bgcolor="white", font_size=12),
            )
            
            # Add level threshold lines
            for level in range(1, user_stats["level"] + 2):
                fig.add_shape(
                    type="line",
                    x0=xp_df["Date"].min(),
                    y0=level * 100,
                    x1=xp_df["Date"].max(),
                    y1=level * 100,
                    line=dict(color="#9c27b0", dash="dash", width=1),
                )
                
                fig.add_annotation(
                    x=xp_df["Date"].min(),
                    y=level * 100,
                    text=f"Level {level}",
                    showarrow=False,
                    xshift=-70,
                    bgcolor="#9c27b0",
                    font=dict(color="white", size=10),
                    borderpad=4,
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Leaderboard section - FIXED
            st.subheader("Leaderboard")
            
            # Create a sample leaderboard
            # In a real app, you'd retrieve this from a database
            leaderboard_data = [
                {"rank": 1, "name": "PythonMaster92", "xp": user_stats["xp"] + 250, "level": user_stats["level"] + 1},
                {"rank": 2, "name": st.session_state.user["username"], "xp": user_stats["xp"], "level": user_stats["level"]},
                {"rank": 3, "name": "CodeNinja", "xp": user_stats["xp"] - 120, "level": user_stats["level"]},
                {"rank": 4, "name": "PyLearner", "xp": user_stats["xp"] - 300, "level": user_stats["level"] - 1},
                {"rank": 5, "name": "AlgorithmAce", "xp": user_stats["xp"] - 450, "level": user_stats["level"] - 1}
            ]
            
            # Display each leaderboard entry as a separate element
            for entry in leaderboard_data:
                # Highlight the current user
                is_current_user = entry["name"] == st.session_state.user["username"]
                bg_color = "#f3e5f5" if is_current_user else "white"
                font_weight = "bold" if is_current_user else "normal"
                
                # Medals for top 3
                if entry["rank"] == 1:
                    medal = '🥇'
                elif entry["rank"] == 2:
                    medal = '🥈'
                elif entry["rank"] == 3:
                    medal = '🥉'
                else:
                    medal = ''
                
                st.markdown(f"""
                <div style="display: flex; align-items: center; background-color: {bg_color}; 
                            padding: 12px; border-radius: 8px; margin-bottom: 10px; font-weight: {font_weight};">
                    <div style="width: 10%; text-align: center; font-size: 1.1em;">{entry["rank"]} {medal}</div>
                    <div style="width: 40%; padding-left: 10px;">{entry["name"]}{' (You)' if is_current_user else ''}</div>
                    <div style="width: 20%; text-align: center;">
                        <div style="background-color: #7b1fa2; color: white; border-radius: 20px; 
                                    padding: 3px 8px; display: inline-block;">
                            Lvl {entry["level"]}
                        </div>
                    </div>
                    <div style="width: 30%; text-align: right; padding-right: 10px;">{entry["xp"]:,} XP</div>
                </div>
                """, unsafe_allow_html=True)
                
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        debug_log(f"Major error in learning_path_page: {e}")
        debug_log(traceback.format_exc())
        st.warning("Please try refreshing the page. If the problem persists, contact support.")

# Helper function to generate improvement suggestions
def get_improvement_suggestion(topic):
    suggestions = {
        "Python Basics": "Review variables, data types, and basic operations",
        "Functions": "Practice creating and using functions with different parameters",
        "Classes": "Review object-oriented programming concepts",
        "Lists": "Practice list comprehensions and common list operations",
        "Dictionaries": "Work on dictionary methods and nested structures",
        "Loops": "Practice different loop structures and when to use each",
        "Algorithms": "Start with simple sorting and searching algorithms",
    }
    
    return suggestions.get(topic, "Focus on understanding core concepts")

# Stand-alone test function
if __name__ == "__main__":
    st.set_page_config(page_title="Learning Path Test", layout="wide")
    
    # Create mock session state for direct testing
    if 'user' not in st.session_state:
        st.session_state.user = {'id': 1, 'username': 'test_user'}
    
    learning_path_page()

# Exports for importing from other modules
__all__ = ['learning_path_page']