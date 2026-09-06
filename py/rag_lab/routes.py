from auth.schemas import ApiResponse
from fastapi import APIRouter, HTTPException, status
from rag_lab.schemas import RagIndexRequest, RagQueryRequest


def dump_model(model) -> dict:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/rag", tags=["RAG 实验台"])
    service = container.rag_lab_service

    @router.post("/index", response_model=ApiResponse)
    async def index_documents(payload: RagIndexRequest):
        try:
            summary = service.index(payload.collection_id, payload.documents)
            return ApiResponse(code=200, msg="知识库索引完成", data=dump_model(summary))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.post("/query", response_model=ApiResponse)
    async def query(payload: RagQueryRequest):
        try:
            result = service.query(payload.collection_id, payload.question, payload.top_k)
            return ApiResponse(code=200, msg="检索完成", data=dump_model(result))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.get("/collections/{collection_id}", response_model=ApiResponse)
    async def stats(collection_id: str):
        return ApiResponse(code=200, msg="获取知识库状态成功", data=dump_model(service.stats(collection_id)))

    @router.delete("/collections/{collection_id}", response_model=ApiResponse)
    async def reset(collection_id: str):
        return ApiResponse(code=200, msg="知识库已清空", data=dump_model(service.reset(collection_id)))

    return router
