import streamlit as st

# Check and install required packages
import subprocess
import sys

def install_packages():
    st.write("Installing required packages...")
    packages = [
        "pandas", "numpy", "scikit-learn", "nltk", "plotly", "altair"
    ]
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            st.write(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            st.write(f"{package} installed successfully.")
    st.write("All packages installed.")

install_packages()