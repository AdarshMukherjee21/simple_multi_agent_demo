import os
import glob
import logging
import streamlit as st
from langchain_core.messages import HumanMessage
from graph import workflow

logger = logging.getLogger("StreamlitApp")

st.set_page_config(page_title="Multi-Agent System Dashboard", layout="wide")
st.title("Orchestrator-Worker Multi-Agent System")

# Session State Initialization
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "session_thread_1"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = []

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# Layout: Left (Chat & Query History) | Right (Live Agent Execution Trace)
left_col, right_col = st.columns([1.2, 1])

def run_graph_stream(inputs, log_container):
    """Executes graph streaming safely and appends logs to session state."""
    for output in workflow.stream(inputs, config=config, stream_mode="updates"):
        for node_name, state_update in output.items():
            log_entry = {"node": node_name, "details": []}
            
            if "messages" in state_update:
                for msg in state_update["messages"]:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool in msg.tool_calls:
                            log_entry["details"].append(
                                f"**[TOOL CALL]** `{tool['name']}` | Arguments: `{tool['args']}`"
                            )
                    elif hasattr(msg, 'content') and msg.content:
                        log_entry["details"].append(f"**[CONTENT]** {msg.content}")
                        
                        # Push Supervisor conversation to the main Chat pane
                        if node_name == "Supervisor" and state_update.get("next") == "FINISH":
                            st.session_state.chat_history.append({"role": "assistant", "content": msg.content})
                            with left_col:
                                with chat_container:
                                    with st.chat_message("assistant"):
                                        st.markdown(msg.content)

            st.session_state.agent_logs.append(log_entry)
            
            # Live updates to right pane container
            with log_container:
                with st.expander(f"[EXECUTION STEP] Node: {node_name}", expanded=True):
                    for detail in log_entry["details"]:
                        st.markdown(detail)

# --- Left Column: Chat Pane ---
with left_col:
    st.subheader("Conversation History")
    
    # Scrollable container for chat messages
    chat_container = st.container(height=650)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

# Chat input is naturally anchored at the bottom of the page
user_input = st.chat_input("Enter your task request...")

# --- Right Column: Live Telemetry Pane ---
with right_col:
    st.subheader("Live Agent Telemetry")
    
    # Scrollable container for logs to match chat height
    log_container = st.container(height=650)

    # Render previous logs for the current session
    for log in st.session_state.agent_logs:
        with log_container:
            with st.expander(f"[EXECUTION STEP] Node: {log['node']}", expanded=False):
                for detail in log["details"]:
                    st.markdown(detail)

# --- Handle New User Input ---
if user_input:
    # 1. Update UI Chat Immediately
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.session_state.agent_logs = []  # Reset log display for new task
    
    with left_col:
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

    # 2. Run Workflow safely
    logger.info(f"Starting workflow execution for prompt: {user_input}")
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    run_graph_stream(initial_state, log_container)
    
    st.rerun()

# --- Handle Human-In-The-Loop Approval ---
current_state = workflow.get_state(config)
if current_state.next and current_state.next[0] == "Emailer":
    with right_col:
        st.warning("[INTERRUPT] Approval required before Emailer Agent executes.")
        
        draft_files = glob.glob("drafts/*.txt")
        if draft_files:
            latest_draft_path = max(draft_files, key=os.path.getctime)
            # Make sure to read with utf-8 to prevent Windows decoding errors
            with open(latest_draft_path, "r", encoding="utf-8") as f:
                draft_content = f.read()
            st.code(draft_content, language="text")

        btn_approve, btn_reject = st.columns(2)
        with btn_approve:
            if st.button("[APPROVE] Send Email", use_container_width=True):
                logger.info("User approved email sending. Resuming graph...")
                run_graph_stream(None, log_container)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "Task completed. Email dispatched."
                })
                st.rerun()
                
        with btn_reject:
            if st.button("[REJECT] Cancel Task", use_container_width=True):
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "Execution cancelled before email dispatch."
                })
                st.rerun()