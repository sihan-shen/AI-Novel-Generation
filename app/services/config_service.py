from sqlalchemy.orm import Session
from app.models.config import Config


class ConfigService:
    DEFAULTS = {
        "llm_provider": "claude",
        "api_key": "",
        "base_url": "",
        "model": "claude-sonnet-4-6",
        "host": "0.0.0.0",
        "port": "8000",
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
