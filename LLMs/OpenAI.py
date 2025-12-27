from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import logging


load_dotenv()

# Initialize models at startup


def load_OpenAI_model():
    # Text-to-SQL model
    llm1 = ChatOpenAI(
        model="gpt-4o-mini",  # or "gpt-4o" for stronger reasoning
        temperature=0,
        max_tokens=3000,
    )

    llm2 = ChatOpenAI(
        model="gpt-4o-mini",  # or "gpt-4o" for stronger reasoning
        temperature=0,
        max_tokens=3000,
    )

    return llm1, llm2
