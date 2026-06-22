import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.outline_gen_service import OutlineGenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/project/{project_id}/outline/generate", tags=["outline_gen"])


@router.post("/volumes")
async def generate_volumes(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    story_desc = body.get("story_desc", "")
    setting_ids = body.get("setting_ids", [])

    async def event_stream():
        async for chunk in OutlineGenerationService.generate_volumes_stream(db, project_id, story_desc, setting_ids):  # noqa: E501
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chapters")
async def generate_chapters(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    async def event_stream():
        async for chunk in OutlineGenerationService.generate_chapters_stream(
            db, project_id, body.get("volume_title", ""), body.get("volume_summary", ""), int(body.get("count", 0))  # noqa: E501
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sections")
async def generate_sections(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    async def event_stream():
        async for chunk in OutlineGenerationService.generate_sections_stream(
            db, project_id, body.get("chapter_title", ""), body.get("chapter_summary", ""), int(body.get("count", 0))  # noqa: E501
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/content")
async def generate_content(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    sections = body.get("sections", [])
    async def event_stream():
        async for chunk in OutlineGenerationService.generate_content_stream(
            db, project_id, body.get("chapter_title", ""), sections
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/confirm")
async def confirm_generation(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    items = body.get("items", [])
    parent_id = body.get("parent_id")
    count = OutlineGenerationService.confirm_save(db, project_id, items, parent_id)
    return {"count": count, "project_id": project_id}
