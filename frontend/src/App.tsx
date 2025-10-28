import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { VisualizationPane } from './components/VisualizationPane';
import './App.css';

interface Citation {
  type: 'url' | 'file';
  text: string;
  url?: string;
  title?: string;
  file_id?: string;
}

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
  session_id: string;
  status: 'pending_approval' | 'approved' | 'max_iterations_reached';
  stage: 'research' | 'write' | 'review' | 'completed';
  iteration?: number;
  max_iterations?: number;
  message?: string;
  topic: string;
  taste?: string; // 追加: バックエンドから返却されるテイスト
  research: string;
  research_citations?: Citation[];
  article: string;
  review: string;
  visualization?: VisualizationData;
}

type TasteType = '広告風' | 'お客様提案資料風' | 'Web記事風' | '論文風';

function App() {
  const [topic, setTopic] = useState('');
  const [taste, setTaste] = useState<TasteType>('Web記事風');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Citationsをリンク化する処理
  const linkifyCitations = (text: string, citations?: Citation[]): string => {
    if (!citations || citations.length === 0) return text;
    
    let linkedText = text;
    citations.forEach(citation => {
      if (citation.type === 'url' && citation.url) {
        // 【3:1†source】のような引用テキストをリンクに変換
        const escapedText = citation.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(escapedText, 'g');
        linkedText = linkedText.replace(
          regex,
          `[${citation.text}](${citation.url} "${citation.title || 'Source'}")`
        );
      }
    });
    return linkedText;
  };

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
        body: JSON.stringify({ topic: topic.trim(), taste }),
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

  const handleApprove = async () => {
    if (!result?.session_id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/agents/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: result.session_id,
          approved: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'エラーが発生しました');
      }

      const data: AgentResponse = await response.json();
      setResult(data);
      setShowFeedback(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '不明なエラーが発生しました');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = () => {
    setShowFeedback(true);
  };

  const handleFeedbackSubmit = async () => {
    if (!result?.session_id) return;
    if (!feedback.trim()) {
      setError('フィードバックを入力してください');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/agents/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: result.session_id,
          approved: false,
          feedback: feedback.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'エラーが発生しました');
      }

      const data: AgentResponse = await response.json();
      setResult(data);
      setFeedback('');
      setShowFeedback(false);
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
              <select
                value={taste}
                onChange={(e) => setTaste(e.target.value as TasteType)}
                className="taste-select"
                disabled={loading}
              >
                <option value="広告風">📢 広告風</option>
                <option value="お客様提案資料風">📊 お客様提案資料風</option>
                <option value="Web記事風">📝 Web記事風</option>
                <option value="論文風">🎓 論文風</option>
              </select>
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
              {/* Research Agent - 常に表示 */}
              {result.research && (
                <div className="result-card">
                  <div className="card-header research">
                    <h2>🔍 Research Agent</h2>
                    <span className="badge">調査</span>
                  </div>
                  <div className="card-content markdown-content">
                    <ReactMarkdown
                      components={{
                        a: (props) => (
                          <a {...props} target="_blank" rel="noopener noreferrer" />
                        ),
                      }}
                    >
                      {linkifyCitations(result.research, result.research_citations)}
                    </ReactMarkdown>
                    
                    {/* 引用元リスト表示 */}
                    {result.research_citations && result.research_citations.length > 0 && (
                      <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                        <h4 style={{ marginTop: 0, color: '#495057' }}>📚 引用元</h4>
                        <ul style={{ marginBottom: 0, paddingLeft: '1.5rem' }}>
                          {result.research_citations.map((citation, idx) => (
                            <li key={idx} style={{ marginBottom: '0.5rem' }}>
                              {citation.type === 'url' && citation.url ? (
                                <a 
                                  href={citation.url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  style={{ color: '#0066cc', textDecoration: 'none' }}
                                >
                                  {citation.title || citation.url}
                                </a>
                              ) : (
                                <span>{citation.text}</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Writer Agent - reviewステージ以降で表示 */}
              {result.article && result.stage !== 'research' && (
                <div className="result-card">
                  <div className="card-header writer">
                    <h2>✍️ Writer Agent</h2>
                    <span className="badge">執筆</span>
                  </div>
                  <div className="card-content markdown-content">
                    <ReactMarkdown>{result.article}</ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Reviewer Agent - reviewステージ以降で表示 */}
              {result.review && result.stage !== 'research' && (
                <div className="result-card">
                  <div className="card-header reviewer">
                    <h2>👁️ Reviewer Agent</h2>
                    <span className="badge">レビュー</span>
                  </div>
                  <div className="card-content markdown-content">
                    <ReactMarkdown>{result.review}</ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Human in the Loop承認UI */}
              {result.status === 'pending_approval' && (
                <div className="approval-section">
                  <div className="approval-header">
                    <h3>✋ Human in the Loop - 承認待ち ({result.stage === 'research' ? 'Research' : 'Review'})</h3>
                    {result.iteration && result.max_iterations && (
                      <span className="iteration-badge">
                        {result.iteration} / {result.max_iterations} 回目
                      </span>
                    )}
                  </div>
                  <p>
                    {result.stage === 'research' 
                      ? 'リサーチ結果を確認してください。問題なければ「承認」、改善が必要な場合は「フィードバック」をクリックしてください。'
                      : 'レビュー結果を確認してください。問題なければ「承認」、改善が必要な場合は「フィードバック」をクリックしてください。'
                    }
                  </p>
                  
                  {!showFeedback ? (
                    <div className="approval-buttons">
                      <button 
                        onClick={handleApprove} 
                        className="approve-button"
                        disabled={loading}
                      >
                        ✅ 承認
                      </button>
                      <button 
                        onClick={handleReject} 
                        className="reject-button"
                        disabled={loading}
                      >
                        ❌ フィードバック
                      </button>
                    </div>
                  ) : (
                    <div className="feedback-form">
                      <textarea
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        placeholder="改善してほしい点を具体的に入力してください..."
                        className="feedback-input"
                        rows={4}
                        disabled={loading}
                      />
                      <div className="feedback-buttons">
                        <button 
                          onClick={handleFeedbackSubmit} 
                          className="submit-feedback-button"
                          disabled={loading || !feedback.trim()}
                        >
                          🔄 フィードバックを送信して再実行
                        </button>
                        <button 
                          onClick={() => setShowFeedback(false)} 
                          className="cancel-feedback-button"
                          disabled={loading}
                        >
                          キャンセル
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {result.status === 'approved' && (
                <div className="approval-section approved">
                  <h3>✅ 承認されました！</h3>
                  <p>{result.message || '処理が完了しました。'}</p>
                </div>
              )}

              {result.status === 'max_iterations_reached' && (
                <div className="approval-section max-iterations">
                  <h3>⚠️ 最大試行回数に達しました</h3>
                  <p>{result.message || '最大試行回数に達したため、処理を終了しました。'}</p>
                </div>
              )}
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
