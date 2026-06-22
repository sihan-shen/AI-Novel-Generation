import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.response import APIResponse
from app.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=APIResponse[dict])
async def get_config(db: Session = Depends(get_db)):
    # Return a redacted view: raw api_key is replaced by api_key_set +
    # api_key_masked so the secret never leaves the server over this endpoint.
    cfg = ConfigService.get_all_masked(db)
    return APIResponse(data=cfg)


@router.post("", response_model=APIResponse[dict])
async def save_config(body: dict, db: Session = Depends(get_db)):
    for key in ("llm_provider", "api_key", "base_url", "model", "host", "port"):
        if key in body:
            ConfigService.set(db, key, body[key])
    # Per task spec, POST response is unchanged: returns raw get_all().
    cfg = ConfigService.get_all(db)
    return APIResponse(data=cfg)


@router.get("/fetch-models")
async def fetch_models(
    provider: str = Query(..., description="Provider ID"),
    api_key: str = Query(""),
    base_url: str = Query(""),
):
    """Fetch available models from the provider API, or return presets."""
    from app.llm.provider_registry import fetch_models as _fetch_models

    models = await _fetch_models(provider, api_key, base_url)
    return APIResponse(data={"models": models})

logger.info("Module %s loaded", __name__)
