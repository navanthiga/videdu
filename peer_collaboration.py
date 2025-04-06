# peer_collaboration.py
import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import sqlite3
import random
import time
from datetime import datetime
import uuid
import plotly.express as px
import plotly.graph_objects as go
from db_utils import get_db_connection, log_activity

def load_student_data():
    """Load student data from SQLite database"""
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
                
                # Get quiz performance
                cursor.execute("""
                    SELECT topic, AVG(score * 100.0 / max_score) as avg_score
                    FROM quiz_attempts
                    WHERE user_id = ?
                    GROUP BY topic
                """, (user_id,))
                
                quiz_results = cursor.fetchall()
                
                # Calculate average Python quiz score
                python_score = 0
                python_count = 0
                
                for topic, score in quiz_results:
                    if 'python' in topic.lower():
                        python_score += score
                        python_count += 1
                
                quiz_score_python = python_score / python_count if python_count > 0 else 50
                
                # Get video watch time
                cursor.execute("""
                    SELECT topic, SUM(watch_count) as total_watches
                    FROM videos_watched
                    WHERE user_id = ?
                    GROUP BY topic
                """, (user_id,))
                
                watch_results = cursor.fetchall()
                
                # Calculate watch time for Python videos
                python_time = 0
                
                for topic, count in watch_results:
                    if 'python' in topic.lower():
                        python_time += count * 10  # Assume 10 min per watch
                
                # Check if user is already in study groups
                cursor.execute("""
                    SELECT COUNT(*) FROM study_group_members
                    WHERE user_id = ?
                """, (user_id,))
                
                group_count = cursor.fetchone()[0]
                
                # Get user's preferred Python topics
                cursor.execute("""
                    SELECT sg.topic 
                    FROM study_groups sg
                    JOIN study_group_members sgm ON sg.group_id = sgm.group_id
                    WHERE sgm.user_id = ?
                """, (user_id,))
                
                topics = cursor.fetchall()
                preferred_topics = [topic[0] for topic in topics] if topics else ["Python Basics"]
                
                # Create student entry
                student_entry = {
                    "Student": full_name,
                    "User_ID": user_id,
                    "Quiz_Score_Python": quiz_score_python,
                    "Watch_Time_Python": python_time if python_time > 0 else random.randint(50, 150),
                    "Learning_Style": "Visual",
                    "Group_Count": group_count,
                    "Preferred_Topics": ", ".join(preferred_topics[:2]) if len(preferred_topics) > 1 else preferred_topics[0]
                }
                
                data.append(student_entry)
            except Exception as e:
                print(f"Error processing user {user[1]}: {e}")
                continue
        
        conn.close()
        
        # If no user data yet, provide sample data
        if not data:
            data = [
                {"Student": "Amogha", "User_ID": 999, "Quiz_Score_Python": 85, "Watch_Time_Python": 120, "Learning_Style": "Visual", "Group_Count": 2, "Preferred_Topics": "Python Basics"},
                {"Student": "Kushi Gupta", "User_ID": 998, "Quiz_Score_Python": 65, "Watch_Time_Python": 60, "Learning_Style": "Visual", "Group_Count": 1, "Preferred_Topics": "Python Advanced"},
                {"Student": "Dev", "User_ID": 997, "Quiz_Score_Python": 90, "Watch_Time_Python": 180, "Learning_Style": "Visual", "Group_Count": 3, "Preferred_Topics": "Data Analysis"},
                {"Student": "Kabir", "User_ID": 996, "Quiz_Score_Python": 45, "Watch_Time_Python": 50, "Learning_Style": "Visual", "Group_Count": 0, "Preferred_Topics": "Python Basics"},
                {"Student": "Oviya", "User_ID": 995, "Quiz_Score_Python": 75, "Watch_Time_Python": 100, "Learning_Style": "Visual", "Group_Count": 1, "Preferred_Topics": "Python Advanced"},
            ]
        
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error in load_student_data: {e}")
        # Return sample data as fallback
        return pd.DataFrame([
            {"Student": "Amogha", "User_ID": 999, "Quiz_Score_Python": 85, "Watch_Time_Python": 120, "Learning_Style": "Visual", "Group_Count": 2, "Preferred_Topics": "Python Basics"},
            {"Student": "Kushi Gupta", "User_ID": 998, "Quiz_Score_Python": 65, "Watch_Time_Python": 60, "Learning_Style": "Visual", "Group_Count": 1, "Preferred_Topics": "Python Advanced"},
            {"Student": "Dev", "User_ID": 997, "Quiz_Score_Python": 90, "Watch_Time_Python": 180, "Learning_Style": "Visual", "Group_Count": 3, "Preferred_Topics": "Data Analysis"},
            {"Student": "Kabir", "User_ID": 996, "Quiz_Score_Python": 45, "Watch_Time_Python": 50, "Learning_Style": "Visual", "Group_Count": 0, "Preferred_Topics": "Python Basics"},
            {"Student": "Oviya", "User_ID": 995, "Quiz_Score_Python": 75, "Watch_Time_Python": 100, "Learning_Style": "Visual", "Group_Count": 1, "Preferred_Topics": "Python Advanced"},
        ])

