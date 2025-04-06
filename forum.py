# forum.py
import streamlit as st
import datetime
from db_utils import get_db_connection, log_activity

def init_forum_db():
    """Initialize the database tables for the forum"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create forum_topics table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forum_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        category TEXT NOT NULL,
        tags TEXT,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )
    ''')
    
    # Create forum_posts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forum_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        parent_id INTEGER,
        is_solution BOOLEAN DEFAULT 0,
        FOREIGN KEY (topic_id) REFERENCES forum_topics (id),
        FOREIGN KEY (created_by) REFERENCES users (id),
        FOREIGN KEY (parent_id) REFERENCES forum_posts (id)
    )
    ''')
    
    # Create forum_likes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forum_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES forum_posts (id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(post_id, user_id)
    )
    ''')
    
    # Create indexes for faster queries
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_forum_topics
    ON forum_topics (category, created_at)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_forum_posts
    ON forum_posts (topic_id, created_at)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_forum_replies
    ON forum_posts (parent_id)
    ''')
    
    conn.commit()
    conn.close()
    
    return True

def get_all_topics(category=None, limit=50):
    """Get all forum topics, optionally filtered by category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if category and category != "All Categories":
        cursor.execute('''
        SELECT t.id, t.title, t.description, t.created_at, t.category, t.tags,
               u.username as created_by, 
               COUNT(DISTINCT p.id) as reply_count
        FROM forum_topics t
        JOIN users u ON t.created_by = u.id
        LEFT JOIN forum_posts p ON t.id = p.topic_id
        WHERE t.category = ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT ?
        ''', (category, limit))
    else:
        cursor.execute('''
        SELECT t.id, t.title, t.description, t.created_at, t.category, t.tags,
               u.username as created_by, 
               COUNT(DISTINCT p.id) as reply_count
        FROM forum_topics t
        JOIN users u ON t.created_by = u.id
        LEFT JOIN forum_posts p ON t.id = p.topic_id
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT ?
        ''', (limit,))
    
    topics = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for t in topics:
        result.append({
            "id": t[0],
            "title": t[1],
            "description": t[2],
            "created_at": t[3],
            "category": t[4],
            "tags": t[5].split(",") if t[5] else [],
            "created_by": t[6],
            "reply_count": t[7]
        })
    
    return result

def get_topic_details(topic_id):
    """Get details of a specific topic"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT t.id, t.title, t.description, t.created_at, t.category, t.tags,
           u.username as created_by, u.id as user_id
    FROM forum_topics t
    JOIN users u ON t.created_by = u.id
    WHERE t.id = ?
    ''', (topic_id,))
    
    topic = cursor.fetchone()
    conn.close()
    
    if not topic:
        return None
    
    return {
        "id": topic[0],
        "title": topic[1],
        "description": topic[2],
        "created_at": topic[3],
        "category": topic[4],
        "tags": topic[5].split(",") if topic[5] else [],
        "created_by": topic[6],
        "user_id": topic[7]
    }

def get_posts_for_topic(topic_id):
    """Get all posts for a specific topic"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT p.id, p.content, p.created_at, p.parent_id, p.is_solution,
           u.username as created_by, u.id as user_id,
           (SELECT COUNT(*) FROM forum_likes WHERE post_id = p.id) as like_count
    FROM forum_posts p
    JOIN users u ON p.created_by = u.id
    WHERE p.topic_id = ? AND p.parent_id IS NULL
    ORDER BY p.created_at
    ''', (topic_id,))
    
    posts = cursor.fetchall()
    
    # Get all replies
    cursor.execute('''
    SELECT p.id, p.content, p.created_at, p.parent_id, p.is_solution,
           u.username as created_by, u.id as user_id,
           (SELECT COUNT(*) FROM forum_likes WHERE post_id = p.id) as like_count
    FROM forum_posts p
    JOIN users u ON p.created_by = u.id
    WHERE p.topic_id = ? AND p.parent_id IS NOT NULL
    ORDER BY p.created_at
    ''', (topic_id,))
    
    replies = cursor.fetchall()
    conn.close()
    
    # Convert to dictionaries and build reply hierarchy
    posts_dict = {}
    for p in posts:
        posts_dict[p[0]] = {
            "id": p[0],
            "content": p[1],
            "created_at": p[2],
            "parent_id": p[3],
            "is_solution": p[4] == 1,
            "created_by": p[5],
            "user_id": p[6],
            "like_count": p[7],
            "replies": []
        }
    
    # Add replies to parent posts
    for r in replies:
        parent_id = r[3]
        if parent_id in posts_dict:
            posts_dict[parent_id]["replies"].append({
                "id": r[0],
                "content": r[1],
                "created_at": r[2],
                "parent_id": r[3],
                "is_solution": r[4] == 1,
                "created_by": r[5],
                "user_id": r[6],
                "like_count": r[7]
            })
    
    return list(posts_dict.values())

def create_topic(title, description, category, tags, created_by):
    """Create a new topic in the forum"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tags_str = ",".join(tags) if tags else ""
    
    cursor.execute('''
    INSERT INTO forum_topics (title, description, created_by, created_at, category, tags)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, description, created_by, datetime.datetime.now().isoformat(), category, tags_str))
    
    topic_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Log activity
    log_activity(created_by, "forum_topic_created", {"topic_id": topic_id, "title": title})
    
    return topic_id

