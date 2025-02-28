from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuração
    app.config['SECRET_KEY'] = 'dev'  # será substituído pelo valor do Render
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicialização das extensões
    db.init_app(app)
    login_manager.init_app(app)
    CORS(app)

    # Criação das tabelas
    with app.app_context():
        db.create_all()

    return app
