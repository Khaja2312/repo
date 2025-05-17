# config.py
import os

# SambaNova API Configuration
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "c98caae8-3cbf-4a77-ba70-b2a8f27ea0c7")
SAMBANOVA_API_URL = "https://api.sambanova.ai/v1/completions"
SAMBANOVA_MODEL_NAME = "sambanova-llm"  # Replace with correct model

# Try these model names if the primary one fails
ALTERNATIVE_MODELS = [
    "sambanova-chat",
    "sambanova-1.5-chat",
    "llama-7b",
    "llama2-7b"
]

# MySQL Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
DB_NAME = os.getenv("DB_NAME", "skill_assessment")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

# Media Storage Configuration
UPLOAD_FOLDER = "uploads"
IMAGE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "images")
AUDIO_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "audio")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size

# Create directories if they don't exist
for folder in [UPLOAD_FOLDER, IMAGE_UPLOAD_FOLDER, AUDIO_UPLOAD_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Fallback Configuration (when API fails)
USE_FALLBACK = True  # Set to True to enable fallback when API fails

# Skills and Levels Configuration
AVAILABLE_SKILLS = [
    "Communication", "Leadership", "Critical Thinking", 
    "Problem Solving", "Teamwork", "Time Management",
    "Adaptability", "Emotional Intelligence", "Creativity",
    "Decision Making", "Conflict Resolution", "Negotiation"
]

AVAILABLE_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# Question Types
QUESTION_TYPES = ["Text", "Audio", "Image"]