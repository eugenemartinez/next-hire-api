import random
import string
from sqlalchemy.orm import Session
import models # Assuming models.py is in the same directory (server)
from core.config import settings # Import settings

# --- Constants for generation ---
MODIFICATION_CODE_LENGTH = 8

def _generate_random_string(length: int, characters: str = string.ascii_letters + string.digits) -> str:
    """Helper function to generate a random string of a given length."""
    return ''.join(random.choice(characters) for _ in range(length))

def generate_modification_code(db: Session) -> str:
    """
    Generates a unique 8-character alphanumeric modification code.
    Ensures uniqueness by checking against the database.
    """
    # Using uppercase letters and digits for better readability if displayed
    # and to reduce ambiguity (e.g., O vs 0, I vs l)
    characters = string.ascii_uppercase + string.digits
    while True:
        code = _generate_random_string(MODIFICATION_CODE_LENGTH, characters)
        # Check if this code already exists in the database
        existing_job = db.query(models.Job).filter(models.Job.modification_code == code).first()
        if not existing_job:
            return code

def generate_unique_poster_username(db: Session) -> str:
    """
    Generates a unique poster username by combining a random adjective and noun
    from predefined lists in settings (e.g., "Strategic Innovator").
    Ensures uniqueness by checking against the database.
    """
    while True:
        adjective = random.choice(settings.DEFAULT_POSTER_ADJECTIVES)
        noun = random.choice(settings.DEFAULT_POSTER_NOUNS)
        username = f"{adjective} {noun}" # Combine with a space, or adjust as preferred

        # Check if this username already exists in the database
        existing_job = db.query(models.Job).filter(models.Job.poster_username == username).first()
        if not existing_job:
            return username

# Example of how you might generate a slug (not currently used but common utility)
# def generate_slug(text: str) -> str:
#     import re
#     text = text.lower()
#     text = re.sub(r'\s+', '-', text)  # Replace spaces with hyphens
#     text = re.sub(r'[^a-z0-9-]', '', text)  # Remove non-alphanumeric characters except hyphens
#     return text
