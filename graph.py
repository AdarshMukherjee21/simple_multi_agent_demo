import json
import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, AIMessage

from state import AgentState
from config import get_llm
from agents import ResearcherAgent, WriterAgent, EmailerAgent
import re
# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MultiAgentOrchestrator")

supervisor_llm = get_llm(role="supervisor")

SUPERVISOR_PROMPT = """You are the Supervisor Orchestrator. Coordinate specialist workers to fulfill user tasks.

Workers:
1. "Researcher": Searches knowledge base and retrieves policy information.
2. "Writer": Summarizes research, finds contact emails, and drafts emails.
3. "Emailer": Sends the drafted emails to the recipient.

Determine the next worker based on the conversation history. 
Respond ONLY in valid JSON format:
{"next": "WorkerName_or_FINISH", "reply": "Conversational response if finishing, else empty"}"""

def supervisor_node(state: AgentState):
    logger.info("--- ENTERING SUPERVISOR NODE ---")
    last_msg = state["messages"][-1] if state["messages"] else None

    # Deterministic Guardrails
    if last_msg and getattr(last_msg, "name", "") == "Researcher" and not getattr(last_msg, "tool_calls", None):
        logger.info("Guardrail triggered: Researcher finished -> Routing to Writer")
        return {"next": "Writer"}
    if last_msg and getattr(last_msg, "name", "") == "Writer" and not getattr(last_msg, "tool_calls", None):
        logger.info("Guardrail triggered: Writer finished -> Routing to Emailer")
        return {"next": "Emailer"}
    if last_msg and getattr(last_msg, "name", "") == "Emailer" and not getattr(last_msg, "tool_calls", None):
        logger.info("Guardrail triggered: Emailer finished -> Finishing execution")
        return {"next": "FINISH"}

    try:
        messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
        response = supervisor_llm.invoke(messages)
        
        # Clean markdown formatting if the LLM adds it
        raw_text = response.content.strip()
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        json_str = match.group(0) if match else raw_text
        
        data = json.loads(json_str)
        next_agent = data.get("next", "FINISH")
        reply_text = data.get("reply", "")
        logger.info(f"Supervisor Decision: Next Agent -> {next_agent}")
    except Exception as e:
        logger.error(f"Supervisor routing error: {str(e)}", exc_info=True)
        next_agent = "FINISH"
        reply_text = "I encountered an internal routing error."

    if next_agent == "FINISH" and reply_text:
        return {"next": next_agent, "messages": [AIMessage(content=reply_text, name="Supervisor")]}
        
    return {"next": next_agent}

# Routers
def supervisor_router(state: AgentState) -> Literal["Researcher", "Writer", "Emailer", "__end__"]:
    target = state.get("next", "FINISH")
    return END if target == "FINISH" else target

def worker_router(state: AgentState, tools_node: str):
    last_msg = state["messages"][-1]
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        logger.info(f"Worker requested tool calls: {[t['name'] for t in last_msg.tool_calls]} -> Routing to {tools_node}")
        return tools_node
    logger.info("Worker finished task without tool calls -> Returning to Supervisor")
    return "Supervisor"

# Build Graph
builder = StateGraph(AgentState)

researcher = ResearcherAgent()
writer = WriterAgent()
emailer = EmailerAgent()

builder.add_node("Supervisor", supervisor_node)
builder.add_node("Researcher", researcher.node)
builder.add_node("Researcher_Tools", ToolNode(researcher.tools))
builder.add_node("Writer", writer.node)
builder.add_node("Writer_Tools", ToolNode(writer.tools))
builder.add_node("Emailer", emailer.node)
builder.add_node("Emailer_Tools", ToolNode(emailer.tools))

builder.add_edge(START, "Supervisor")
builder.add_conditional_edges("Supervisor", supervisor_router)

builder.add_conditional_edges("Researcher", lambda s: worker_router(s, "Researcher_Tools"), {"Researcher_Tools": "Researcher_Tools", "Supervisor": "Supervisor"})
builder.add_edge("Researcher_Tools", "Researcher")

builder.add_conditional_edges("Writer", lambda s: worker_router(s, "Writer_Tools"), {"Writer_Tools": "Writer_Tools", "Supervisor": "Supervisor"})
builder.add_edge("Writer_Tools", "Writer")

builder.add_conditional_edges("Emailer", lambda s: worker_router(s, "Emailer_Tools"), {"Emailer_Tools": "Emailer_Tools", "Supervisor": "Supervisor"})
builder.add_edge("Emailer_Tools", "Emailer")

memory = MemorySaver()

workflow = builder.compile(
    checkpointer=memory,
    interrupt_before=["Emailer"]
)