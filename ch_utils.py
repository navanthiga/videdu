# challenge_utils.py
import streamlit as st
import json
from db_utils import log_activity

def complete_daily_challenge(user_id, challenge_data):
    """Mark a daily challenge as completed and award XP"""
    try:
        # Get XP reward from the challenge
        xp_reward = challenge_data["xp_reward"]
        
        # Log the activity
        log_activity(
            user_id, 
            "daily_challenge_completed", 
            {
                "challenge": challenge_data["challenge"],
                "topic": challenge_data["topic"],
                "xp_reward": xp_reward
            }
        )
        
        # Return success with the XP amount
        return {
            "success": True,
            "xp_awarded": xp_reward,
            "message": f"Challenge completed! You earned {xp_reward} XP!"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error completing challenge: {str(e)}"
        }