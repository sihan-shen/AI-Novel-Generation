from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/novel_tool.db"
    llm_provider: str = "claude"
    claude_api_key: str = ""
    openai_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
