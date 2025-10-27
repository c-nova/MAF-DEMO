"""マルチエージェントシステムの実装

このモジュールでは、以下のエージェントを定義:
- ResearchAgent: 情報収集と調査を担当（Bing Grounding有効）
- WriterAgent: コンテンツ作成と文章生成を担当
- ReviewerAgent: レビューと品質チェックを担当
"""

import logging
from typing import Any, Dict, Optional

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential, DefaultAzureCredential

from app.config import settings
from app.agents.visualization import AgentTracer

# ロガー設定
logger = logging.getLogger(__name__)


def _get_azure_credential():
    """Azure認証情報を取得"""
    if settings.use_azure_cli_auth:
        return AzureCliCredential()
    return DefaultAzureCredential()


def _get_project_client() -> AIProjectClient:
    """Azure AI Project クライアントを取得
    
    Returns:
        AIProjectClient クライアントインスタンス
    """
    return AIProjectClient(
        credential=_get_azure_credential(),
        endpoint=settings.ai_foundry_endpoint,
    )


class MultiAgentSystem:
    """マルチエージェントシステム

    3つのエージェントが協調して作業:
    1. ResearchAgent: トピックについて調査 (Bing Grounding有効)
    2. WriterAgent: 調査結果を元に文章作成
    3. ReviewerAgent: 作成された文章をレビュー
    """

    def __init__(self):
        """エージェントシステムの初期化"""
        # AI Project クライアントを取得
        self.project_client = _get_project_client()
        # トレーサーを初期化
        self.tracer = AgentTracer()
    
    def _run_agent(self, agent_config: dict, user_message: str) -> tuple[str, str]:
        """エージェント実行（トレース付き）
        
        Args:
            agent_config: エージェント設定
            user_message: ユーザーメッセージ
            
        Returns:
            (結果文字列, トレースID)
        """
        agent_name = agent_config.get("name", "UnknownAgent")
        
        # 1. エージェント新規作成
        agent = self.project_client.agents.create_agent(**agent_config)
        agent_id = agent.id
        
        # トレース開始
        trace_id = self.tracer.add_agent_start(agent_name, agent_id, user_message)
        
        # 2. スレッド作成
        thread = self.project_client.agents.threads.create()
        # 3. メッセージ追加
        self.project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        # 4. エージェント実行
        run = self.project_client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent_id
        )
        
        # 5. 結果取得
        result = ""
        status = "failed"
        
        if run.status == "completed":
            status = "completed"
            messages = self.project_client.agents.messages.list(thread_id=thread.id)
            for msg in messages:
                if msg.role == "assistant":
                    if msg.text_messages and len(msg.text_messages) > 0:
                        result = msg.text_messages[0].text.value
                        break
        else:
            # エラーの場合、詳細情報を取得
            logger.error(f"Agent run failed with status: {run.status}")
            result = f"エージェント実行エラー: {run.status}"
            if hasattr(run, 'last_error') and run.last_error:
                logger.error(f"Error details: {run.last_error}")
                result += f"\n詳細: {run.last_error}"
        
        # トレース完了
        self.tracer.add_agent_complete(trace_id, result, status)
        
        # ツール実行があればトレースに追加
        if hasattr(agent_config, 'tools') and agent_config.get('tools'):
            for tool in agent_config['tools']:
                tool_type = tool.get('type', 'unknown')
                self.tracer.add_tool_execution(
                    trace_id, 
                    tool_type, 
                    user_message, 
                    f"Tool execution: {tool_type}"
                )
        
        return result, trace_id

    async def process(self, topic: str) -> Dict[str, Any]:
        """トピックを処理してマルチエージェントで協調作業

        Args:
            topic: 処理するトピック

        Returns:
            各エージェントの結果と可視化データを含む辞書
        """
        # トレースセッション開始
        self.tracer.start_session()
        
        if settings.debug:
            logger.info(f"🔍 Starting multi-agent processing for topic: {topic}")

        # Step 1: ResearchAgentをAPIで新規作成（Bing Grounding有効）
        if settings.debug:
            logger.info("📊 Step 1: Research Agent is working...")

        research_agent_config = {
            "model": settings.model_deployment_name,
            "name": "ResearchAgent",
            "instructions": "あなたは優秀なリサーチャーです。ユーザーのトピックについて最新情報をBing検索で調査し、要点をわかりやすくまとめてください。",
            "tools": [{
                "type": "bing_grounding",
                "bing_grounding": {
                    "search_configurations": [{
                        "connection_id": f"/subscriptions/{settings.ai_foundry_subscription_id}/resourceGroups/{settings.ai_foundry_resource_group}/providers/Microsoft.CognitiveServices/accounts/imageone-resource/projects/{settings.ai_foundry_project_name}/connections/bingrag"
                    }]
                }
            }]
        }
        research_result, research_trace_id = self._run_agent(
            agent_config=research_agent_config,
            user_message=f"以下のトピックについて調査してください: {topic}"
        )

        if settings.debug:
            logger.info(f"✅ Research completed: {len(research_result or '')} characters")

        # Step 2: WriterAgentをAPIで新規作成
        if settings.debug:
            logger.info("✍️  Step 2: Writer Agent is working...")

        writer_agent_config = {
            "model": settings.model_deployment_name,
            "name": "WriterAgent",
            "instructions": "あなたは優秀なライターです。提供されたリサーチ結果を元に、読みやすく魅力的な記事を執筆してください。見出しや段落を適切に使い、読者にわかりやすい構成を心がけてください。",
        }
        write_result, write_trace_id = self._run_agent(
            agent_config=writer_agent_config,
            user_message=f"以下のリサーチ結果を元に、魅力的な記事を書いてください:\n\n{research_result}"
        )
        
        # エージェント間の遷移を記録
        self.tracer.add_agent_transition(research_trace_id, write_trace_id, "Research -> Writer")

        if settings.debug:
            logger.info(f"✅ Article completed: {len(write_result or '')} characters")

        # Step 3: ReviewerAgentをAPIで新規作成
        if settings.debug:
            logger.info("👁️  Step 3: Reviewer Agent is working...")

        reviewer_agent_config = {
            "model": settings.model_deployment_name,
            "name": "ReviewerAgent",
            "instructions": "あなたは経験豊富なエディターです。提供された記事を丁寧にレビューし、内容の正確性、読みやすさ、構成のバランスなどを評価してください。改善提案も含めて具体的なフィードバックを提供してください。",
        }
        review_result, review_trace_id = self._run_agent(
            agent_config=reviewer_agent_config,
            user_message=f"以下の記事をレビューしてください:\n\n{write_result}"
        )
        
        # エージェント間の遷移を記録
        self.tracer.add_agent_transition(write_trace_id, review_trace_id, "Writer -> Reviewer")

        if settings.debug:
            logger.info(f"✅ Review completed: {len(review_result or '')} characters")
            logger.info("🎉 All agents completed successfully!")
            logger.info(f"📊 {self.tracer.get_summary()}")

        return {
            "topic": topic,
            "research": research_result or "",
            "article": write_result or "",
            "review": review_result or "",
            "visualization": self.tracer.get_visualization_data(),
        }


def create_multi_agent_system() -> MultiAgentSystem:
    """マルチエージェントシステムのインスタンスを作成

    Returns:
        MultiAgentSystemのインスタンス
    """
    return MultiAgentSystem()
