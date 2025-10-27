# Azure AI Foundry セットアップガイド

Azure AI Foundryを使ったプロジェクトのセットアップ手順

## 🎯 Azure AI Foundry とは

Azure AI Foundryは、AIアプリケーション開発のための統合プラットフォームです。
- エージェント管理とバージョニング
- モデルデプロイメント管理
- 評価とモニタリング
- セキュリティとコンプライアンス

## 📋 準備

### 1. Azure AI Foundry ハブとプロジェクト作成

#### ポータルから作成

1. [Azure AI Foundry](https://ai.azure.com/) にアクセス
2. **+ New project** をクリック
3. プロジェクト情報を入力:
   - Project name: `maf-demo`
   - Hub: 既存を選択 or 新規作成
   - Resource group: 既存 or 新規作成
   - Location: `Japan East` 推奨

#### Azure CLI から作成

```bash
# 拡張機能インストール
az extension add --name ml

# リソースグループ作成
az group create --name maf-demo-rg --location japaneast

# AI Foundry Hub 作成
az ml workspace create \
  --kind hub \
  --resource-group maf-demo-rg \
  --name maf-demo-hub \
  --location japaneast

# AI Foundry Project 作成
az ml workspace create \
  --kind project \
  --resource-group maf-demo-rg \
  --name maf-demo-project \
  --hub-id /subscriptions/{subscription-id}/resourceGroups/maf-demo-rg/providers/Microsoft.MachineLearningServices/workspaces/maf-demo-hub
```

### 2. モデルデプロイメント作成

#### ポータルから

1. プロジェクトを開く
2. **Deployments** → **+ Create deployment**
3. モデル選択:
   - Model: `gpt-4o-mini` または `gpt-4o`
   - Deployment name: `gpt-4o-mini`
4. **Deploy** をクリック

#### Azure CLI から

```bash
# Azure OpenAI リソースが必要
az cognitiveservices account deployment create \
  --name your-openai-resource \
  --resource-group your-openai-rg \
  --deployment-name gpt-4o-mini \
  --model-name gpt-4o-mini \
  --model-version "2024-07-18" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard"
```

### 3. 接続文字列の取得

#### ポータルから

1. プロジェクトを開く
2. **Settings** → **Project details**
3. **Connection string** をコピー

フォーマット:
```
<endpoint>;<subscription-id>;<resource-group>;<project-name>
```

例:
```
eastus.api.azureml.ms;12345678-1234-1234-1234-123456789abc;maf-demo-rg;maf-demo-project
```

### 4. 認証設定

#### Azure CLI 認証 (開発環境推奨)

```bash
# Azure にログイン
az login

# サブスクリプション確認
az account show

# 必要に応じてサブスクリプション切り替え
az account set --subscription "your-subscription-id"
```

#### マネージドID (本番環境推奨)

App Service でシステムマネージドIDを有効化:

```bash
# マネージドID有効化
az webapp identity assign \
  --resource-group maf-demo-rg \
  --name maf-demo-backend

# Principal ID 取得
PRINCIPAL_ID=$(az webapp identity show \
  --resource-group maf-demo-rg \
  --name maf-demo-backend \
  --query principalId -o tsv)

# AI Foundry へのアクセス権限付与
az role assignment create \
  --role "Azure AI Developer" \
  --assignee $PRINCIPAL_ID \
  --scope /subscriptions/{subscription-id}/resourceGroups/maf-demo-rg
```

## 🔧 ローカル開発設定

### .env ファイル設定

```bash
cd backend
cp .env.example .env
```

`.env` を編集:

```bash
# AI Foundry 接続文字列
AI_FOUNDRY_CONNECTION_STRING=eastus.api.azureml.ms;your-sub-id;maf-demo-rg;maf-demo-project

# モデル名
MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# 認証 (ローカル開発)
USE_AZURE_CLI_AUTH=true
```

### 動作確認

```bash
# 依存関係インストール
uv sync --prerelease=allow

# サーバー起動
uv run uvicorn app.main:app --reload

# 別ターミナルでテスト
curl http://localhost:8000/api/agents/health
```

## 🌐 本番環境設定

### App Service 環境変数

```bash
az webapp config appsettings set \
  --resource-group maf-demo-rg \
  --name maf-demo-backend \
  --settings \
    AI_FOUNDRY_CONNECTION_STRING="your-connection-string" \
    MODEL_DEPLOYMENT_NAME="gpt-4o-mini" \
    USE_AZURE_CLI_AUTH="false"
```

## 🔍 トラブルシューティング

### 認証エラー

```
DefaultAzureCredential failed to retrieve a token
```

**解決策:**
- `az login` でログインしているか確認
- サブスクリプションが正しいか確認
- マネージドIDにロールが割り当てられているか確認

### 接続文字列エラー

```
ValueError: AI Foundry設定が不足しています
```

**解決策:**
- `.env` ファイルが存在するか確認
- `AI_FOUNDRY_CONNECTION_STRING` が正しいフォーマットか確認
- 環境変数が読み込まれているか確認

### モデルが見つからない

```
Model deployment 'gpt-4o-mini' not found
```

**解決策:**
- AI Foundry ポータルでデプロイメントを確認
- デプロイメント名が `.env` の設定と一致するか確認

## 📚 参考リンク

- [Azure AI Foundry ドキュメント](https://learn.microsoft.com/azure/ai-studio/)
- [Agent Framework ドキュメント](https://learn.microsoft.com/agent-framework/)
- [Azure AI Projects SDK](https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme)