def get_user_study_groups(user_id):
    """Get all study groups that a user is a member of"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sg.group_id, sg.topic, sg.description, sg.created_at, u.username as creator
            FROM study_groups sg
            JOIN study_group_members sgm ON sg.group_id = sgm.group_id
            JOIN users u ON sg.creator_id = u.id
            WHERE sgm.user_id = ?
        """, (user_id,))
        
        groups = cursor.fetchall()
        
        # Format the results
        formatted_groups = []
        for group in groups:
            # Get the count of members in this group
            cursor.execute("""
                SELECT COUNT(*) FROM study_group_members
                WHERE group_id = ?
            """, (group[0],))
            
            member_count = cursor.fetchone()[0]
            
            # Format creation date
            try:
                created_at = datetime.fromisoformat(group[3]).strftime("%d %b %Y")
            except:
                created_at = group[3]
            
            formatted_groups.append({
                "group_id": group[0],
                "topic": group[1],
                "description": group[2],
                "created_at": created_at,
                "creator": group[4],
                "member_count": member_count
            })
        
        conn.close()
        return formatted_groups
    except Exception as e:
        print(f"Error getting user study groups: {e}")
        return []

def cluster_students(student_data, n_clusters=3):
    """Cluster students based on their learning metrics"""
    # Features for clustering
    features = student_data[["Quiz_Score_Python", "Watch_Time_Python"]]
    
    # Standardize features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    
    # k-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(scaled_features)
    student_data["Cluster"] = clusters
    
    # Calculate cluster centers for visualization
    cluster_centers = scaler.inverse_transform(kmeans.cluster_centers_)
    
    return student_data, cluster_centers

def match_peers(student_data, current_student, same_learning_style=False):
    """Match similar peers based on clustering"""
    # Get current student's cluster and learning style
    current_student_row = student_data[student_data["Student"] == current_student]
    if current_student_row.empty:
        return []
    
    cluster = current_student_row["Cluster"].iloc[0]
    learning_style = current_student_row["Learning_Style"].iloc[0]
    
    # Find peers in the same cluster
    if same_learning_style:
        peers = student_data[(student_data["Cluster"] == cluster) & 
                             (student_data["Learning_Style"] == learning_style) &
                             (student_data["Student"] != current_student)]
    else:
        peers = student_data[(student_data["Cluster"] == cluster) & 
                             (student_data["Student"] != current_student)]
    
    # If no peers found, just find anyone not the current student
    if peers.empty:
        peers = student_data[student_data["Student"] != current_student]
    
    # Select up to 3 peers
    if len(peers) > 3:
        peers = peers.sample(3)
        
    return peers.to_dict('records')

