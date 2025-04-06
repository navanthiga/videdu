# auth.py
import streamlit as st
from db_utils import register_user, authenticate_user, init_db

def login_page():
    """Display login page and handle authentication"""
    # Initialize database if not exists
    init_db()
    
    # CSS for a nicer login form
    st.markdown("""
    <style>
        .auth-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            background-color: #f8f9fa;
            margin-top: 50px;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 20px;
        }
        .auth-form {
            display: flex;
            flex-direction: column;
        }
        .auth-tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #dee2e6;
        }
        .auth-tab {
            padding: 10px 15px;
            cursor: pointer;
            flex: 1;
            text-align: center;
        }
        .auth-tab.active {
            border-bottom: 2px solid #4CAF50;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Logo and header
    st.image("https://www.python.org/static/community_logos/python-logo-generic.svg", width=100)
    st.title("Python Learning Platform")
    
    # Initialize session state for authentication
    if 'auth_status' not in st.session_state:
        st.session_state.auth_status = "login"  # Default to login view
    
    # Tabs for Login/Register
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True, 
                    disabled=st.session_state.auth_status == "login"):
            st.session_state.auth_status = "login"
            st.rerun()
    
    with col2:
        if st.button("Register", use_container_width=True, 
                    disabled=st.session_state.auth_status == "register"):
            st.session_state.auth_status = "register"
            st.rerun()
    
    # Display login form
    if st.session_state.auth_status == "login":
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.success("Login successful!")
                        # Add a small delay before redirecting
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
    
    # Display registration form
    else:
        with st.form("register_form"):
            st.subheader("Create an Account")
            full_name = st.text_input("Full Name")
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            submit = st.form_submit_button("Register", use_container_width=True)
            
            if submit:
                if not (full_name and username and email and password):
                    st.warning("Please fill in all fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success = register_user(username, email, password, full_name)
                    if success:
                        st.success("Registration successful! Please login.")
                        st.session_state.auth_status = "login"
                        st.rerun()
                    else:
                        st.error("Username or email already exists")
    
    # Return authentication status
    return 'user' in st.session_state and st.session_state.user is not None