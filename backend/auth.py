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
    
    if not data or not data.get('event') or not data.get('data'):
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
    
    event_data = data['data']
    user_email = event_data.get('customer', {}).get('email')
    
    if not user_email:
        return jsonify({'success': False, 'error': 'Email do usuário não encontrado'}), 400
    
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
    
    webhook = KiwifyWebhook(
        user_id=user.id,
        event_type=data['event'],
        subscription_id=event_data.get('subscription_id'),
        payment_status=event_data.get('status'),
        payment_method=event_data.get('payment_method'),
        payment_date=datetime.fromisoformat(event_data.get('payment_date')) if event_data.get('payment_date') else None,
        amount=float(event_data.get('amount', 0)) / 100,  # Kiwify envia em centavos
        next_payment_date=datetime.fromisoformat(event_data.get('next_payment_date')) if event_data.get('next_payment_date') else None,
        refund_reason=event_data.get('refund_reason'),
        chargeback_reason=event_data.get('chargeback_reason')
    )
    
    db.session.add(webhook)
    
    # Processar diferentes eventos
    event = data['event']
    
    if event == 'subscription.renewed' or event == 'compra.aprovada':
        user.activate_subscription()
        
        # Agendar email de lembrete 5 dias antes do vencimento
        if webhook.next_payment_date:
            reminder_date = webhook.next_payment_date - timedelta(days=5)
            if reminder_date > datetime.utcnow():
                # TODO: Implementar sistema de agendamento (Celery/Redis)
                pass
    
    elif event == 'subscription.canceled':
        user.deactivate_subscription()
        send_subscription_canceled_email(user_email)
    
    elif event == 'compra.recusada' or event == 'assinatura.atrasada':
        user.deactivate_subscription()
        send_payment_failed_email(user_email)
    
    elif event == 'subscription.refunded' or event == 'chargeback':
        user.deactivate_subscription()
        send_chargeback_notification_email(user_email)
        # Você pode adicionar lógica adicional aqui, como marcar o usuário para revisão
    
    elif event == 'carrinho.abandonado':
        send_abandoned_cart_email(user_email)
    
    elif event in ['boleto.gerado', 'pix.gerado']:
        # Pagamento pendente - não faz nada até confirmar
        pass
    
    db.session.commit()
    
    return jsonify({'success': True})
