from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))
    subscription_active = db.Column(db.Boolean, default=False)
    subscription_id = db.Column(db.String(100))
    free_uses = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def activate_subscription(self):
        self.subscription_active = True
        self.free_uses = 0  # Remove usos gratuitos quando ativa assinatura
    
    def deactivate_subscription(self):
        self.subscription_active = False
        self.subscription_id = None
    
    def can_use_service(self):
        return self.subscription_active or self.free_uses > 0
    
    def use_free_trial(self):
        if self.free_uses > 0:
            self.free_uses -= 1
            return True
        return False

class UsageHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    query = db.Column(db.Text)
    response = db.Column(db.Text)

class KiwifyWebhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    subscription_id = db.Column(db.String(100))
    payment_status = db.Column(db.String(50))
    payment_method = db.Column(db.String(20))  # pix, boleto, credit_card
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    payment_date = db.Column(db.DateTime)
    amount = db.Column(db.Float)
    next_payment_date = db.Column(db.DateTime)
    refund_reason = db.Column(db.String(200))
    chargeback_reason = db.Column(db.String(200))
    
    user = db.relationship('User', backref=db.backref('webhooks', lazy=True))
