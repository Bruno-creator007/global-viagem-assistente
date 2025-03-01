from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subscription_start = db.Column(db.DateTime)
    subscription_end = db.Column(db.DateTime)
    free_uses_remaining = db.Column(db.Integer, default=3)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    usage_history = db.relationship('UsageHistory', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def check_subscription(self):
        if not self.subscription_end:
            return False
        return datetime.utcnow() <= self.subscription_end

    def activate_subscription(self, duration_days=30):
        now = datetime.utcnow()
        self.subscription_start = now
        self.subscription_end = now + timedelta(days=duration_days)
        db.session.commit()

    def deactivate_subscription(self):
        self.subscription_end = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()

    def use_free_trial(self):
        if self.free_uses_remaining > 0:
            self.free_uses_remaining -= 1
            db.session.commit()
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
    payment_method = db.Column(db.String(20))  # pix, boleto, cartao
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    payment_date = db.Column(db.DateTime)
    amount = db.Column(db.Float)
    next_payment_date = db.Column(db.DateTime)
    refund_reason = db.Column(db.String(200))
    chargeback_reason = db.Column(db.String(200))
