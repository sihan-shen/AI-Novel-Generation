from sqlalchemy.orm import Session
from app.models.config import Config


class ConfigService:
    DEFAULTS = {
        "llm_provider": "claude",
        "claude_api_key": "",
        "openai_api_key": "",
        "claude_model": "claude-sonnet-4-6",
        "openai_model": "gpt-4o",
    }

    @staticmethod
    def get_all(db: Session) -> dict:
        rows = db.query(Config).all()
        result = dict(ConfigService.DEFAULTS)
        for row in rows:
            result[row.key] = row.value
        return result

    @staticmethod
    def get(db: Session, key: str) -> str | None:
        row = db.query(Config).filter(Config.key == key).first()
        return row.value if row else ConfigService.DEFAULTS.get(key)

    @staticmethod
    def set(db: Session, key: str, value: str) -> None:
        row = db.query(Config).filter(Config.key == key).first()
        if row:
            row.value = value
        else:
            db.add(Config(key=key, value=value))
        db.commit()

    @staticmethod
    def set_many(db: Session, items: dict) -> None:
        for key, value in items.items():
            ConfigService.set(db, key, value)
