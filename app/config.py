from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/novel_tool.db"
    llm_provider: str = "claude"
    claude_api_key: str = ""
    openai_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
