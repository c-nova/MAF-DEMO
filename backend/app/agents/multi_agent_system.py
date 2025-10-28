"""マルチエージェントシステムの実装

このモジュールでは、以下のエージェントを定義:
- ResearchAgent: 情報収集と調査を担当（Bing Grounding有効）
- WriterAgent: コンテンツ作成と文章生成を担当
- ReviewerAgent: レビューと品質チェックを担当
"""

import logging
import uuid
import re
import urllib.parse
from typing import Any, Dict, Optional, List

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential, DefaultAzureCredential

from app.config import settings
from app.agents.visualization import AgentTracer

# ロガー設定
logger = logging.getLogger(__name__)

# テイスト設定辞書
taste_configs: Dict[str, Dict[str, Any]] = {
    "広告風": {
        "style": "キャッチーで短いセンテンス。強い動詞と感嘆符を適度に使用。読者の注意を最初の1行で掴み、CTAを含める。",
        "structure": ["フック", "ベネフィット", "社会的証拠", "CTA"],
    },
    "お客様提案資料風": {
        "style": "丁寧で論理的。ビジネス敬語。箇条書きや番号付きリストを活用。抽象→具体の順序。",
        "structure": ["課題", "解決策", "導入効果", "次のステップ"],
    },
    "Web記事風": {
        "style": "親しみやすく適度な口語。視認性の高い見出しと短い段落。必要なら箇条書き。",
        "structure": ["導入", "本論", "詳細セクション", "まとめ"],
    },
    "論文風": {
        "style": "学術的で客観的。専門用語は定義。引用や根拠を明示。過剰な誇張禁止。",
        "structure": ["要旨", "序論", "方法", "結果", "考察", "結論"],
    },
}


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
    
    Human in the loop:
    - Reviewerの結果を承認待ち状態で返す
    - フィードバックを受けて再実行
    - 最大10回まで試行可能
    """
    
    # クラス変数: セッション管理用ストレージ
    _sessions: Dict[str, Dict[str, Any]] = {}
    MAX_ITERATIONS = 10

    def __init__(self):
        """エージェントシステムの初期化"""
        # AI Project クライアントを取得
        self.project_client = _get_project_client()
        # トレーサーを初期化
        self.tracer = AgentTracer()
    
    def _run_agent(self, agent_config: dict, user_message: str) -> tuple[str, str, List[Dict[str, Any]]]:
        """エージェント実行（トレース付き）
        
        Args:
            agent_config: エージェント設定
            user_message: ユーザーメッセージ
            
        Returns:
            (結果文字列, トレースID, Citations情報リスト)
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
        citations = []
        status = "failed"
        
        if run.status == "completed":
            status = "completed"
            messages = self.project_client.agents.messages.list(thread_id=thread.id)
            for msg in messages:
                if msg.role == "assistant":
                    if msg.text_messages and len(msg.text_messages) > 0:
                        text_msg = msg.text_messages[0]
                        result = text_msg.text.value
                        
                        # Citations情報を取得
                        if hasattr(text_msg.text, 'annotations') and text_msg.text.annotations:
                            for annotation in text_msg.text.annotations:
                                # ファイル引用をチェック
                                file_citation = getattr(annotation, 'file_citation', None)
                                if file_citation is not None:
                                    citations.append({
                                        "type": "file",
                                        "text": annotation.text,
                                        "file_id": getattr(file_citation, 'file_id', None)
                                    })
                                    continue
                                
                                # URL引用をチェック（Bing Groundingなど）
                                url_citation = getattr(annotation, 'url_citation', None)
                                if url_citation is not None:
                                    citations.append({
                                        "type": "url",
                                        "text": annotation.text,
                                        "url": getattr(url_citation, 'url', None),
                                        "title": getattr(url_citation, 'title', None)
                                    })
                        
                        logger.info(f"📎 Found {len(citations)} citations")
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
        
        return result, trace_id, citations

    def _generate_illustrations(self, article_markdown: str, taste: str) -> List[Dict[str, Any]]:
        """記事本文から簡易に挿絵用プロンプトを生成（ダミーURL返却）

        NOTE: 現時点では実際の画像生成API呼び出しは行わず、将来の差し替えを前提に
        見出し(H2/H3)を抽出 → 先頭3件を題材化 → placehold.co のプレースホルダー画像URLを返す。

        Args:
            article_markdown: Writer生成Markdown
            taste: テイスト（プロンプト差別化用）
        Returns:
            list[{prompt,url,alt}]
        """
        if not article_markdown.strip():
            return []

        # 見出し抽出 (#, ##, ###)
        headings = re.findall(r"^#{2,3}\s+(.+)$", article_markdown, flags=re.MULTILINE)
        if not headings:
            # 段落先頭数行を fallback として使う
            lines = [l.strip() for l in article_markdown.splitlines() if l.strip()]
            headings = lines[:3]

        selected = headings[:3]
        illustrations: List[Dict[str, Any]] = []
        for idx, h in enumerate(selected, 1):
            base_text = h[:60]
            prompt = (
                f"Generate an illustrative image for: '{base_text}'. Style hint: {taste}. "
                "Clean, informative, no text overlay, high contrast."
            )
            # ダミーURL生成（将来ここを本物のimage生成に差し替え）
            label = urllib.parse.quote(base_text[:20]) or f"image{idx}"
            url = f"https://placehold.co/600x400?text={label}"  # プレースホルダー
            illustrations.append({
                "index": idx,
                "heading": base_text,
                "prompt": prompt,
                "url": url,
                "alt": f"{base_text} の挿絵"
            })
        return illustrations
    
    def _create_session(self, topic: str, taste: str) -> str:
        """新しいセッションを作成
        
        Args:
            topic: 処理するトピック
            
        Returns:
            セッションID
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "topic": topic,
            "stage": "research",  # research, write, review, completed
            "iteration": 0,
            "research_result": "",
            "research_citations": [],
            "write_result": "",
            "review_result": "",
            "illustrations": [],  # 挿絵（ダミー生成 or 画像生成エージェント）
            "research_feedbacks": [],
            "review_feedbacks": [],  # Writerは自動実行なのでフィードバックなし
            "status": "pending_approval",  # pending_approval, approved, max_iterations_reached
            "taste": taste,
        }
        logger.info(f"📝 Created new session: {session_id} at stage: research")
        return session_id
    
    def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション情報（存在しない場合はNone）
        """
        return self._sessions.get(session_id)
    
    def _update_session(self, session_id: str, **kwargs) -> None:
        """セッション情報を更新
        
        Args:
            session_id: セッションID
            **kwargs: 更新する情報
        """
        if session_id in self._sessions:
            self._sessions[session_id].update(kwargs)
            logger.info(f"📝 Updated session {session_id}: iteration={self._sessions[session_id]['iteration']}")

    async def process(self, topic: str, session_id: Optional[str] = None, taste: Optional[str] = None) -> Dict[str, Any]:
        """トピックを処理してマルチエージェントで協調作業

        Args:
            topic: 処理するトピック
            session_id: セッションID（再実行時に指定）

        Returns:
            各エージェントの結果と可視化データ、セッション情報を含む辞書
        """
        # セッション管理
        if session_id is None:
            # 新規セッション - Researchから開始
            taste_value = taste or "Web記事風"
            session_id = self._create_session(topic, taste_value)
            session = self._get_session(session_id)
            assert session is not None, "Failed to create session"
            # トレースセッション開始（新規セッションのみ）
            self.tracer.start_session()
        else:
            # 既存セッション（再実行またはステージ進行）
            session = self._get_session(session_id)
            if session is None:
                logger.error(f"❌ Session not found: {session_id}")
                return {"error": "Session not found"}
            
            # イテレーション回数チェック
            if session["iteration"] >= self.MAX_ITERATIONS:
                logger.warning(f"⚠️  Max iterations reached: {session['iteration']}")
                self._update_session(session_id, status="max_iterations_reached")
                return {
                    "session_id": session_id,
                    "status": "max_iterations_reached",
                    "stage": session["stage"],
                    "message": f"最大試行回数（{self.MAX_ITERATIONS}回）に達しました。",
                    "topic": session["topic"],
                    "taste": session.get("taste"),
                    "research": session["research_result"],
                    "article": session["write_result"],
                    "review": session["review_result"],
                    "illustrations": session.get("illustrations", []),
                    "visualization": self.tracer.get_visualization_data(),
                }
            
            # イテレーション回数を増加
            session["iteration"] += 1
            self._update_session(session_id, iteration=session["iteration"])
            # 再実行時はトレースセッションをリセットしない（継続）
        
        if settings.debug:
            logger.info(f"🔍 Starting stage: {session['stage']} for topic: {topic}")

        # ステージごとに処理
        current_stage = session["stage"]
        
        # === Research Stage ===
        if current_stage == "research":
            if settings.debug:
                logger.info("📊 Step 1: Research Agent is working...")

            # フィードバック履歴を含めたメッセージを構築
            research_message = f"以下のトピックについて調査してください: {topic}"
            if session["research_feedbacks"]:
                feedback_history = "\n\n【過去のフィードバック履歴】\n"
                for i, fb in enumerate(session["research_feedbacks"], 1):
                    feedback_history += f"{i}. {fb}\n"
                research_message += feedback_history
                research_message += "\n上記のフィードバックを踏まえて、改善した内容で調査してください。"

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
            research_result, research_trace_id, research_citations = self._run_agent(
                agent_config=research_agent_config,
                user_message=research_message
            )

            if settings.debug:
                logger.info(f"✅ Research completed: {len(research_result or '')} characters")
            
            # Research結果とCitations情報を保存
            self._update_session(
                session_id,
                research_result=research_result or "",
                research_citations=research_citations,
                status="pending_approval",
                stage="research"
            )

            return {
                "session_id": session_id,
                "status": "pending_approval",
                "stage": "research",
                "iteration": session["iteration"] + 1,
                "max_iterations": self.MAX_ITERATIONS,
                "topic": topic,
                "taste": session.get("taste"),
                "research": research_result or "",
                "research_citations": research_citations,
                "article": "",
                "review": "",
                "illustrations": session.get("illustrations", []),
                "visualization": self.tracer.get_visualization_data(),
            }
        
        # === Write & Review Stage ===
        elif current_stage in ["write", "review"]:
            # Writer Agentを実行（承認不要、自動実行）
            if settings.debug:
                logger.info("✍️  Step 2: Writer Agent is working...")

            # Review feedbacksを含めたメッセージを構築
            original_research = session['research_result']
            # 入力サイズが大きすぎる場合はトリミング（簡易トークン対策）
            MAX_RESEARCH_CHARS = 12000  # 過剰入力による server_error 回避のため暫定値
            trimmed_research = original_research
            was_trimmed = False
            if len(original_research) > MAX_RESEARCH_CHARS:
                trimmed_research = original_research[:MAX_RESEARCH_CHARS]
                was_trimmed = True
                logger.warning(
                    f"⚠️ Research result too long ({len(original_research)} chars). Trimmed to {MAX_RESEARCH_CHARS}."
                )

            write_message = (
                "以下のリサーチ結果を元に、魅力的な記事を書いてください:\n\n"
                f"{trimmed_research}"
            )
            if was_trimmed:
                write_message += (
                    "\n\n【注意】入力が長すぎたため先頭部分のみ使用しています。必要な場合は要約強化が必要です。"
                )
            if session["review_feedbacks"]:
                feedback_history = "\n\n【Reviewerからのフィードバック履歴】\n"
                for i, fb in enumerate(session["review_feedbacks"], 1):
                    feedback_history += f"{i}. {fb}\n"
                write_message += feedback_history
                write_message += "\n上記のフィードバックを踏まえて、改善した記事を書いてください。"

            # テイスト設定を取得
            taste_value = session.get("taste", "Web記事風")
            taste_conf = taste_configs.get(taste_value, taste_configs["Web記事風"])
            style_desc = taste_conf["style"]
            structure_desc = " / ".join(taste_conf["structure"])

            writer_instructions = (
                "あなたは優秀なライターです。指定されたテイストに従って記事を執筆してください。\n"
                f"[テイスト]: {taste_value}\n"
                f"[文体ガイド]: {style_desc}\n"
                f"[推奨構成]: {structure_desc}\n"
                "出力形式はMarkdown。構成要素は見出し(H2/H3)を使い、不要な前置きは避けてください。"
            )

            writer_agent_config = {
                "model": settings.model_deployment_name,
                "name": "WriterAgent",
                "instructions": writer_instructions,
            }
            write_result, write_trace_id, _ = self._run_agent(
                agent_config=writer_agent_config,
                user_message=write_message
            )
            
            # Research -> Writer の遷移を記録（初回のみ）
            if current_stage == "write":
                # Research trace_idは保存されていないので、遷移記録はスキップ
                pass

            if settings.debug:
                logger.info(f"✅ Article completed: {len(write_result or '')} characters")

            # ===== 挿絵生成 (プレースホルダー) =====
            try:
                illustrations = self._generate_illustrations(write_result or "", taste_value)
                session["illustrations"] = illustrations
                self._update_session(session_id, illustrations=illustrations)
                if settings.debug:
                    logger.info(f"🖼️ Generated {len(illustrations)} illustration placeholders")
            except Exception as illu_err:
                logger.warning(f"Illustration generation failed: {illu_err}")

            # Reviewer Agentを実行
            if settings.debug:
                logger.info("👁️  Step 3: Reviewer Agent is working...")

            reviewer_agent_config = {
                "model": settings.model_deployment_name,
                "name": "ReviewerAgent",
                "instructions": "あなたは経験豊富なエディターです。提供された記事を丁寧にレビューし、内容の正確性、読みやすさ、構成のバランスなどを評価してください。改善提案も含めて具体的なフィードバックを提供してください。",
            }
            review_result, review_trace_id, _ = self._run_agent(
                agent_config=reviewer_agent_config,
                user_message=f"以下の記事をレビューしてください:\n\n{write_result}"
            )
            
            # Writer -> Reviewer の遷移を記録
            self.tracer.add_agent_transition(write_trace_id, review_trace_id, "Writer -> Reviewer")

            if settings.debug:
                logger.info(f"✅ Review completed: {len(review_result or '')} characters")
                logger.info(f"🔄 Iteration: {session['iteration'] + 1}/{self.MAX_ITERATIONS}")
                logger.info("⏸️  Waiting for human approval...")
                logger.info(f"📊 {self.tracer.get_summary()}")
            
            # Write & Review結果を保存
            self._update_session(
                session_id,
                write_result=write_result or "",
                review_result=review_result or "",
                status="pending_approval",
                stage="review"
            )

            return {
                "session_id": session_id,
                "status": "pending_approval",
                "stage": "review",
                "iteration": session["iteration"] + 1,
                "max_iterations": self.MAX_ITERATIONS,
                "topic": topic,
                "taste": session.get("taste"),
                "research": session["research_result"],
                "article": write_result or "",
                "review": review_result or "",
                "illustrations": session.get("illustrations", []),
                "visualization": self.tracer.get_visualization_data(),
            }
        
        # 不明なステージ
        else:
            logger.error(f"❌ Unknown stage: {current_stage}")
            return {"error": f"Unknown stage: {current_stage}"}
    
    async def handle_feedback(self, session_id: str, approved: bool, feedback: Optional[str] = None) -> Dict[str, Any]:
        """Human feedbackを処理
        
        Args:
            session_id: セッションID
            approved: 承認フラグ（True: OK, False: NG）
            feedback: フィードバックメッセージ（NGの場合）
            
        Returns:
            処理結果（OKの場合は次のステージまたは完了、NGの場合は再実行結果）
        """
        session = self._get_session(session_id)
        if session is None:
            logger.error(f"❌ Session not found: {session_id}")
            return {"error": "Session not found"}
        
        current_stage = session["stage"]
        
        if approved:
            # 承認された場合
            if current_stage == "research":
                # Research承認 → Writeステージへ進む
                logger.info(f"✅ Research approved! Moving to Write stage...")
                self._update_session(session_id, stage="write")
                # Writer & Reviewer を自動実行
                return await self.process(topic=session["topic"], session_id=session_id)
                
            elif current_stage == "review":
                # Review承認 → 完了
                logger.info(f"✅ Review approved! Session completed!")
                self._update_session(session_id, status="approved", stage="completed")
                return {
                    "session_id": session_id,
                    "status": "approved",
                    "stage": "completed",
                    "message": "承認されました！すべての処理が完了しました。",
                    "topic": session["topic"],
                    "taste": session.get("taste"),
                    "research": session["research_result"],
                    "article": session["write_result"],
                    "review": session["review_result"],
                    "illustrations": session.get("illustrations", []),
                    "visualization": self.tracer.get_visualization_data(),
                }
            else:
                logger.error(f"❌ Invalid stage for approval: {current_stage}")
                return {"error": f"Invalid stage: {current_stage}"}
        else:
            # フィードバック（NG）の場合
            if current_stage == "research":
                # Research NG → Research再実行
                if feedback:
                    session["research_feedbacks"].append(feedback)
                    logger.info(f"📝 Added research feedback: {feedback}")
                
                logger.info(f"🔄 Re-running Research with feedback...")
                # Researchステージのまま再実行
                return await self.process(topic=session["topic"], session_id=session_id)
                
            elif current_stage == "review":
                # Review NG → Writer & Reviewer再実行
                if feedback:
                    session["review_feedbacks"].append(feedback)
                    logger.info(f"📝 Added review feedback: {feedback}")
                
                logger.info(f"🔄 Re-running Writer & Reviewer with feedback...")
                # Writeステージに戻して再実行（Writer → Reviewerを両方実行）
                self._update_session(session_id, stage="write")
                return await self.process(topic=session["topic"], session_id=session_id)
            else:
                logger.error(f"❌ Invalid stage for feedback: {current_stage}")
                return {"error": f"Invalid stage: {current_stage}"}


# シングルトンインスタンス保持用
_multi_agent_system_instance: Optional[MultiAgentSystem] = None

def create_multi_agent_system() -> MultiAgentSystem:
    """マルチエージェントシステムのインスタンスを取得（シングルトン）

    Returns:
        MultiAgentSystemのインスタンス（既存があれば再利用）
    """
    global _multi_agent_system_instance
    if _multi_agent_system_instance is None:
        _multi_agent_system_instance = MultiAgentSystem()
        logger.info("🆕 Created new MultiAgentSystem singleton instance")
    else:
        logger.debug("♻️ Reusing existing MultiAgentSystem singleton instance")
    return _multi_agent_system_instance
