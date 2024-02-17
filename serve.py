import os
from dotenv import load_dotenv

load_dotenv()

langchain_key = os.getenv("LANGCHAIN_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")