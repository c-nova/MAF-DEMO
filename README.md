# MAF Demo - Multi-Agent Framework Demo

Microsoft Agent Frameworkを使ったマルチエージェントシステムのデモプロジェクト

## 🚀 技術スタック

### Backend
- **FastAPI** - 高速な非同期Webフレームワーク
- **Microsoft Agent Framework** - マルチエージェントオーケストレーション
- **Azure AI Foundry** - エージェント管理とデプロイ
- **uv** - 高速Pythonパッケージマネージャー

### Frontend
- **Vite** - 次世代フロントエンドビルドツール
- **React** - UIフレームワーク
- **TypeScript** - 型安全なJavaScript

### Deployment
- **Azure App Service** - バックエンドホスティング
- **Azure Static Web Apps** - フロントエンドホスティング
- **Azure AI Foundry** - エージェント管理

## 📦 セットアップ

### 前提条件
- Python 3.11以上
- Node.js 20以上
- uv (インストール: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Azure AI Foundry プロジェクト (作成方法は後述)

### Azure AI Foundry プロジェクト作成

1. [Azure AI Foundry](https://ai.azure.com/) にアクセス
2. 新しいプロジェクトを作成
3. モデルデプロイメント (gpt-4o-mini など) を作成
4. プロジェクトの接続文字列を取得:
   - Settings → Project Details → Connection String

### Backend

```bash
cd backend

# uv で依存関係をインストール
uv sync --prerelease=allow

# 環境変数を設定
cp .env.example .env
# .env を編集してAI Foundry接続文字列を設定

# 開発サーバー起動
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# 依存関係をインストール
npm install

# 開発サーバー起動
npm run dev
```

## 🔧 開発

Backend: http://localhost:8000
Frontend: http://localhost:5173
API Docs: http://localhost:8000/docs

## 🌐 Azure デプロイ

Coming soon...
