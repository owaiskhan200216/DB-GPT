from langchain_community.llms import LlamaCpp
from dotenv import load_dotenv
import logging
import os


def load_local_models():

    # Update these paths according to your setup
    model_path = os.getenv("MODEL_PATH")
    dst_path = os.getenv("DST_PATH")

    llm1 = LlamaCpp(
        model_path=model_path,
        n_threads=10,
        n_ctx=8016,
        temperature=0,
        max_tokens=1024,
    )

    llm2 = LlamaCpp(
        model_path=dst_path, n_threads=6, n_ctx=4096, temperature=0, max_tokens=3000
    )

    return llm1, llm2
