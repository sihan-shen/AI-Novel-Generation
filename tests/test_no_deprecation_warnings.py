"""Verify zero Pydantic class Config warnings and zero datetime.utcnow warnings."""

import subprocess
import sys
from datetime import UTC


def test_config_import_no_pydantic_class_config_warning():
    """Importing app.config must not raise Pydantic class Config deprecation."""
    code = """
import warnings
warnings.filterwarnings('error', category=DeprecationWarning, message='.*class-based.*config.*')
import app.config
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_schemas_and_routers_no_pydantic_class_config_warning():
    """Importing schemas and routers must not raise Pydantic class Config deprecation."""
    code = """
import warnings
warnings.filterwarnings('error', category=DeprecationWarning, message='.*class-based.*config.*')
import app.schemas.outline
import app.schemas.project
import app.routers.chapters
import app.routers.ideas
import app.routers.reviews
import app.routers.settings
import app.routers.styles
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_model_creation_no_datetime_utcnow_warning():
    """Creating model instances must not call datetime.utcnow()."""
    code = """
import warnings
warnings.filterwarnings('error', message='.*utcnow.*', category=DeprecationWarning)
from app.database import Base, engine
from sqlalchemy.orm import sessionmaker
# Import all models before create_all so tables are registered
from app.models.project import Project
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.models.setting import Setting
from app.models.review import Review
from app.models.style import Style
from app.models.idea import Idea
from app.models.ai_call import AICall
from app.models.agent_task import AgentTask
from app.models.agent_message import AgentMessage
from app.models.chapter_snapshot import ChapterSnapshot
from app.models.config import Config
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

import uuid as uuid_mod

pid = str(uuid_mod.uuid4())
cid = str(uuid_mod.uuid4())
tid = str(uuid_mod.uuid4())

p = Project(id=pid, title='test')
db.add(p)
o = Outline(id=str(uuid_mod.uuid4()), project_id=pid, level=1, title='test')
db.add(o)
ch = Chapter(id=cid, project_id=pid, outline_id=o.id, title='test')
db.add(ch)
s = Setting(id=str(uuid_mod.uuid4()), project_id=pid, category='char', name='test', key='test')
db.add(s)
r = Review(id=str(uuid_mod.uuid4()), project_id=pid, chapter_id=ch.id, scope='full')
db.add(r)
st = Style(id=str(uuid_mod.uuid4()), name='test')
db.add(st)
i = Idea(id=str(uuid_mod.uuid4()), content='test')
db.add(i)
ac = AICall(id=str(uuid_mod.uuid4()), project_id=pid, scenario='test', model='test')
db.add(ac)
at = AgentTask(id=tid, project_id=pid, task_type='test')
db.add(at)
am = AgentMessage(id=str(uuid_mod.uuid4()), task_id=tid, role='user', content='test')
db.add(am)
cs = ChapterSnapshot(id=str(uuid_mod.uuid4()), chapter_id=cid, content='test')
db.add(cs)
c = Config(key='test', value='test')
db.add(c)
db.commit()
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_agent_router_no_datetime_utcnow_warning():
    """Importing agent router must not trigger datetime.utcnow deprecation."""
    code = """
import warnings
warnings.filterwarnings('error', message='.*utcnow.*', category=DeprecationWarning)
import app.routers.agent
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_outline_response_tree_shape():
    """OutlineResponse with children populates correctly after model_rebuild."""
    from datetime import datetime

    from app.schemas.outline import OutlineResponse

    child = OutlineResponse(
        id="c1", project_id="p1", parent_id="o1", level=2, sort_order=1,
        title="Child", summary="", notes="", status="draft",
        word_count_target=0, word_count_actual=0, pov_character="",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        children=[],
    )
    parent = OutlineResponse(
        id="o1", project_id="p1", parent_id=None, level=1, sort_order=0,
        title="Parent", summary="", notes="", status="draft",
        word_count_target=0, word_count_actual=0, pov_character="",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        children=[child],
    )
    assert isinstance(parent.children, list)
    assert parent.children == [child]
    assert parent.children[0].title == "Child"
