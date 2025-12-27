from langchain_core.prompts import PromptTemplate


def get_sql_prompt_template(db_type: str) -> PromptTemplate:
    """Get SQL prompt template based on database type with SELECT-only constraints"""

    db_type = db_type.lower()

    if db_type == "mysql":
        dialect_info = "MySQL"
        specific_instructions = "- Use LIMIT for result limiting."
        example_snippet = """Question: Return the first row from the employees table  
                            SQL Query: SELECT * FROM employees LIMIT 1;

                            Question: Show all emails from the users table  
                            SQL Query: SELECT email FROM users;"""
    elif db_type == "postgresql":
        dialect_info = "PostgreSQL"
        specific_instructions = (
            "- **Always** wrap table and column names in double quotes ("
            ").\n"
            "- Use LIMIT for result limiting.\n"
            "- Use OFFSET for pagination."
        )
        example_snippet = """Question: Return the first row from the employees table  
                            SQL Query: SELECT * FROM "employees" LIMIT 1;

                            Question: Show all emails from the users table  
                            SQL Query: SELECT "email" FROM "users";"""
    elif db_type == "sqlite":
        dialect_info = "SQLite"
        specific_instructions = "- Use LIMIT and OFFSET for pagination."
        example_snippet = """Question: Return the first row from the employees table  
                            SQL Query: SELECT * FROM employees LIMIT 1;"""
    elif db_type == "oracle":
        dialect_info = "Oracle"
        specific_instructions = "- Use ROWNUM or FETCH FIRST for result limiting."
        example_snippet = """Question: Return the first row from the employees table  
                            SQL Query: SELECT * FROM employees WHERE ROWNUM = 1;"""
    elif db_type == "mssql":
        dialect_info = "SQL Server"
        specific_instructions = (
            "- Use TOP for result limiting.\n- Use OFFSET...FETCH for pagination."
        )
        example_snippet = """Question: Return the first row from the employees table  
                            SQL Query: SELECT TOP 1 * FROM employees;"""
    else:
        dialect_info = "SQL"
        specific_instructions = "- Follow standard SQL syntax."
        example_snippet = """Question: Return the first row from the employees table  
                        SQL Query: SELECT * FROM employees LIMIT 1;"""

    return PromptTemplate.from_template(
        f"""You are a {dialect_info} expert. 
Your task is to generate only a single **SELECT** query that answers the question.

Rules:
- Only output one SELECT statement, nothing else. 
- Do NOT generate CREATE, INSERT, UPDATE, DELETE, DROP, ALTER, or comments.
- Do NOT explain or restate the question.
- Use {dialect_info} syntax correctly.
- {specific_instructions}
- Use the schema below only to reference column and table names.

### Examples
{example_snippet}

---

Schema:
{{table_info}}

Question: {{input}}
SQL Query:"""
    )


def get_enhanced_sql_prompt_template(db_type: str) -> PromptTemplate:
    """Enhanced SQL prompt template with better join handling"""

    db_type = db_type.lower()

    if db_type == "mysql":
        dialect_info = "MySQL"
        specific_instructions = "- Use LIMIT only if query has top n, “first few”, “first n”, “only 1 row”, “just one record”, “only show the first”, “only the top”, “at most 5”, or “no more than 10”"
        example_snippet = """Question: Get employees and their department names
SQL Query: SELECT e.name, d.department_name FROM employees e INNER JOIN departments d ON e.department_id = d.id;
"""
    elif db_type == "postgresql":
        dialect_info = "PostgreSQL"
        specific_instructions = (
            "- **Always** wrap table and column names in double quotes.\n"
            "- Use LIMIT for result limiting.\n"
            "- Use OFFSET for pagination."
        )
        example_snippet = """Question: Get employees and their department names
SQL Query: SELECT "e"."name", "d"."department_name" FROM "employees" "e" INNER JOIN "departments" "d" ON "e"."department_id" = "d"."id";

Question: Return the first row from the employees table  
SQL Query: SELECT * FROM "employees" LIMIT 1;"""
    else:
        dialect_info = "SQL"
        specific_instructions = "- Follow standard SQL syntax."
        example_snippet = """Question: Return the first row from the employees table  
SQL Query: SELECT * FROM employees LIMIT 1;"""

    return PromptTemplate.from_template(
        f"""You are a {dialect_info} expert specializing in complex queries.
Your task is to generate only a single **SELECT** query that answers the question.

Rules:
- Only output one SELECT statement, nothing else.
- Do NOT generate CREATE, INSERT, UPDATE, DELETE, DROP, ALTER, or comments.
- Do NOT explain or restate the question.
- Use {dialect_info} syntax correctly.
- {specific_instructions}

**JOIN Guidelines:**
- Always use explicit JOIN syntax (INNER JOIN, LEFT JOIN, etc.)
- Always specify ON conditions for joins
- Use table aliases for clarity (e.g., employees e, departments d)
- Ensure foreign key relationships match the schema
- For multiple joins, verify each ON clause references correct columns

**Common Pitfalls to Avoid:**
- Missing ON clauses in JOIN statements
- Ambiguous column names (always use table prefix: e.name, not just name)
- Incorrect foreign key references
- Missing closing parentheses in subqueries

### Examples
{example_snippet}

---

Schema:
{{table_info}}

Question: {{input}}
SQL Query:"""
    )


answer_prompt = PromptTemplate.from_template(
    """You are given a user question, a SQL query, and the SQL result. 
Return *only* the final answer to the question as a short human-readable sentence, 
without any explanation, details, or restating the query.

Question: {question}
SQL Query: {query}
SQL Result: {result}
Answer:"""
)


question_rephrase = PromptTemplate.from_template(
    """
You are an expert at understanding natural language and rewriting questions
to make them easier for a database query model (Text-to-SQL) to understand.

Your task:
- Rephrase the given question into a clear, unambiguous, and SQL-friendly form.
- Keep all the original intent and information.
- Remove vague or conversational language.
- Use explicit references to columns, tables, or filters when possible.
- Do NOT add new information that wasn’t in the question.
                                                 
Schema:
{{table_info}}
    

### Examples

User Question: "Who joined recently?"
Rephrased Question: "Show all employees who joined within the last 30 days."

User Question: "Get me all people earning more than average salary."
Rephrased Question: "Show all employees whose salary is greater than the average salary."

User Question: "What’s the total revenue?"
Rephrased Question: "Show the total revenue from the sales table."

User Question: "Which products sold the most?"
Rephrased Question: "Show products from the sales table ordered by total quantity sold in descending order."

---

Original Question: {input}
Rephrased Question:
"""
)

correction_prompt = PromptTemplate.from_template(
    """The following SQL query has a syntax error:

        Query: {query}
        Error: {error}

        Database Type: {db_type}
        Schema:
        {table_info}

        Generate a corrected SQL query that fixes this error.
        Rules:
        - Output ONLY the corrected SELECT statement
        - Do NOT explain the fix
        - Pay special attention to JOIN clauses and column references

        Corrected SQL Query:"""
)
