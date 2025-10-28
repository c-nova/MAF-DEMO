"""エージェント関連のAPIエンドポイント"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents import create_multi_agent_system

router = APIRouter(prefix="/api/agents", tags=["agents"])


class ProcessTopicRequest(BaseModel):
    """トピック処理リクエスト

    Attributes:
        topic: 処理対象トピック
        taste: 出力テイスト（広告風/お客様提案資料風/Web記事風/論文風）
    """

    topic: str = Field(..., description="処理するトピック", min_length=1, max_length=500)
    taste: Optional[str] = Field(
        "Web記事風",
        description="文章生成テイスト (広告風 / お客様提案資料風 / Web記事風 / 論文風)",
        examples=["広告風", "お客様提案資料風", "Web記事風", "論文風"],
    )


class ProcessTopicResponse(BaseModel):
    """トピック処理レスポンス"""

    session_id: str = Field(..., description="セッションID")
    status: str = Field(..., description="ステータス（pending_approval/approved/max_iterations_reached）")
    iteration: Optional[int] = Field(None, description="現在のイテレーション回数")
    max_iterations: Optional[int] = Field(None, description="最大イテレーション回数")
    message: Optional[str] = Field(None, description="メッセージ（エラー時等）")
    stage: Optional[str] = Field(None, description="現在のステージ（research/write/review/completed）")
    topic: str = Field(..., description="処理されたトピック")
    taste: Optional[str] = Field(None, description="採用された文章テイスト")
    research: str = Field(..., description="リサーチ結果")
    research_citations: Optional[list[Dict[str, Any]]] = Field(None, description="リサーチのCitations情報")
    article: str = Field(..., description="作成された記事")
    review: str = Field(..., description="レビュー結果")
    illustrations: Optional[list[Dict[str, Any]]] = Field(None, description="挿絵情報リスト (prompt/url/alt など)")
    visualization: Dict[str, Any] = Field(..., description="可視化データ")


class FeedbackRequest(BaseModel):
    """フィードバックリクエスト"""

    session_id: str = Field(..., description="セッションID")
    approved: bool = Field(..., description="承認フラグ（True: OK, False: NG）")
    feedback: Optional[str] = Field(None, description="フィードバックメッセージ（NGの場合）")


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
        result = await multi_agent.process(request.topic, taste=request.taste)

        return ProcessTopicResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"エージェント処理中にエラーが発生しました: {str(e)}"
        ) from e


@router.post("/feedback", response_model=ProcessTopicResponse)
async def handle_feedback(request: FeedbackRequest) -> ProcessTopicResponse:
    """Human feedbackを処理（承認またはフィードバック付き再実行）

    Args:
        request: フィードバックリクエスト

    Returns:
        処理結果（OKの場合は完了、NGの場合は再実行結果）

    Raises:
        HTTPException: 処理中にエラーが発生した場合
    """
    try:
        # マルチエージェントシステムを作成
        multi_agent = create_multi_agent_system()

        # フィードバックを処理
        result = await multi_agent.handle_feedback(
            session_id=request.session_id,
            approved=request.approved,
            feedback=request.feedback
        )

        # エラーがあれば例外を投げる
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return ProcessTopicResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"フィードバック処理中にエラーが発生しました: {str(e)}"
        ) from e
