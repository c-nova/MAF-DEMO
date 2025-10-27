import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { VisualizationPane } from './components/VisualizationPane';
import './App.css';

interface VisualizationData {
  nodes: Array<{
    id: string;
    type: 'agent' | 'tool';
    label: string;
    status: 'running' | 'completed' | 'failed';
    timestamp: number;
    duration?: number;
  }>;
  edges: Array<{
    from: string;
    to: string;
    label: string;
    data?: string;
  }>;
  traces: Array<Record<string, unknown>>;
  session_duration: number;
  total_agents: number;
  total_tools: number;
}

interface AgentResponse {
  topic: string;
  research: string;
  article: string;
  review: string;
  visualization?: VisualizationData;
}

function App() {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!topic.trim()) {
      setError('トピックを入力してください');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/api/agents/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic: topic.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'エラーが発生しました');
      }

      const data: AgentResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '不明なエラーが発生しました');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <div className="app">
        <header className="header">
          <h1>🤖 Multi-Agent Framework Demo</h1>
          <p>Microsoft Agent Framework を使ったマルチエージェントシステム</p>
        </header>

        <main className="main">
          <form onSubmit={handleSubmit} className="input-form">
            <div className="input-group">
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="トピックを入力してください（例: Microsoft Build 2025の最新情報）"
                className="topic-input"
                disabled={loading}
              />
              <button 
                type="submit" 
                className="submit-button"
                disabled={loading}
              >
                {loading ? '処理中...' : '🚀 実行'}
              </button>
            </div>
          </form>

          {error && (
            <div className="error-box">
              <h3>❌ エラー</h3>
              <p>{error}</p>
            </div>
          )}

          {loading && (
            <div className="loading-box">
              <div className="spinner"></div>
              <p>マルチエージェントが処理中です...</p>
              <small>Research → Writer → Reviewer の順で実行中</small>
            </div>
          )}

          {result && (
            <div className="results">
              <div className="result-card">
                <div className="card-header research">
                  <h2>🔍 Research Agent</h2>
                  <span className="badge">調査</span>
                </div>
                <div className="card-content markdown-content">
                  <ReactMarkdown>{result.research}</ReactMarkdown>
                </div>
              </div>

              <div className="result-card">
                <div className="card-header writer">
                  <h2>✍️ Writer Agent</h2>
                  <span className="badge">執筆</span>
                </div>
                <div className="card-content markdown-content">
                  <ReactMarkdown>{result.article}</ReactMarkdown>
                </div>
              </div>

              <div className="result-card">
                <div className="card-header reviewer">
                  <h2>👁️ Reviewer Agent</h2>
                  <span className="badge">レビュー</span>
                </div>
                <div className="card-content markdown-content">
                  <ReactMarkdown>{result.review}</ReactMarkdown>
                </div>
              </div>
            </div>
          )}
        </main>

        <footer className="footer">
          <p>Powered by Microsoft Agent Framework + FastAPI + Vite</p>
        </footer>
      </div>

      <VisualizationPane data={result?.visualization || null} />
    </div>
  );
}

export default App;
