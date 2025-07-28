import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024 # 100 mb