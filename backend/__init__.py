from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuração
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    app.config['AMADEUS_API_KEY'] = os.getenv('AMADEUS_API_KEY')
    app.config['AMADEUS_API_SECRET'] = os.getenv('AMADEUS_API_SECRET')

    db.init_app(app)
    login_manager.init_app(app)
    CORS(app)

    from .admin import admin_bp
    app.register_blueprint(admin_bp)

    from .travel_api import travel_bp
    app.register_blueprint(travel_bp)

    return app
