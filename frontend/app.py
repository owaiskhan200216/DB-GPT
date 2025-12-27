import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
import base64
from pathlib import Path
import mimetypes


def image_to_base64(path):
    """Convert image to base64 with automatic mime type detection"""
    img_bytes = Path(path).read_bytes()

    # Get mime type from file extension
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type is None:
        # Fallback to jpeg if can't determine
        mime_type = "image/jpeg"

    base64_str = base64.b64encode(img_bytes).decode()
    return base64_str, mime_type


# Configure page
st.set_page_config(
    page_title="Text-to-SQL Assistant",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API Base URL
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "table_info" not in st.session_state:
    st.session_state.table_info = None


st.markdown(
    """
<style>
    /* General */
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }

    .model-badge {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    margin-left: 6px;
    font-weight: 600;
    display: inline-block;
    }

    .badge-openai {
        background-color: rgba(16,163,127,0.2);
        color: #10a37f;
    }

    .badge-mistral {
        background-color: rgba(255,76,76,0.2);
        color: #ff4c4c;
    }

    .badge-local {
        background-color: rgba(63,81,181,0.2);
        color: #3f51b5;
    }

    /* Chat messages */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }

    .user-message {
        background-color: rgba(33, 150, 243, 0.1);
        border-left-color: #2196F3;
        color: inherit;
    }

    .assistant-message {
        background-color: rgba(76, 175, 80, 0.1);
        border-left-color: #4CAF50;
        color: inherit;
    }

    /* SQL code block */
    .sql-code {
        background-color: #1e1e1e;
        color: #00d9ff;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        margin: 0.5rem 0;
    }

    /* Metric cards and other blocks */
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid rgba(255,255,255,0.1);
    }

    /* Adjust text color for dark theme */
    [data-testid="stSidebar"], .stMarkdown, .stTextInput label, .stSelectbox label {
        color: inherit !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Sidebar - Database Connection
with st.sidebar:
    st.title("🗄️ Database Connection")

    model_type = st.selectbox(
        "Model Type",
        options=["Local Text2SQL", "OpenAi", "Mistral"],
        index=1,
    )

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.divider()

    # Database configuration
    db_type = st.selectbox(
        "Database Type",
        options=["postgresql", "mysql", "sqlite", "oracle", "mssql"],
        index=1,
    )

    if db_type == "sqlite":
        db_name = st.text_input("Database File Path", value="example.db")
        db_user = "root"
        db_password = ""
        db_host = "localhost"
        db_port = None
    else:
        col1, col2 = st.columns(2)
        with col1:
            db_host = st.text_input("Host", value="localhost")
        with col2:
            default_ports = {
                "postgresql": 5432,
                "mysql": 3306,
                "oracle": 1521,
                "mssql": 1433,
            }
            db_port = st.number_input(
                "Port",
                value=default_ports.get(db_type, 5432),
                min_value=1,
                max_value=65535,
            )

        db_name = st.text_input("Database Name", value="text2sql_test")
        db_user = st.text_input("Username", value="root")
        db_password = st.text_input("Password", type="password", value="")

    # Table names
    table_names_input = st.text_area(
        "Table Names (one per line)",
        value="courses\nenrollments\nstudents",
        help="Enter the names of tables you want to query",
    )
    table_names = [t.strip() for t in table_names_input.split("\n") if t.strip()]

    st.divider()

    # Connect/Disconnect button
    if not st.session_state.connected:
        if st.button(
            "🔌 Connect to Database", type="primary", use_container_width=True
        ):
            if not db_name or (db_type != "sqlite" and not db_user):
                st.error("Please fill in all required fields")
            elif not table_names:
                st.error("Please specify at least one table name")
            else:
                with st.spinner("Connecting to database..."):
                    try:
                        config = {
                            "db_type": db_type,
                            "db_user": db_user,
                            "db_password": db_password,
                            "db_host": db_host,
                            "db_port": db_port,
                            "db_name": db_name,
                            "table_names": table_names,
                        }

                        response = requests.post(
                            f"{API_BASE_URL}/connect-database", json=config
                        )

                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.session_id = data["session_id"]
                            st.session_state.connected = True
                            st.session_state.table_info = data.get("table_info")
                            st.session_state.chat_history = []
                            st.success("✅ Connected successfully!")
                            st.rerun()
                        else:
                            st.error(
                                f"Connection failed: {response.json().get('detail', 'Unknown error')}"
                            )
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    else:
        st.success(f"✅ Connected")
        st.info(f"Session: `{st.session_state.session_id[:16]}...`")

        if st.button("🔌 Disconnect", type="secondary", use_container_width=True):
            try:
                requests.delete(f"{API_BASE_URL}/session/{st.session_state.session_id}")
            except:
                pass
            st.session_state.session_id = None
            st.session_state.connected = False
            st.session_state.chat_history = []
            st.session_state.table_info = None
            st.rerun()

    # Show table info if connected
    if st.session_state.connected and st.session_state.table_info:
        with st.expander("📊 Database Schema", expanded=False):
            st.code(st.session_state.table_info, language="sql")

# # Main content area
# st.title("💬 Text-to-SQL Assistant")
# st.markdown("Ask questions about your database in natural language")

if not st.session_state.connected:
    st.info("👈 Please connect to a database using the sidebar to get started")

    # # Show example queries
    # st.subheader("Example Queries")
    # col1, col2 = st.columns(2)

    # with col1:
    #     st.markdown(
    #         """
    #     **Simple Queries:**
    #     - Show all employees
    #     - What is the total revenue?
    #     - List all products
    #     - Get the first 10 orders
    #     """
    #     )

    # with col2:
    #     st.markdown(
    #         """
    #     **Complex Queries:**
    #     - Which employees earn more than average?
    #     - Show top 5 selling products
    #     - Get employees and their departments
    #     - What's the revenue by month?
    #     """
    #     )
else:
    # Chat interface
    chat_container = st.container()
    if len(st.session_state.chat_history) == 0:
        img_base64, mime_type = image_to_base64("assets/4.jpeg")

        st.markdown(
            f"""
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin-top: 80px;
            ">
                <div style="
                    width: 220px;
                    height: 220px;
                    border-radius: 50%;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                ">
                    <img src="data:{mime_type};base64,{img_base64}"
                        style="
                            width: 100%;
                            height: 100%;
                            object-fit: cover;
                        ">
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with chat_container:
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(
                    f"""
                <div class="chat-message user-message">
                    <strong>You:</strong> {message['content']}
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                model_used = message.get("model_type", "Unknown")

                MODEL_COLOR = {
                    "OpenAi": "#ff9800",  # orange
                    "Mistral": "#ff4c4c",  # red
                    "Local_Text2SQL": "#3f51b5",  # indigo
                }

                color = MODEL_COLOR.get(model_used, "#ff9800")  # fallback orange

                st.markdown(
                    f"""
                    <div class="chat-message assistant-message">
                        <strong>
                            Assistant:
                            <span style="color:{color};">
                                {model_used}
                            </span>
                        </strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Show SQL query
                if message.get("sql"):
                    with st.expander("🔍 Generated SQL Query", expanded=False):
                        st.code(message["sql"], language="sql")

                # Show rephrased question if available
                if message.get("rephrased"):
                    with st.expander("💭 Rephrased Question", expanded=False):
                        st.info(message["rephrased"])

                # Show result
                if message.get("result"):
                    result = message["result"]

                    # Try to parse as JSON dataframe
                    try:
                        result_dict = json.loads(result)
                        if (
                            isinstance(result_dict, dict)
                            and result_dict.get("type") == "dataframe"
                        ):
                            df = pd.DataFrame(result_dict["data"])
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.markdown(result, unsafe_allow_html=True)
                    except (json.JSONDecodeError, ValueError):
                        # Check if it's HTML
                        if "<table" in result.lower():
                            st.markdown(result, unsafe_allow_html=True)
                        else:
                            st.code(result, language="text")

                # Show status
                if message.get("status"):
                    if message["status"] == "success":
                        st.success("✅ Query executed successfully")
                    elif message["status"] == "success_after_correction":
                        st.warning("⚠️ Query executed after automatic correction")

    # Query input
    # st.divider()

    # col1, col2 = st.columns([6, 1])

    # with col1:
    #     user_question = st.text_input(
    #         "Ask a question about your data:",
    #         placeholder="e.g., Show me all employees who joined in 2024",
    #         key="question_input",
    #         label_visibility="collapsed",
    #     )

    # with col2:
    #     ask_button = st.button("Ask", type="primary", use_container_width=True)

    # # Quick action buttons
    # col1, col2, col3, col4 = st.columns(4)
    # with col1:
    #     if st.button("📋 Show all data", use_container_width=True):
    #         user_question = (
    #             f"Show all data from {table_names[0] if table_names else 'table'}"
    #         )
    #         ask_button = True
    # with col2:
    #     if st.button("📊 Count rows", use_container_width=True):
    #         user_question = (
    #             f"Count total rows in {table_names[0] if table_names else 'table'}"
    #         )
    #         ask_button = True
    # with col3:
    #     if st.button("🔍 Describe schema", use_container_width=True):
    #         user_question = "Describe the table schema"
    #         ask_button = True
    # with col4:
    #     if st.button("🗑️ Clear chat", use_container_width=True):
    #         st.session_state.chat_history = []
    #         st.rerun()

    user_question = st.chat_input("Ask me anything about your database...")

    # Process question
    if user_question:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_question})

        # Call API
        with st.spinner("🤔 Thinking..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/ask-question",
                    json={
                        "session_id": st.session_state.session_id,
                        "question": user_question,
                        "used_model": {"model_type": model_type},
                    },
                    timeout=1000,
                )

                if response.status_code == 200:
                    data = response.json()

                    # Add assistant response to history
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "sql": data.get("generated_sql"),
                            "rephrased": data.get("question_rephrased"),
                            "result": data.get("clean_text", data.get("answer")),
                            "status": data.get("status"),
                            "model_type": data.get("used_model", {}).get(
                                "model_type", "Unknown"
                            ),
                        }
                    )

                    st.rerun()
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    st.error(f"❌ Error: {error_detail}")
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The query might be too complex.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Footer
# st.divider()
# st.markdown(
#     """
# <div style="text-align: center; color: #666; font-size: 0.9em;">
#     Text-to-SQL Assistant | Powered by FastAPI & Streamlit
# </div>
# """,
#     unsafe_allow_html=True,
# )
