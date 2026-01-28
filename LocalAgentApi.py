import json
import time
from typing import List

from fastapi import FastAPI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from LocalAgent import LocalAgent
from ConfigurationManager import ConfigurationManager
import requests

agent = LocalAgent()
app = FastAPI()
models = ConfigurationManager.get_configuration("agent")
tasks = ConfigurationManager.get_configuration("tasksModel")

class ChatRequest(BaseModel):
    messages: list
    model: str


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    if request.model == models["model"]:
        return StreamingResponse(get_agent_stream(request.messages), media_type="text/event-stream")
    elif request.model == tasks["model"]:
        request.messages[-1]["content"] = request.messages[-1]["content"] + "\n/nothink"
        data = json.dumps(request.model_dump(mode="json"))
        response = requests.post(tasks["baseUrl"]+"/chat/completions", data=data, headers={"Content-Type": "application/json"}).json()
        return response
    return "data: [DONE]\n\n"

@app.get("/v1/models")
async def get_models():
    return {
        "object": "list",
        "data": [{
            "id": models["model"],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "organization-owner",
        },
        {
            "id": tasks["model"],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "organization-owner",
        }]
    }

async def get_agent_stream(messages: List):
    start_state = [HumanMessage(content=item["content"]) if item["role"] == "user" else AIMessage(content=item["content"])
             for item in messages]
    try:
        async for response in agent.gui_chat_async(start_state):
            yield format_response(response)
    except Exception as e:
        print(f"Error in agent stream: {e}")
    yield "data: [DONE]\n\n"

def format_response(message: str):
    data = {
        "id": "default-chat",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "langgraph-agent",
        "choices": [
            {
                "delta": {"content": message},
                "index": 0,
                "finish_reason": None
            }
        ]
    }
    return f"data: {json.dumps(data)}\n\n"

def start_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")