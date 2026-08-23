import os
from dotenv import load_dotenv
load_dotenv()
OPENAI_MODEL = os.getenv('OPENAI_MODEL','gpt-4o-mini')
DATA_FOLDER = os.path.join(os.path.dirname(__file__),'AI Agent Assessment - Candidate Pack')
ALLOWED_ROLE = os.getenv('PARCELPILOT_ALLOWED_ROLE','support')