def get_strengths(student_data):
    """Determine student strengths based on their data"""
    strengths = []
    
    # Check Python score
    if student_data["Quiz_Score_Python"] >= 80:
        strengths.append("Python Expert")
    elif student_data["Quiz_Score_Python"] >= 60:
        strengths.append("Python Intermediate")
    else:
        strengths.append("Python Beginner")
    
    # Check for high watch time
    if student_data["Watch_Time_Python"] > 150:
        strengths.append("Dedicated Python Learner")
    elif student_data["Watch_Time_Python"] > 80:
        strengths.append("Regular Python Practitioner")
    
    # Add Python-specific strengths based on preferred topics
    if "Preferred_Topics" in student_data:
        preferred_topics = student_data["Preferred_Topics"].lower()
        if "data" in preferred_topics:
            strengths.append("Data Science")
        elif "web" in preferred_topics:
            strengths.append("Web Development")
        elif "advanced" in preferred_topics:
            strengths.append("Advanced Python")
        elif "game" in preferred_topics:
            strengths.append("Game Development")
        else:
            strengths.append("Python Fundamentals")
    
    # Return comma-separated strengths
    return ", ".join(strengths) if strengths else "Still developing"

def create_study_group(creator_id, peer_ids, topic, description):
    """Create a new study group"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate a unique group ID
        group_id = str(uuid.uuid4())[:8]
        creation_time = datetime.now().isoformat()
        
        # Create the group
        cursor.execute("""
            INSERT INTO study_groups (group_id, creator_id, topic, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (group_id, creator_id, topic, description, creation_time))
        
        # Add members to the group (including creator)
        all_members = [creator_id] + peer_ids
        for member_id in all_members:
            cursor.execute("""
                INSERT INTO study_group_members (group_id, user_id, joined_at)
                VALUES (?, ?, ?)
            """, (group_id, member_id, creation_time))
        
        conn.commit()
        conn.close()
        
        # Log activity
        log_activity(creator_id, "create_study_group", {"group_id": group_id, "topic": topic})
        
        return group_id
    except Exception as e:
        print(f"Error creating study group: {e}")
        return None

