import logging

from sqlalchemy.orm import Session

from app.models.config import Config

logger = logging.getLogger(__name__)


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
        """Return the full config including the raw ``api_key``.

        This is the *internal* view of configuration used by backend code
        that actually needs the real credentials (e.g. ``get_adapter``).
        Do NOT expose this dict to clients without redaction.
        """
        rows = db.query(Config).all()
        result = dict(ConfigService.DEFAULTS)
        for row in rows:
            result[row.key] = row.value  # type: ignore[index,assignment]
        return result

    @staticmethod
    def get_all_masked(db: Session) -> dict:
        """Return config safe for client consumption.

        The raw ``api_key`` is replaced with two fields:

        * ``api_key_set`` — bool, True iff a non-empty key is stored.
        * ``api_key_masked`` — str, ``"<first 3 chars>...<last 4 chars>"``
          (e.g. ``"sk-...6789"``) when a key is set, otherwise ``""``.

        All other config keys are returned unchanged.
        """
        cfg = ConfigService.get_all(db)
        raw_key = cfg.get("api_key", "") or ""
        # Remove the raw key from the outgoing payload
        cfg.pop("api_key", None)
        if raw_key:
            cfg["api_key_set"] = True
            if len(raw_key) > 7:
                cfg["api_key_masked"] = f"{raw_key[:3]}...{raw_key[-4:]}"
            else:
                # Key too short to safely mask with the standard pattern;
                # still show only the first 3 + "..." + last 4 from the key.
                cfg["api_key_masked"] = (
                    f"{raw_key[:3]}...{raw_key[-4:]}" if len(raw_key) >= 4 else "***"
                )
        else:
            cfg["api_key_set"] = False
            cfg["api_key_masked"] = ""
        return cfg

    @staticmethod
    def get(db: Session, key: str) -> str | None:
        row = db.query(Config).filter(Config.key == key).first()
        return row.value if row else ConfigService.DEFAULTS.get(key)  # type: ignore[return-value]

    @staticmethod
    def set(db: Session, key: str, value: str) -> None:
        row = db.query(Config).filter(Config.key == key).first()
        if row:
            row.value = value  # type: ignore[assignment]
        else:
            db.add(Config(key=key, value=value))
        db.commit()
        logger.info("Updated config %s", key)

    @staticmethod
    def set_many(db: Session, items: dict) -> None:
        for key, value in items.items():
            ConfigService.set(db, key, value)
