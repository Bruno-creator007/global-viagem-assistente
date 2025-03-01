from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User, KiwifyWebhook
from .notifications import (
    send_abandoned_cart_email,
    send_subscription_expiring_email,
    send_payment_failed_email,
    send_chargeback_notification_email,
    send_subscription_canceled_email
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400
        
    user = User(email=data['email'])
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    
    return jsonify({
        'success': True,
        'user_id': user.id,
        'email': user.email,
        'subscription_active': user.check_subscription()
    })

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
    user = User.query.filter_by(email=data['email']).first()
    
    if user and user.check_password(data['password']):
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user_id': user.id,
            'email': user.email,
            'subscription_active': user.check_subscription()
        })
    
    return jsonify({'success': False, 'error': 'Email ou senha inválidos'}), 401

@auth_bp.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True})

@auth_bp.route('/api/check_auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user_id': current_user.id,
            'email': current_user.email,
            'subscription_active': current_user.check_subscription(),
            'free_uses_remaining': current_user.free_uses_remaining
        })
    return jsonify({
        'authenticated': False,
        'subscription_active': False,
        'free_uses_remaining': 3
    })

@auth_bp.route('/webhook/kiwify', methods=['POST'])
def kiwify_webhook():
    # Verificar token do webhook
    webhook_token = request.headers.get('X-Kiwify-Token')
    if not webhook_token or webhook_token != 'yfpccex6uk4':
        return jsonify({'success': False, 'error': 'Token inválido'}), 401

    data = request.get_json()
    
    if not data or not data.get('order'):
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
    
    order_data = data['order']
    customer_data = order_data.get('Customer', {})
    subscription_data = order_data.get('Subscription', {})
    
    user_email = customer_data.get('email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Email do usuário não encontrado'}), 400
    
    user = User.query.filter_by(email=user_email).first()
    if not user:
        # Criar usuário se não existir
        user = User(
            email=user_email,
            name=customer_data.get('full_name'),
            subscription_active=False
        )
        db.session.add(user)
    
    webhook = KiwifyWebhook(
        user_id=user.id,
        event_type=order_data.get('webhook_event_type'),
        subscription_id=subscription_data.get('subscription_id'),
        payment_status=order_data.get('order_status'),
        payment_method=order_data.get('payment_method'),
        payment_date=datetime.strptime(order_data.get('approved_date', ''), '%Y-%m-%d %H:%M') if order_data.get('approved_date') else None,
        amount=float(order_data.get('Commissions', {}).get('charge_amount', 0)) / 100,
        next_payment_date=datetime.fromisoformat(subscription_data.get('next_payment').replace('Z', '+00:00')) if subscription_data.get('next_payment') else None,
        refund_reason=None,
        chargeback_reason=None
    )
    
    db.session.add(webhook)
    
    # Processar diferentes eventos
    event_type = order_data.get('webhook_event_type')
    order_status = order_data.get('order_status')
    subscription_status = subscription_data.get('status')
    
    if order_status == 'paid' and subscription_status == 'active':
        user.activate_subscription()
        
        # Agendar email de lembrete 5 dias antes do vencimento
        if webhook.next_payment_date:
            reminder_date = webhook.next_payment_date - timedelta(days=5)
            if reminder_date > datetime.utcnow():
                # TODO: Implementar sistema de agendamento (Celery/Redis)
                pass
    
    elif order_status == 'refunded' or order_status == 'chargeback':
        user.deactivate_subscription()
        send_chargeback_notification_email(user_email)
    
    elif event_type == 'pix_created':
        # Pagamento PIX pendente
        pass
    
    elif event_type == 'subscription_canceled':
        user.deactivate_subscription()
        send_subscription_canceled_email(user_email)
    
    db.session.commit()
    
    return jsonify({'success': True})
