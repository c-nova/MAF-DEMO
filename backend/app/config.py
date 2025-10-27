"""設定管理モジュール"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Azure AI Foundry
    ai_foundry_connection_string: str = ""
    ai_foundry_endpoint: str = ""
    ai_foundry_subscription_id: str = ""
    ai_foundry_resource_group: str = ""
    ai_foundry_project_name: str = ""
    ai_foundry_api_key: str = ""
    
    # Model Configuration
    model_deployment_name: str = "gpt-4o-mini"
    
    # Authentication
    use_azure_cli_auth: bool = True

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Environment
    environment: str = "development"
    debug: bool = False

    def get_connection_info(self) -> str:
        """接続情報を文字列で取得（デバッグ用）"""
        if self.ai_foundry_connection_string:
            return f"Connection String: {self.ai_foundry_connection_string[:50]}..."
        return f"Project: {self.ai_foundry_project_name}"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins をリスト形式で取得"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
