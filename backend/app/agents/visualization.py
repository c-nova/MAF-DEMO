"""エージェント実行の可視化機能

エージェントの実行フローをトレースして可視化データを生成
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentTracer:
    """エージェント実行のトレーサー
    
    エージェントの実行状況を記録し、可視化用のデータを生成
    """
    
    def __init__(self):
        """トレーサーの初期化"""
        self.traces: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []
        
    def start_session(self):
        """トレースセッション開始"""
        self.start_time = time.time()
        self.traces = []
        self.nodes = []
        self.edges = []
        logger.info("🔍 Tracing session started")
        
    def add_agent_start(self, agent_name: str, agent_id: str, input_message: str) -> str:
        """エージェント実行開始を記録
        
        Args:
            agent_name: エージェント名
            agent_id: エージェントID
            input_message: 入力メッセージ
            
        Returns:
            トレースID
        """
        trace_id = str(uuid4())
        timestamp = time.time()
        
        trace = {
            "id": trace_id,
            "type": "agent_start",
            "agent_name": agent_name,
            "agent_id": agent_id,
            "input": input_message,
            "timestamp": timestamp,
            "relative_time": timestamp - self.start_time if self.start_time else 0,
        }
        self.traces.append(trace)
        
        # ノード追加
        node = {
            "id": trace_id,
            "type": "agent",
            "label": agent_name,
            "status": "running",
            "timestamp": timestamp,
        }
        self.nodes.append(node)
        
        logger.debug(f"📍 Agent start: {agent_name} (ID: {trace_id})")
        return trace_id
        
    def add_agent_complete(self, trace_id: str, output: str, status: str = "completed"):
        """エージェント実行完了を記録
        
        Args:
            trace_id: トレースID
            output: 出力結果
            status: 実行ステータス（completed/failed）
        """
        timestamp = time.time()
        
        trace = {
            "id": trace_id,
            "type": "agent_complete",
            "output": output,
            "status": status,
            "timestamp": timestamp,
            "relative_time": timestamp - self.start_time if self.start_time else 0,
        }
        self.traces.append(trace)
        
        # ノードステータス更新
        for node in self.nodes:
            if node["id"] == trace_id:
                node["status"] = status
                node["duration"] = timestamp - node["timestamp"]
                break
                
        logger.debug(f"✅ Agent complete: {trace_id} ({status})")
        
    def add_agent_transition(self, from_trace_id: str, to_trace_id: str, data: Optional[str] = None):
        """エージェント間の遷移を記録
        
        Args:
            from_trace_id: 遷移元トレースID
            to_trace_id: 遷移先トレースID
            data: 遷移データ（省略可）
        """
        edge = {
            "from": from_trace_id,
            "to": to_trace_id,
            "label": "transition",
            "data": data,
        }
        self.edges.append(edge)
        
        logger.debug(f"🔗 Transition: {from_trace_id} -> {to_trace_id}")
        
    def add_tool_execution(self, parent_trace_id: str, tool_name: str, tool_input: Any, tool_output: Any):
        """ツール実行を記録
        
        Args:
            parent_trace_id: 親エージェントのトレースID
            tool_name: ツール名
            tool_input: ツール入力
            tool_output: ツール出力
        """
        trace_id = str(uuid4())
        timestamp = time.time()
        
        trace = {
            "id": trace_id,
            "type": "tool_execution",
            "parent_id": parent_trace_id,
            "tool_name": tool_name,
            "input": str(tool_input),
            "output": str(tool_output),
            "timestamp": timestamp,
            "relative_time": timestamp - self.start_time if self.start_time else 0,
        }
        self.traces.append(trace)
        
        # ツールノード追加
        node = {
            "id": trace_id,
            "type": "tool",
            "label": tool_name,
            "status": "completed",
            "timestamp": timestamp,
        }
        self.nodes.append(node)
        
        # 親エージェントとの接続
        edge = {
            "from": parent_trace_id,
            "to": trace_id,
            "label": "uses",
        }
        self.edges.append(edge)
        
        logger.debug(f"🔧 Tool execution: {tool_name} (Parent: {parent_trace_id})")
        
    def get_visualization_data(self) -> Dict[str, Any]:
        """可視化用データを取得
        
        Returns:
            可視化データ（nodes, edges, traces）
        """
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "traces": self.traces,
            "session_duration": time.time() - self.start_time if self.start_time else 0,
            "total_agents": len([n for n in self.nodes if n["type"] == "agent"]),
            "total_tools": len([n for n in self.nodes if n["type"] == "tool"]),
        }
        
    def get_summary(self) -> str:
        """実行サマリーを取得
        
        Returns:
            サマリー文字列
        """
        agent_count = len([n for n in self.nodes if n["type"] == "agent"])
        tool_count = len([n for n in self.nodes if n["type"] == "tool"])
        duration = time.time() - self.start_time if self.start_time else 0
        
        return f"Executed {agent_count} agents, {tool_count} tools in {duration:.2f}s"
