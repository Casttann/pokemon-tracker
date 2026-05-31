import os
from flask import Flask
from database import db

def create_app(testing=False):
    app = Flask(__name__)
    db_path = os.environ.get("POKEMON_DB_PATH",
                             os.path.expanduser("~/.pokemon_tracker/tracker.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = testing
    db.init_app(app)
    return app
