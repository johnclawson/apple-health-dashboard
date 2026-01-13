"""Configuration settings for Apple Health Dashboard."""

import os
from pathlib import Path
from datetime import datetime

# Project directories
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
SRC_DIR = PROJECT_ROOT / "src"

# Apple Health export settings
EXPORT_ZIP_PATH = Path.home() / "SynologyDrive" / "health records" / "John apple health export 1-11-26.zip"
EXPORT_XML_NAME = "export.xml"
WORKOUT_ROUTES_DIR = "workout-routes"

# Workout filtering
WORKOUT_TYPES = [
    "HKWorkoutActivityTypeCycling"
]

# Date range filtering (None = no filter)
START_DATE = None  # datetime(2020, 1, 1)
END_DATE = None    # datetime(2025, 12, 31)

# Heart Rate Zones (based on percentage of max HR)
# Default max HR = 220 - age, or can be set manually
MAX_HEART_RATE = 185  # Adjust based on your actual max HR

HR_ZONES = {
    "Zone 1 (Recovery)": (0, 0.60),      # <60% max HR
    "Zone 2 (Endurance)": (0.60, 0.70),  # 60-70%
    "Zone 3 (Aerobic)": (0.70, 0.80),    # 70-80%
    "Zone 4 (Threshold)": (0.80, 0.90),  # 80-90%
    "Zone 5 (Maximum)": (0.90, 1.00),    # 90-100%
}

# Output settings
OUTPUT_FILENAME_TEMPLATE = "apple_health_cycling_report_{date}.xlsx"

# Excel styling
EXCEL_THEME_COLORS = {
    "primary": "4472C4",    # Blue
    "secondary": "70AD47",  # Green
    "accent": "FFC000",     # Orange
    "header_bg": "305496",  # Dark blue
    "header_text": "FFFFFF" # White
}

# Unit preferences
DISTANCE_UNIT = "miles"  # "km" or "miles"
ELEVATION_UNIT = "ft"  # "m" or "ft"

def get_output_filename():
    """Generate output filename with current date."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return OUTPUT_FILENAME_TEMPLATE.format(date=date_str)

def ensure_directories():
    """Create necessary directories if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