def create_post(topic_id, content, created_by, parent_id=None):
    """Create a new post or reply in a topic"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO forum_posts (topic_id, content, created_by, created_at, parent_id)
    VALUES (?, ?, ?, ?, ?)
    ''', (topic_id, content, created_by, datetime.datetime.now().isoformat(), parent_id))
    
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Log activity
    log_activity(created_by, "forum_post_created", {"topic_id": topic_id, "post_id": post_id})
    
    return post_id

def mark_as_solution(post_id, user_id):
    """Mark a post as the solution to a topic"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First, get the topic id and creator
    cursor.execute('''
    SELECT p.topic_id, t.created_by 
    FROM forum_posts p
    JOIN forum_topics t ON p.topic_id = t.id
    WHERE p.id = ?
    ''', (post_id,))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return False
    
    topic_id, topic_creator = result
    
    # Only the topic creator can mark solutions
    if topic_creator != user_id:
        conn.close()
        return False
    
    # Update the post to mark it as a solution
    cursor.execute('''
    UPDATE forum_posts SET is_solution = 1
    WHERE id = ?
    ''', (post_id,))
    
    conn.commit()
    conn.close()
    
    # Log activity
    log_activity(user_id, "forum_solution_marked", {"topic_id": topic_id, "post_id": post_id})
    
    return True

def like_post(post_id, user_id):
    """Add a like to a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO forum_likes (post_id, user_id, created_at)
        VALUES (?, ?, ?)
        ''', (post_id, user_id, datetime.datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Log activity
        log_activity(user_id, "forum_post_liked", {"post_id": post_id})
        
        return True
    except Exception as e:
        # Likely a duplicate like
        conn.close()
        return False

def unlike_post(post_id, user_id):
    """Remove a like from a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    DELETE FROM forum_likes 
    WHERE post_id = ? AND user_id = ?
    ''', (post_id, user_id))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected > 0:
        # Log activity
        log_activity(user_id, "forum_post_unliked", {"post_id": post_id})
    
    return affected > 0

def has_user_liked_post(post_id, user_id):
    """Check if a user has liked a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT COUNT(*) FROM forum_likes
    WHERE post_id = ? AND user_id = ?
    ''', (post_id, user_id))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0

