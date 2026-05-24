from app.llm.adapter import record_usage
from app.models.ai_call import AICall


def test_record_usage_writes_to_ai_call(db_session):
    record_usage(db_session, model="claude-sonnet-4-6",
                 usage={"input_tokens": 120, "output_tokens": 80},
                 scenario="writing")
    records = db_session.query(AICall).all()
    assert len(records) == 1
    assert records[0].model == "claude-sonnet-4-6"
    assert records[0].input_tokens == 120
    assert records[0].output_tokens == 80
    assert records[0].scenario == "writing"
    assert records[0].status == "success"


def test_record_usage_supports_prompt_response_duration(db_session):
    record_usage(
        db_session,
        model="gpt-4-turbo",
        usage={"input_tokens": 50, "output_tokens": 30},
        scenario="brainstorm",
        prompt="hello",
        response="world",
        duration_ms=2100,
        project_id="proj-1",
    )
    rec = db_session.query(AICall).first()
    assert rec.prompt == "hello"
    assert rec.response == "world"
    assert rec.duration_ms == 2100
    assert rec.project_id == "proj-1"


def test_record_usage_no_op_when_empty_usage(db_session):
    record_usage(db_session, model="claude", usage={}, scenario="writing")
    assert db_session.query(AICall).count() == 0
