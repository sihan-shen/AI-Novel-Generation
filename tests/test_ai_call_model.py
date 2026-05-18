from datetime import datetime
from app.models.ai_call import AICall


def test_ai_call_insert_with_minimum_fields(db_session):
    call = AICall(
        scenario="writing",
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=50,
        status="success",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.id is not None
    assert call.scenario == "writing"
    assert call.input_tokens == 100
    assert call.output_tokens == 50
    assert call.status == "success"
    assert isinstance(call.created_at, datetime)


def test_ai_call_with_prompt_response_and_duration(db_session):
    call = AICall(
        scenario="outline_gen",
        model="claude-sonnet-4-6",
        prompt="Write a chapter outline",
        response="Chapter 1: ...",
        input_tokens=200,
        output_tokens=300,
        duration_ms=4500,
        status="success",
        project_id="proj-123",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.prompt == "Write a chapter outline"
    assert call.duration_ms == 4500
    assert call.project_id == "proj-123"


def test_ai_call_error_status(db_session):
    call = AICall(
        scenario="review",
        model="gpt-4-turbo",
        status="error",
        error_message="rate limit",
        input_tokens=0,
        output_tokens=0,
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.status == "error"
    assert call.error_message == "rate limit"
