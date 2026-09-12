"""LangGraph workflow for the AI IT Support Assistant."""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.state import SupportState
from src.tools import create_ticket, lookup_tickets, search_knowledge_base


SYSTEM_PROMPT = """You are the internal AI IT Support Assistant for a fictional organisation.

Use the available tools for all knowledge-base answers, ticket details, and ticket creation. Never invent employee records, ticket details, article content, or tool results.

For ticket lookup, ask for an employee ID if it is missing. For ticket creation, ask for any missing employee ID, clear title, detailed description, category, or priority before calling the creation tool. Do not say that a ticket was created unless the tool confirms it. If a tool returns an error, explain it plainly and offer the next useful action.

Keep answers concise, professional, and based only on the conversation and tool results."""

TOOLS = [search_knowledge_base, lookup_tickets, create_ticket]


def _route_after_assistant(state: SupportState) -> Literal["tools", "end"]:
    """Send model-issued tool calls to the tool node; otherwise end the turn."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


def build_graph():
    """Build a stateful tool-calling graph using configuration from ``.env``."""
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and add your Gemini API key."
        )

    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    ).bind_tools(TOOLS)

    def assistant_node(state: SupportState) -> dict[str, list]:
        response = model.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
        return {"messages": [response]}

    workflow = StateGraph(SupportState)
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", ToolNode(TOOLS))
    workflow.add_edge(START, "assistant")
    workflow.add_conditional_edges(
        "assistant",
        _route_after_assistant,
        {"tools": "tools", "end": END},
    )
    workflow.add_edge("tools", "assistant")

    return workflow.compile(checkpointer=MemorySaver())
