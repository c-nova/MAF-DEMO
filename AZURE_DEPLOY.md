# Azure デプロイ設定

このプロジェクトをAzureにデプロイする手順です。

## 前提条件

- Azure CLI インストール済み (`az --version` で確認)
- Azure アカウントでログイン済み (`az login`)
- Azure AI Foundry プロジェクト作成済み ([AI_FOUNDRY_SETUP.md](./AI_FOUNDRY_SETUP.md) 参照)

## Backend デプロイ (Azure App Service)

### 1. リソースグループ作成

```bash
az group create --name maf-demo-rg --location japaneast
```

### 2. App Service Plan 作成

```bash
az appservice plan create \
  --name maf-demo-plan \
  --resource-group maf-demo-rg \
  --sku B1 \
  --is-linux
```

### 3. Web App 作成 (Python)

```bash
az webapp create \
  --resource-group maf-demo-rg \
  --plan maf-demo-plan \
  --name maf-demo-backend \
  --runtime "PYTHON:3.11"
```

### 4. 環境変数設定

```bash
az webapp config appsettings set \
  --resource-group maf-demo-rg \
  --name maf-demo-backend \
  --settings \
    AI_FOUNDRY_CONNECTION_STRING="your-connection-string" \
    MODEL_DEPLOYMENT_NAME="gpt-4o-mini" \
    USE_AZURE_CLI_AUTH="false" \
    CORS_ORIGINS="https://your-frontend.azurestaticapps.net"
```

**接続文字列の取得方法:**
[AI_FOUNDRY_SETUP.md](./AI_FOUNDRY_SETUP.md) の「接続文字列の取得」を参照

### 5. デプロイ

```bash
cd backend
az webapp up \
  --resource-group maf-demo-rg \
  --name maf-demo-backend \
  --runtime "PYTHON:3.11"
```

## Frontend デプロイ (Azure Static Web Apps)

### 1. Static Web App 作成

```bash
az staticwebapp create \
  --name maf-demo-frontend \
  --resource-group maf-demo-rg \
  --location eastasia
```

### 2. ビルドと デプロイ

```bash
cd frontend

# 環境変数設定
echo "VITE_API_URL=https://maf-demo-backend.azurewebsites.net" > .env.production

# ビルド
npm run build

# Azure Static Web Apps CLI でデプロイ
npm install -g @azure/static-web-apps-cli
swa deploy ./dist \
  --app-name maf-demo-frontend \
  --resource-group maf-demo-rg
```

## マネージドIDを使う場合 (推奨)

API Keyの代わりにマネージドIDを使用する方が安全です。

### 1. システムマネージドIDを有効化

```bash
az webapp identity assign \
  --resource-group maf-demo-rg \
  --name maf-demo-backend
```

### 2. AI Foundry へのアクセス権限付与

```bash
# Principal ID を取得
PRINCIPAL_ID=$(az webapp identity show \
  --resource-group maf-demo-rg \
  --name maf-demo-backend \
  --query principalId -o tsv)

# Azure AI Developer ロールを付与
az role assignment create \
  --role "Azure AI Developer" \
  --assignee $PRINCIPAL_ID \
  --scope /subscriptions/{subscription-id}/resourceGroups/maf-demo-rg

# Cognitive Services User ロールも付与 (モデル使用のため)
az role assignment create \
  --role "Cognitive Services User" \
  --assignee $PRINCIPAL_ID \
  --scope /subscriptions/{subscription-id}/resourceGroups/{ai-foundry-rg}
```

### 3. 環境変数更新

```bash
az webapp config appsettings set \
  --resource-group maf-demo-rg \
  --name maf-demo-backend \
  --settings USE_AZURE_CLI_AUTH="false"
```

> **Note:** マネージドIDを使う場合、`USE_AZURE_CLI_AUTH=false` でDefaultAzureCredentialが自動的にマネージドIDを使用します

## 確認

- Backend: https://maf-demo-backend.azurewebsites.net/docs
- Frontend: https://maf-demo-frontend.azurestaticapps.net

## コスト削減のヒント

- 開発環境では Free Tier を活用
- App Service Plan は B1 (Basic) から開始
- 使用しない時はリソースを停止

```bash
# App Service 停止
az webapp stop --resource-group maf-demo-rg --name maf-demo-backend

# App Service 開始
az webapp start --resource-group maf-demo-rg --name maf-demo-backend
```
