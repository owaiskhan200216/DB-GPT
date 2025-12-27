import re
from langchain.messages import AIMessage
import subprocess
import time
from langsmith import traceable
import requests
import sqlglot
from sqlglot import exp


OLLAMA_EXE = r"C:\Users\hasan\AppData\Local\Programs\Ollama\ollama app.exe"
OLLAMA_URL = "http://127.0.0.1:11434"
_port = 8001


def normalize_sql_quotes(query: str) -> str:
    """Fix escaped quotes from LLM output"""

    print("\n\n\n\n\n\n\n\n\n", query.replace('\\"', '"').strip(), "\n\n\n\n\n\n\n\n\n")
    return query.replace('\\"', '"').strip()


@traceable(name="extract_sql")
def extract_sql(text: str) -> str:
    """Extract only SELECT statements from model output"""
    # Match the first SELECT ... ; (non-greedy)
    m = re.search(r"(?is)\bSELECT\b.*?;", text)
    if m:
        print(
            "\n\n\n\n\n\n\n\n\n\n\n\n This is the extracted SQL:",
            m.group(0).strip(),
            "\n\n\n\n\n\n\n\n\n\n\n\n",
        )
        return m.group(0).strip()

    # Fallback: SELECT without semicolon
    m2 = re.search(r"(?is)\bSELECT\b.*", text)
    if m2:
        print(
            "\n\n\n\n\n\n\n\n\n\n\n\n This is the extracted SQL:",
            m2.group(0).strip(),
            "\n\n\n\n\n\n\n\n\n\n\n\n",
        )
        return m2.group(0).strip()

    # If no SELECT found, return empty or raise error
    return ""


def extract_thinking_and_answer(response: str):
    """
    Extracts the reasoning (thinking) part and the clean final answer
    from a model-generated text-to-SQL response.

    Everything after any variant of <...think> is considered thinking text.
    Everything before is the clean answer.

    Args:
        response (str): The full answer text (possibly containing <think>, </think>, etc.).

    Returns:
        tuple[str, str]: (thinking_text, clean_answer)
    """
    # Find the position of anything followed by 'think>' tag (case insensitive)
    # This will match <think>, </think>, <anythink>, etc.
    think_match = re.search(r"<[^>]*think>", response, re.IGNORECASE)

    if think_match:
        # Everything before the think tag is the clean answer
        clean_answer = response[: think_match.start()].strip()
        # Everything after the think tag is thinking text
        thinking_text = response[think_match.end() :].strip()
    else:
        # No think tag found
        thinking_text = "..."
        clean_answer = response.strip()

    return thinking_text, clean_answer


def to_text(msg):

    if isinstance(msg, AIMessage):
        return msg.content

    elif isinstance(msg, dict) and "content" in msg:
        return msg["content"]

    else:
        return str(msg)


# @traceable(name="extract_sql")
def call_model(prompt: str, max_tokens: int = 1024):
    url = "http://127.0.0.1:8001/generate"
    resp = requests.post(url, json={"prompt": prompt, "max_tokens": max_tokens})
    resp.raise_for_status()
    return resp.json()["text"]


def is_ollama_running():
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=1)
        return True
    except:
        return False


def start_ollama():
    if is_ollama_running():
        return

    subprocess.Popen(
        f'"{OLLAMA_EXE}"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(15):
        if is_ollama_running():
            return
        time.sleep(1)

    raise RuntimeError("Ollama failed to start")


def stop_ollama():
    # Kill the tray / app
    subprocess.run(
        'taskkill /F /IM "ollama app.exe"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Kill the server & runners
    subprocess.run(
        "taskkill /F /IM ollama.exe",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def sqlglot_validate(query, schema):
    """
    schema = db.table_info  → {table: [columns]}
    Returns (is_valid, error_message)
    """
    try:
        parsed = sqlglot.parse_one(query)
    except Exception as e:
        return False, f"SQL Syntax Error: {str(e)}"

    # TABLE VALIDATION
    # available_tables = set(schema.keys())
    # referenced_tables = [t.name for t in parsed.find_all(exp.Table)]

    # for t in referenced_tables:
    #     if t not in available_tables:
    #         return False, f"Unknown table '{t}'"

    # COLUMN VALIDATION
    # for col in parsed.find_all(exp.Column):
    #     table = col.table
    #     colname = col.name

    #     if table in schema:
    #         if colname not in schema[table]:
    #             return False, f"Unknown column '{colname}' in table '{table}'"
    #     # if unqualified column → skip (optional)

    # DETECT CROSS JOIN
    # for join in parsed.find_all(exp.Join):
    #     if join.args.get("kind") == "cross":
    #         return False, "Unsafe CROSS JOIN detected (refusing to execute)"
    #     if not join.args.get("on"):
    #         return False, "JOIN missing ON clause (implicit CROSS JOIN)"

    return True, None

def is_model_server_running():
    try:
        r = requests.get(f"http://127.0.0.1:{_port}/docs", timeout=0.3)
        return r.status_code == 200
    except:
        return False