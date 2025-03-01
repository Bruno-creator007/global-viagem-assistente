import os
from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from flask_mail import Mail
from .models import db, User
from .notifications import mail

login_manager = LoginManager()

def create_app(config=None):
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    
    # Configurações padrão
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')
    
    # Configurações de email
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    if config:
        app.config.update(config)
    
    # Inicialização das extensões
    CORS(app, supports_credentials=True)
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configuração do Login Manager
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Criar todas as tabelas
    with app.app_context():
        db.create_all()
        
        # Criar usuário admin se não existir
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_email and admin_password:
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(email=admin_email, is_admin=True)
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
    
    # Registrar blueprints
    from .auth import auth_bp
    from .api import api_bp
    from .admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    
    return app
