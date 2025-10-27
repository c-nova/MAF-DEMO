"""FastAPI メインアプリケーション"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent_router
from app.config import settings

# ロギング設定
if settings.debug:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)
else:
    logging.basicConfig(level=logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時の処理
    print("🚀 Starting Multi-Agent Framework Demo API...")
    print(f"📍 Environment: {settings.environment}")
    print(f"� Debug Mode: {'ON' if settings.debug else 'OFF'}")
    print(f"�🔗 Azure AI Foundry: {settings.get_connection_info()}")
    print(f"🤖 Model: {settings.model_deployment_name}")

    yield

    # 終了時の処理
    print("👋 Shutting down Multi-Agent Framework Demo API...")


# FastAPIアプリケーション作成
app = FastAPI(
    title="MAF Demo API",
    description="Microsoft Agent Framework を使ったマルチエージェントシステムのデモAPI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(agent_router)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Welcome to MAF Demo API",
        "docs": "/docs",
        "health": "/api/agents/health",
    }


@app.get("/health")
async def health():
    """グローバルヘルスチェック"""
    return {"status": "healthy", "service": "maf-demo-api"}
