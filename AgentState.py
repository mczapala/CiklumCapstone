from typing import TypedDict, List, Annotated

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    iterations: int
    evaluations: Annotated[List[AIMessage], add_messages]