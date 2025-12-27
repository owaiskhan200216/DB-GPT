from tabulate import tabulate
from sqlalchemy import text
from langchain_core.runnables import RunnableLambda
from utils import to_text
from utils import extract_sql, normalize_sql_quotes
from prompts import correction_prompt
from utils import call_model, sqlglot_validate



def validate_and_execute_query(query: str, db, db_type: str, max_retries: int = 2):
    """
    Validates and executes SQL query with automatic sqlglot-based error detection
    and LLM-powered correction.
    Returns: (success: bool, result: str, final_query: str, error_log: list)
    """

    error_log = []
    current_query = query  # after regex extraction

    for attempt in range(max_retries + 1):

        is_valid, validation_error = sqlglot_validate(current_query, db.table_info)

        if not is_valid:
            error_msg = validation_error

            error_log.append(
                {
                    "attempt": attempt + 1,
                    "query": current_query,
                    "error": error_msg,
                    "source": "sqlglot",
                }
            )

            if attempt >= max_retries:
                return False, error_msg, current_query, error_log

            try:

                inputs = {
                    "query": current_query,
                    "error": error_msg,
                    "db_type": db_type,
                    "table_info": db.table_info,
                }

                correction_prompt = correction_prompt.format(**inputs)

                corrected_output = call_model(correction_prompt)

                corrected_output = to_text(corrected_output)

                current_query = extract_sql(corrected_output)

                current_query = normalize_sql_quotes(current_query)

                continue

            except Exception as correction_error:
                error_log.append(
                    {"attempt": attempt + 1, "correction_error": str(correction_error)}
                )
                return (
                    False,
                    f"Correction failed: {correction_error}",
                    current_query,
                    error_log,
                )

        try:
            with db._engine.connect() as conn:
                result_proxy = conn.execute(text(current_query))
                rows = result_proxy.fetchall()
                columns = result_proxy.keys()

            result = tabulate(rows, headers=columns, tablefmt="pretty")

            return True, result, current_query, error_log

        except Exception as e:
            error_msg = str(e)

            error_log.append(
                {
                    "attempt": attempt + 1,
                    "query": current_query,
                    "error": error_msg,
                    "source": "db_error",
                }
            )

            if attempt >= max_retries:
                return False, error_msg, current_query, error_log

            try:

                inputs = {
                    "query": current_query,
                    "error": error_msg,
                    "db_type": db_type,
                    "table_info": db.table_info,
                }

                correction_prompt = correction_prompt.format(**inputs)

                corrected_output = call_model(correction_prompt)

                corrected_output = to_text(corrected_output)

                current_query = extract_sql(corrected_output)

                current_query = normalize_sql_quotes(current_query)

            except Exception as correction_error:
                error_log.append(
                    {"attempt": attempt + 1, "correction_error": str(correction_error)}
                )
                return (
                    False,
                    f"Correction failed: {correction_error}",
                    current_query,
                    error_log,
                )

    return False, "Max retries exceeded", current_query, error_log
