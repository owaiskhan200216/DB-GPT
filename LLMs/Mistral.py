from langchain_community.chat_models import ChatOllama


def load_mistral_models():
    llm1 = ChatOllama(
        model="mistral:7b-instruct",
        base_url="http://127.0.0.1:11434",
        temperature=0,
        num_ctx=8192,  # adjust if needed
    )
    

    llm2 = ChatOllama(
        model="mistral:7b-instruct",
        base_url="http://127.0.0.1:11434",
        temperature=0,
        num_ctx=4096,
    )


    return llm1, llm2
