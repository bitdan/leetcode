import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from typing import List

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from langgraph.LangGraph import graph


app = FastAPI(title="LangGraph API", version="1.0.0")

# 允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    topic: str


class ChatResponse(BaseModel):
    topic: str
    draft: str
    corrections: List[str]
    attempts: int


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        initial_state = {"topic": req.topic, "draft": "", "corrections": [], "attempts": 0}
        final_state = graph.invoke(initial_state)
        return ChatResponse(
            topic=req.topic,
            draft=final_state.get("draft", ""),
            corrections=final_state.get("corrections", []),
            attempts=final_state.get("attempts", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
