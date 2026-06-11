from app.models.project import Project
from app.models.outline import Outline


def test_agent_page_renders(client, db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()
    response = client.get("/project/p1/agent")
    assert response.status_code == 200
    assert "Agent" in response.text or "agent" in response.text.lower()


def test_agent_chat_stream_starts(client, db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Outline(id="o1", project_id="p1", parent_id=None, level=2, sort_order=1, title="Chapter 1"))
    db_session.commit()
    with client.stream("POST", "/project/p1/agent/chat/stream", json={"message": "Write chapter 1", "chapter_outline_id": "o1", "target_words": 1000}) as response:
        assert response.status_code == 200
        content = ""
        for chunk in response.iter_text():
            content += chunk
            if "event:" in content and len(content) > 50:
                break
        assert "event:" in content


def test_agent_task_list_returns_empty(client, db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()
    response = client.get("/project/p1/agent/tasks")
    assert response.status_code == 200
    body = response.json()
    assert "tasks" in body
    assert isinstance(body["tasks"], list)