def get_user_topics(user_id, limit=10):
    """Get topics created by a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT t.id, t.title, t.created_at, t.category, 
           COUNT(DISTINCT p.id) as reply_count
    FROM forum_topics t
    LEFT JOIN forum_posts p ON t.id = p.topic_id
    WHERE t.created_by = ?
    GROUP BY t.id
    ORDER BY t.created_at DESC
    LIMIT ?
    ''', (user_id, limit))
    
    topics = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for t in topics:
        result.append({
            "id": t[0],
            "title": t[1],
            "created_at": t[2],
            "category": t[3],
            "reply_count": t[4]
        })
    
    return result

def get_popular_topics(limit=5):
    """Get the most active topics based on reply count"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT t.id, t.title, t.category, 
           COUNT(DISTINCT p.id) as reply_count
    FROM forum_topics t
    LEFT JOIN forum_posts p ON t.id = p.topic_id
    GROUP BY t.id
    ORDER BY reply_count DESC, t.created_at DESC
    LIMIT ?
    ''', (limit,))
    
    topics = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for t in topics:
        result.append({
            "id": t[0],
            "title": t[1],
            "category": t[2],
            "reply_count": t[3]
        })
    
    return result

def search_topics(query, limit=20):
    """Search topics based on title, description or tags"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    search_term = f"%{query}%"
    
    cursor.execute('''
    SELECT t.id, t.title, t.description, t.created_at, t.category, t.tags,
           u.username as created_by, 
           COUNT(DISTINCT p.id) as reply_count
    FROM forum_topics t
    JOIN users u ON t.created_by = u.id
    LEFT JOIN forum_posts p ON t.id = p.topic_id
    WHERE t.title LIKE ? OR t.description LIKE ? OR t.tags LIKE ?
    GROUP BY t.id
    ORDER BY t.created_at DESC
    LIMIT ?
    ''', (search_term, search_term, search_term, limit))
    
    topics = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for t in topics:
        result.append({
            "id": t[0],
            "title": t[1],
            "description": t[2],
            "created_at": t[3],
            "category": t[4],
            "tags": t[5].split(",") if t[5] else [],
            "created_by": t[6],
            "reply_count": t[7]
        })
    
    return result

def forum_page():
    """Main forum page with topic listing and navigation"""
    st.title("🧩 Python Learning Community Forum")
    
    # Initialize forum database if needed
    init_forum_db()
    
    # Set up tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📚 Browse Topics", "➕ Create Topic", "🔍 Search"])
    
    with tab1:
        st.header("Browse Discussion Topics")
        
        # Filter topics by category
        categories = ["All Categories", "Python Basics", "Data Structures", "Functions", 
                     "OOP", "Libraries", "Web Development", "Data Science", "Other"]
        
        selected_category = st.selectbox("Filter by category:", categories)
        
        # Get topics based on filter
        topics = get_all_topics(selected_category if selected_category != "All Categories" else None)
        
        if not topics:
            st.info("No topics found in this category. Be the first to create one!")
        else:
            # Display each topic as a card
            for topic in topics:
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"### [{topic['title']}](#topic/{topic['id']})")
                        st.markdown(f"*{topic['description'][:100]}..." if len(topic['description']) > 100 else f"*{topic['description']}*")
                        st.caption(f"Posted by: {topic['created_by']} | Category: {topic['category']} | {topic['created_at'][:10]}")
                        
                        # Display tags
                        if topic['tags']:
                            tags_html = " ".join([f"<span style='background-color: #f0f2f6; padding: 2px 8px; border-radius: 10px; margin-right: 5px; font-size: 0.8em;'>{tag}</span>" for tag in topic['tags']])
                            st.markdown(f"{tags_html}", unsafe_allow_html=True)
                    
                    with col2:
                        st.metric("Replies", topic['reply_count'])
                        if st.button("View", key=f"view_{topic['id']}"):
                            st.session_state.forum_view = "topic"
                            st.session_state.forum_topic_id = topic['id']
                            st.rerun()
                    
                    st.markdown("---")
        
        # Popular topics sidebar
        st.sidebar.header("Popular Discussions")
        popular_topics = get_popular_topics()
        
        for topic in popular_topics:
            st.sidebar.markdown(f"**[{topic['title']}](#topic/{topic['id']})**")
            st.sidebar.caption(f"{topic['reply_count']} replies | {topic['category']}")
            
            if st.sidebar.button("View", key=f"side_{topic['id']}"):
                st.session_state.forum_view = "topic"
                st.session_state.forum_topic_id = topic['id']
                st.rerun()
            
            st.sidebar.markdown("---")
    
    with tab2:
        st.header("Create a New Topic")
        
        topic_title = st.text_input("Title", max_chars=100)
        topic_description = st.text_area("Description", height=150)
        
        category = st.selectbox("Category", 
                               ["Python Basics", "Data Structures", "Functions", 
                                "OOP", "Libraries", "Web Development", "Data Science", "Other"])
        
        tags_input = st.text_input("Tags (comma separated)", 
                                  placeholder="e.g., beginner, lists, functions")
        
        if st.button("Create Topic"):
            if not topic_title or not topic_description:
                st.error("Please provide both a title and description.")
            else:
                tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
                
                topic_id = create_topic(
                    topic_title, 
                    topic_description,
                    category,
                    tags,
                    st.session_state.user["id"]
                )
                
                st.success(f"Topic created successfully!")
                
                # Navigate to the new topic
                st.session_state.forum_view = "topic"
                st.session_state.forum_topic_id = topic_id
                st.rerun()
    
    with tab3:
        st.header("Search Topics")
        
        search_query = st.text_input("Search by keyword, topic, or tag")
        
        if search_query:
            search_results = search_topics(search_query)
            
            if not search_results:
                st.info("No topics found matching your search.")
            else:
                st.write(f"Found {len(search_results)} topics matching '{search_query}'")
                
                for topic in search_results:
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"### {topic['title']}")
                            st.markdown(f"*{topic['description'][:100]}..." if len(topic['description']) > 100 else f"*{topic['description']}*")
                            st.caption(f"Posted by: {topic['created_by']} | Category: {topic['category']} | {topic['created_at'][:10]}")
                        
                        with col2:
                            st.metric("Replies", topic['reply_count'])
                            if st.button("View", key=f"search_{topic['id']}"):
                                st.session_state.forum_view = "topic"
                                st.session_state.forum_topic_id = topic['id']
                                st.rerun()
                        
                        st.markdown("---")

def topic_view(topic_id):
    """Display a single topic and its discussions"""
    # Get topic details
    topic = get_topic_details(topic_id)
    
    if not topic:
        st.error("Topic not found.")
        if st.button("Back to Forum"):
            st.session_state.forum_view = "main"
            st.rerun()
        return
    
    # Show topic details
    st.title(topic["title"])
    st.caption(f"Posted by: {topic['created_by']} | Category: {topic['category']} | {topic['created_at'][:10]}")
    
    # Display tags
    if topic['tags']:
        tags_html = " ".join([f"<span style='background-color: #f0f2f6; padding: 2px 8px; border-radius: 10px; margin-right: 5px; font-size: 0.8em;'>{tag}</span>" for tag in topic['tags']])
        st.markdown(f"{tags_html}", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(topic["description"])
    st.markdown("---")
    
    # Get posts for this topic
    posts = get_posts_for_topic(topic_id)
    
    # Add a new post
    with st.expander("Add a Response"):
        post_content = st.text_area("Your response", height=150, key="new_post")
        if st.button("Post Response"):
            if not post_content:
                st.error("Please write something before posting.")
            else:
                post_id = create_post(
                    topic_id,
                    post_content,
                    st.session_state.user["id"]
                )
                st.success("Response posted successfully!")
                st.rerun()
    
    # Display posts and replies
    st.subheader(f"Responses ({len(posts)})")
    
    if not posts:
        st.info("No responses yet. Be the first to respond!")
    else:
        for post in posts:
            with st.container():
                # Check if this post is a solution
                if post["is_solution"]:
                    st.markdown("✅ **SOLUTION**")
                
                # Post content
                st.markdown(post["content"])
                st.caption(f"Posted by: {post['created_by']} | {post['created_at'][:10]}")
                
                # Like button
                col1, col2, col3 = st.columns([1, 1, 8])
                
                # Check if current user has liked this post
                user_liked = has_user_liked_post(post["id"], st.session_state.user["id"])
                
                with col1:
                    if user_liked:
                        if st.button("❤️", key=f"unlike_{post['id']}"):
                            unlike_post(post["id"], st.session_state.user["id"])
                            st.rerun()
                    else:
                        if st.button("🤍", key=f"like_{post['id']}"):
                            like_post(post["id"], st.session_state.user["id"])
                            st.rerun()
                
                with col2:
                    st.write(f"{post['like_count']}")
                
                with col3:
                    # Mark as solution button (only visible to topic creator)
                    if topic["user_id"] == st.session_state.user["id"] and not post["is_solution"]:
                        if st.button("Mark as Solution", key=f"solution_{post['id']}"):
                            mark_as_solution(post["id"], st.session_state.user["id"])
                            st.success("Response marked as solution!")
                            st.rerun()
                
                # Add reply expander
                with st.expander("Reply"):
                    reply_content = st.text_area("Your reply", height=100, key=f"reply_{post['id']}")
                    if st.button("Submit Reply", key=f"submit_reply_{post['id']}"):
                        if not reply_content:
                            st.error("Please write something before posting.")
                        else:
                            create_post(
                                topic_id,
                                reply_content,
                                st.session_state.user["id"],
                                post["id"]
                            )
                            st.success("Reply posted successfully!")
                            st.rerun()
                
                # Display replies
                if post["replies"]:
                    with st.container():
                        st.markdown(f"**{len(post['replies'])} Replies**")
                        
                        for reply in post["replies"]:
                            st.markdown("---")
                            st.markdown(f"> {reply['content']}")
                            st.caption(f"Reply by: {reply['created_by']} | {reply['created_at'][:10]}")
                            
                            # Like button for replies
                            rcol1, rcol2, rcol3 = st.columns([1, 1, 8])
                            
                            # Check if current user has liked this reply
                            user_liked_reply = has_user_liked_post(reply["id"], st.session_state.user["id"])
                            
                            with rcol1:
                                if user_liked_reply:
                                    if st.button("❤️", key=f"unlike_reply_{reply['id']}"):
                                        unlike_post(reply["id"], st.session_state.user["id"])
                                        st.rerun()
                                else:
                                    if st.button("🤍", key=f"like_reply_{reply['id']}"):
                                        like_post(reply["id"], st.session_state.user["id"])
                                        st.rerun()
                            
                            with rcol2:
                                st.write(f"{reply['like_count']}")
                
                st.markdown("---")
    
    # Navigation button to go back to forum
    if st.button("Back to Forum"):
        st.session_state.forum_view = "main"
        st.rerun()

def community_forum_page():
    """
    Main entry point for the community forum feature
    """
    # Initialize forum in session state
    if "forum_view" not in st.session_state:
        st.session_state.forum_view = "main"
    
    # Determine which view to show
    if st.session_state.forum_view == "main":
        forum_page()
    elif st.session_state.forum_view == "topic" and "forum_topic_id" in st.session_state:
        topic_view(st.session_state.forum_topic_id)
    else:
        # Default to main forum view
        forum_page()