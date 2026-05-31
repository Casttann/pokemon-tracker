import os
import tempfile
import pytest
from app import create_app
from database import init_db, db

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["POKEMON_DB_PATH"] = db_path
    application = create_app(testing=True)
    with application.app_context():
        init_db()
    yield application
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()
