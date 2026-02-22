"""
Module: config.py
Purpose: Central configuration management for the Investment Agent.
         Loads environment variables and defines system-wide constants 
         like THESIS_CONSTRAINTS for the RAG system.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    @classmethod
    def validate(cls):
        """Validates that necessary environment variables are set."""
        missing = []
        if not cls.ALPACA_API_KEY:
            missing.append("ALPACA_API_KEY")
        if not cls.ALPACA_SECRET_KEY:
            missing.append("ALPACA_SECRET_KEY")
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.SMTP_EMAIL:
            missing.append("SMTP_EMAIL")
        if not cls.SMTP_PASSWORD:
            missing.append("SMTP_PASSWORD")
            
        if missing:
            print(f"Warning: The following environment variables are missing: {', '.join(missing)}")
            print("Please create a .env file based on .env.example")
            return False
        return True

    # RAG: Thesis Constraints
    # If the score (0-10) is >= threshold, we FORCE HOLD these assets.
    # RAG: Thesis Constraints
    # If the score (0-10) is >= threshold, we FORCE HOLD these assets.
    THESIS_CONSTRAINTS = {
        # Geopolitical Hedges (War/Conflict)
        'LMT': {'risk_type': 'conflict_score', 'threshold': 6, 'role': 'Geopolitical Hedge'},
        'BA':  {'risk_type': 'conflict_score', 'threshold': 6, 'role': 'Defense/Aerospace'},
        'GE':  {'risk_type': 'conflict_score', 'threshold': 6, 'role': 'Industrial/Defense'},
        'RTX': {'risk_type': 'conflict_score', 'threshold': 6, 'role': 'Defense'},

        # Inflation Hedges (Energy/Real Assets)
        'XOM': {'risk_type': 'inflation_score', 'threshold': 6, 'role': 'Inflation Hedge (Energy)'},
        'CVX': {'risk_type': 'inflation_score', 'threshold': 6, 'role': 'Inflation Hedge (Energy)'},
        'CAT': {'risk_type': 'inflation_score', 'threshold': 6, 'role': 'Real Assets (Infra)'},
        'DE':  {'risk_type': 'inflation_score', 'threshold': 6, 'role': 'Real Assets (Ag)'},
        
        # Economic Instability Hedges (Recession/Defensive)
        'KO':   {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Consumer Defensive'},
        'PEP':  {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Consumer Defensive'},
        'PG':   {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Consumer Defensive'},
        'WMT':  {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Consumer Staples'},
        'COST': {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Consumer Staples'},
        'MCD':  {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Recession Resistant'},
        'JNJ':  {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Healthcare Defensive'},
        'PFE':  {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Healthcare Defensive'},
        'ABBV': {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Healthcare Yield'},
        'UNH':  {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Healthcare Defensive'},
        
        # New Additions
        'BRK.B': {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Diversified Defensive'},
        'CL':    {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Consumer Staples'},
        'HON':   {'risk_type': 'conflict_score', 'threshold': 6, 'role': 'Aerospace Defense'},
        'MDT':   {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Medical Equipment'},
        'BMY':   {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Pharma Defensive'},
        'DUK':   {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Regulated Utility'},
        'AEP':   {'risk_type': 'economic_instability_score', 'threshold': 6, 'role': 'Electric Grid'},
        'LIN':   {'risk_type': 'inflation_score', 'threshold': 6, 'role': 'Industrial Materials'},
    }
