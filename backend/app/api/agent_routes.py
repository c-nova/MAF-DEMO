"""エージェント関連のAPIエンドポイント"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents import create_multi_agent_system

router = APIRouter(prefix="/api/agents", tags=["agents"])


class ProcessTopicRequest(BaseModel):
    """トピック処理リクエスト"""

    topic: str = Field(..., description="処理するトピック", min_length=1, max_length=500)


class ProcessTopicResponse(BaseModel):
    """トピック処理レスポンス"""

    topic: str = Field(..., description="処理されたトピック")
    research: str = Field(..., description="リサーチ結果")
    article: str = Field(..., description="作成された記事")
    review: str = Field(..., description="レビュー結果")
    visualization: Dict[str, Any] = Field(..., description="可視化データ")


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str = Field(..., description="サービスステータス")
    message: str = Field(..., description="メッセージ")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """ヘルスチェックエンドポイント

    Returns:
        サービスの状態
    """
    return HealthResponse(status="healthy", message="Multi-agent system is running")


@router.post("/process", response_model=ProcessTopicResponse)
async def process_topic(request: ProcessTopicRequest) -> ProcessTopicResponse:
    """トピックをマルチエージェントで処理

    Args:
        request: トピック処理リクエスト

    Returns:
        各エージェントの処理結果

    Raises:
        HTTPException: 処理中にエラーが発生した場合
    """
    try:
        # マルチエージェントシステムを作成
        multi_agent = create_multi_agent_system()

        # トピックを処理
        result = await multi_agent.process(request.topic)

        return ProcessTopicResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"エージェント処理中にエラーが発生しました: {str(e)}"
        ) from e
