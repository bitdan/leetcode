from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sql_generator.service import generate_sql_payload

router = APIRouter(prefix="/api/v1", tags=["sql-generator"])


class SqlGeneratorRequest(BaseModel):
    account: str = Field(default="", description="账号站点参数（可空），格式如 QD-US")
    question: str = Field(..., description="用户问题")


class SqlGeneratorResponse(BaseModel):
    sql: str
    preview_sql: str = Field(default="", description="仅用于展示的替换参数 SQL")
    params: List[str]
    result_columns: List[str]
    explanation: str
    tables: List[str]


@router.post("/sql-generator", response_model=SqlGeneratorResponse)
async def sql_generator(req: SqlGeneratorRequest) -> SqlGeneratorResponse:
    try:
        payload = generate_sql_payload(
            account_token=req.account,
            question=req.question,
        )
        return SqlGeneratorResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SQL 生成失败: {exc}")
