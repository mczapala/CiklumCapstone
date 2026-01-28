from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from KnowledgeManager import KnowledgeManager

@tool(description="Used to retrieve knowledge about Hogwarts and Harry Potter series.")
def search_database(query: str, runtime: ToolRuntime):
    retriever = KnowledgeManager().get_retriever()
    docs = retriever.invoke(query)
    # return "Could not find any information about your query."
    return "\n\n".join([doc.page_content for doc in docs])

# List of tools provided to the agent
tools = [search_database]