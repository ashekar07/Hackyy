"""
=============================================================================
FOOD WASTE MANAGEMENT SYSTEM - CONFIGURATION
=============================================================================
Loads environment variables from .env and defines kitchen operational settings.
All settings are kept simple and readable.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load .env file from current folder or parent folder
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ---------------------------------------------------------------------------
# 1. API & LLM Settings (Stored in .env)
# ---------------------------------------------------------------------------
# Users can store their API key as either API_KEY or FEATHERLESS_API_KEY
API_KEY = os.getenv("API_KEY") or os.getenv("FEATHERLESS_API_KEY", "")
FEATHERLESS_API_KEY = API_KEY  # For backwards compatibility

# Model name and base endpoint
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("FEATHERLESS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
FEATHERLESS_DEFAULT_MODEL = LLM_MODEL
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
FEATHERLESS_BASE_URL = LLM_BASE_URL

# ---------------------------------------------------------------------------
# 2. Web Server Settings
# ---------------------------------------------------------------------------
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# ---------------------------------------------------------------------------
# 3. Email Notifications
# ---------------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")
SMTP_FROM = os.getenv("SMTP_FROM") or SMTP_USERNAME

# ---------------------------------------------------------------------------
# 4. Kitchen Operating Thresholds & Constants
# ---------------------------------------------------------------------------
# Standard daily diner headcount capacity
BASELINE_CAMPUS_FOOTFALL = 750

# Environmental factors (EPA / FAO standards)
# 2.5 kg CO2 avoided per 1 kg of food saved
EMISSIONS_FACTOR_CO2_PER_KG = 2.5

# 13.2 liters of water conserved per 1 kg of food saved
WATER_CONSERVATION_L_PER_KG = 13.2

# Agent optimization rules
DEMAND_SAFETY_BUFFER = 0.08      # Demand Agent adds +8% buffer to prevent running out of food
HIGH_SCRAP_THRESHOLD_PCT = 15.0  # Waste Agent flags dishes with >15% plate waste
EXPIRY_URGENCY_HOURS = 24.0      # Inventory Agent alerts on food expiring in < 24 hours

# Staged cooking split (Cook in 2 batches to prevent overproduction)
SHIFT_1_RATIO = 0.65             # 65% prepped at 11:00 AM for early lunch
SHIFT_2_RATIO = 0.35             # 35% kept chilled until 1:15 PM rush is confirmed
