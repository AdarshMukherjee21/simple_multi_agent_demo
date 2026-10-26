from langchain_core.messages import SystemMessage
from config import get_llm
from tools import lookup_policy, lookup_leave, fetch_email_id, write_email, send_email

class ResearcherAgent:
    def __init__(self):
        self.tools = [lookup_policy, lookup_leave]
        self.llm = get_llm().bind_tools(self.tools)
        self.system_prompt = SystemMessage(
            content="You are the Researcher Agent. Search the knowledge base for relevant policy/leave information. Do NOT draft emails or send them."
        )

    def node(self, state):
        messages = [self.system_prompt] + state["messages"]
        response = self.llm.invoke(messages)
        response.name = "Researcher"
        return {"messages": [response]}

class WriterAgent:
    def __init__(self):
        self.tools = [fetch_email_id, write_email]
        self.llm = get_llm().bind_tools(self.tools)
        self.system_prompt = SystemMessage(
            content="You are the Writer Agent. Summarize information provided by the Researcher into a clear email. Fetch recipient emails and save drafts. Do NOT search policies or send emails directly."
        )

    def node(self, state):
        messages = [self.system_prompt] + state["messages"]
        response = self.llm.invoke(messages)
        response.name = "Writer"
        return {"messages": [response]}

class EmailerAgent:
    def __init__(self):
        self.tools = [send_email]
        self.llm = get_llm().bind_tools(self.tools)
        self.system_prompt = SystemMessage(
            content="You are the Emailer Agent. Send approved email drafts to their recipients. Do NOT conduct research or write summaries."
        )

    def node(self, state):
        messages = [self.system_prompt] + state["messages"]
        response = self.llm.invoke(messages)
        response.name = "Emailer"
        return {"messages": [response]}