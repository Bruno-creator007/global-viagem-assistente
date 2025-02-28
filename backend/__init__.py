from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    CORS(app)

    from .admin import admin_bp
    app.register_blueprint(admin_bp)

    from .travel_api import travel_bp
    app.register_blueprint(travel_bp)

    return app
