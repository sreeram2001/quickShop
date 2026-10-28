# The model/brain of the whole agent.
import os

from dotenv import load_dotenv
from strands.models.openai import OpenAIModel

load_dotenv()

ASU_BASE_URL = "https://openai.rc.asu.edu/v1"
MODEL_ID = "gpt-oss-120b"

def build_model():
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY is not set. Copy .env.example to .env and add your ASU key.")
    return OpenAIModel(
        client_args={"base_url": ASU_BASE_URL, "api_key": api_key},
        model_id=MODEL_ID,
        params={"temperature": 0},
    )