def peer_collaboration_page():
    """Main function for the peer collaboration page"""
    # Check if user is logged in
    if 'user' not in st.session_state or not st.session_state.user:
        st.warning("Please log in to use the peer collaboration feature.")
        return
    
    # Get user data
    user_id = st.session_state.user['id']
    username = st.session_state.user['username']
    
    # Add custom CSS with dark blue, light blue, and white theme
    st.markdown("""
    <style>
    /* Main theme colors - Dark blue, light blue, white */
    :root {
        --dark-blue: #1e3a8a;
        --medium-blue: #3b82f6;
        --light-blue: #bfdbfe;
        --white: #ffffff;
    }
    
    /* Streamlit background */
    .stApp {
        background-color: var(--white);
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--dark-blue);
    }
    
    /* Peer card styling */
    .peer-card {
        background-color: var(--white);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid var(--medium-blue);
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Group card styling */
    .group-card {
        background-color: var(--light-blue);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid var(--dark-blue);
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Match button styling */
    .match-button {
        background-color: var(--medium-blue);
        color: var(--white);
        border-radius: 10px;
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 20px;
        font-size: 0.8em;
        margin-right: 5px;
    }
    
    .badge.visual {
        background-color: var(--light-blue);
        color: var(--dark-blue);
    }
    
    .badge.topic {
        background-color: var(--dark-blue);
        color: var(--white);
    }
    
    /* Button styling */
    .stButton>button {
        background-color: var(--medium-blue);
        color: var(--white);
    }
    
    .stButton>button:hover {
        background-color: var(--dark-blue);
        color: var(--white);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: var(--light-blue);
        color: var(--dark-blue);
        border-radius: 4px 4px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--medium-blue);
        color: var(--white);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Page title and description
    st.title("✨ Find Your Python Study Buddies")
    st.write("Connect with peers who have similar Python learning patterns!")
    
    # Create tabs for Find Peers and My Groups
    tab1, tab2 = st.tabs(["Find Study Partners", "My Study Groups"])
    
    with tab1:
        # Create two columns for the form and results
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Match Settings")
            
            # Learning style preference
            same_learning_style = st.checkbox("Match with same learning style", value=False)
            
            # Topic selection - Python skill levels
            level_options = ["Beginner", "Intermediate", "Advanced"]
            selected_level = st.selectbox("Your skill level:", level_options)
            
            # Description
            group_description = st.text_area("Group description:", 
                                   placeholder="E.g., Python study group for Django...",
                                   max_chars=200)
            
            # Match button
            if st.button("Find My Study Match", type="primary", use_container_width=True):
                # Load and cluster student data
                with st.spinner("Analyzing Python learning patterns..."):
                    student_data = load_student_data()
                    
                    # Check if current user exists in data
                    if username not in student_data["Student"].values:
                        st.error(f"User {username} not found in student data. Please take some Python quizzes and watch videos first.")
                        # Add current user with default values
                        new_user = {
                            "Student": username,
                            "User_ID": user_id,
                            "Quiz_Score_Python": 50,
                            "Watch_Time_Python": 60,
                            "Learning_Style": "Visual",
                            "Group_Count": 0,
                            "Preferred_Topics": "Python Basics"
                        }
                        student_data = pd.concat([student_data, pd.DataFrame([new_user])], ignore_index=True)
                    
                    # Apply clustering
                    clustered_data, _ = cluster_students(student_data)
                    
                    # Match peers
                    matched_peers = match_peers(clustered_data, username, same_learning_style)
                    
                    if matched_peers:
                        # Store matches in session state
                        st.session_state.matched_peers = matched_peers
                        st.session_state.selected_level = selected_level
                        st.session_state.group_description = group_description
                        
                        # Simulate processing for better UX
                        progress_bar = st.progress(0)
                        for percent_complete in range(100):
                            time.sleep(0.01)
                            progress_bar.progress(percent_complete + 1)
                        
                        st.success("Perfect Python study partners found! Check them out on the right.")
                    else:
                        st.error("No matching peers found. Try adjusting your criteria.")
        
        with col2:
            # Show matched peers if available
            if hasattr(st.session_state, 'matched_peers') and st.session_state.matched_peers:
                st.subheader("Your Perfect Python Study Partners")
                
                # Display each peer
                for peer in st.session_state.matched_peers:
                    # Get peer's details
                    peer_style = "Visual"
                    style_class = peer_style.lower()
                    preferred_topics = peer.get("Preferred_Topics", "Python")
                    
                    st.markdown(f"""
                    <div class="peer-card">
                        <h3>{peer["Student"]}</h3>
                        <div style="display: flex; margin-bottom: 10px;">
                            <div style="flex: 1;">
                                <span style="font-weight: bold;">Python Score:</span> {peer["Quiz_Score_Python"]:.1f}%
                            </div>
                            <div style="flex: 1;">
                                <span style="font-weight: bold;">Groups:</span> {peer.get("Group_Count", 0)}
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <span class="badge topic">{preferred_topics}</span>
                        </div>
                        <div style="font-size: 0.9em; color: #666;">
                            Strengths: {get_strengths(peer)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Create group button
                if st.button("Create Study Group", type="primary"):
                    peer_ids = [peer["User_ID"] for peer in st.session_state.matched_peers]
                    group_id = create_study_group(
                        user_id, 
                        peer_ids, 
                        st.session_state.selected_level, 
                        st.session_state.group_description
                    )
                    
                    if group_id:
                        # Show success message with group details
                        st.success(f"Python study group created successfully! Group ID: {group_id}")
                        
                        # Add video call option
                        jitsi_link = f"https://meet.jit.si/Group_{group_id}"
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; border-radius: 10px; padding: 20px; margin-top: 20px; text-align: center;">
                            <h3>Start Python Coding Session Now</h3>
                            <p>Pair program, share code, and solve Python problems together!</p>
                            <a href="{jitsi_link}" target="_blank" style="text-decoration: none;">
                                <button style="background-color: #bfdbfe; color: #1e3a8a; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                                    Join Video Call
                                </button>
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("Failed to create study group. Please try again.")
            else:
                
                # Show existing registered users as suggestions
                st.subheader("Suggested Python Learners")
                
                # Load student data
                student_data = load_student_data()
                
                # Filter out current user
                current_username = st.session_state.user.get('full_name') or st.session_state.user['username']
                filtered_data = student_data[student_data["Student"] != current_username]
                
                if not filtered_data.empty:
                    # Select 3 random users
                    suggestions = filtered_data.sample(min(3, len(filtered_data)))
                    
                    for _, peer in suggestions.iterrows():
                        preferred_topics = peer.get("Preferred_Topics", "Python")
                        
                        st.markdown(f"""
                        <div class="peer-card">
                            <h3>{peer["Student"]}</h3>
                            <div style="display: flex; margin-bottom: 10px;">
                                <div style="flex: 1;">
                                    <span style="font-weight: bold;">Python Score:</span> {peer["Quiz_Score_Python"]:.1f}%
                                </div>
                                <div style="flex: 1;">
                                    <span style="font-weight: bold;">Groups:</span> {peer.get("Group_Count", 0)}
                                </div>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <span class="badge topic">{preferred_topics}</span>
                            </div>
                            <div style="font-size: 0.9em; color: #666;">
                                Recent Activity: {random.choice([
                                    "Completed Python quizzes", 
                                    "Watched Python tutorial videos",
                                    "Practicing with Python frameworks",
                                    "Learning about Python data science"
                                ])}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.write("""
                    **Why connect with these Python learners?**
                    - Similar coding experience levels
                    - Complementary Python skills
                    - Active in the coding community
                    """)
                else:
                    st.info("Be the first to invite friends! No other Python learners found yet.")
                    
                # Add refresh button
                if st.button("Refresh Suggestions", key="refresh_suggestions"):
                    st.rerun()

    with tab2:
        st.subheader("My Python Study Groups")
        
        # Fetch user's study groups
        user_groups = get_user_study_groups(user_id)
        
        if user_groups:
            for group in user_groups:
                # Display each group with details
                st.markdown(f"""
                <div class="group-card">
                    <h3>{group["topic"]}</h3>
                    <div style="display: flex; margin-bottom: 10px;">
                        <div style="flex: 1;">
                            <span style="font-weight: bold;">Group ID:</span> {group["group_id"]}
                        </div>
                        <div style="flex: 1;">
                            <span style="font-weight: bold;">Members:</span> {group["member_count"]}
                        </div>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <span style="font-weight: bold;">Created:</span> {group["created_at"]} by {group["creator"]}
                    </div>
                    <div style="font-size: 0.9em; margin-bottom: 10px;">
                        {group["description"] if group["description"] else "No description available."}
                    </div>
                    <a href="https://meet.jit.si/Group_{group["group_id"]}" target="_blank" style="text-decoration: none;">
                        <button style="background-color: #1e3a8a; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 0.9em;">
                            Join Video Call
                        </button>
                    </a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("You haven't joined any study groups yet. Find peers and create a group to get started!")
            
            # Show a create group button that redirects to the Find Peers tab
            if st.button("Find Study Partners", type="primary"):
                # This will switch to the first tab
                st.experimental_rerun()

# For standalone testing
if __name__ == "__main__":
    st.set_page_config(page_title="Python Peer Collaboration", layout="wide")
    
    # Create mock session state for direct testing
    if 'user' not in st.session_state:
        st.session_state.user = {'id': 1, 'username': 'test_user'}
    
    peer_collaboration_page()