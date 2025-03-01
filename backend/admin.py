from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from backend.models import db, Admin, AssistantFunction, SystemConfig, Usage
from datetime import datetime
import json

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'admin.login'

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

@admin_bp.app_template_filter('datetime')
def format_datetime(value):
    if value is None:
        return ""
    return value.strftime('%d/%m/%Y %H:%M')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
            
        flash('Usuário ou senha inválidos', 'error')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@login_required
def dashboard():
    # Estatísticas para o dashboard
    functions = AssistantFunction.query.all()
    usage_stats = Usage.query.order_by(Usage.timestamp.desc()).limit(10).all()
    
    # Cálculo de métricas
    total_usage = Usage.query.count()
    success_count = Usage.query.filter_by(success=True).count()
    success_rate = success_count / total_usage if total_usage > 0 else 0
    
    avg_response_time = db.session.query(db.func.avg(Usage.response_time)).scalar() or 0
    
    return render_template('admin/dashboard.html',
                         functions=functions,
                         usage_stats=usage_stats,
                         total_usage=total_usage,
                         success_rate=success_rate,
                         avg_response_time=avg_response_time)

@admin_bp.route('/functions')
@login_required
def manage_functions():
    functions = AssistantFunction.query.all()
    return render_template('admin/functions.html', functions=functions)

@admin_bp.route('/functions/create', methods=['POST'])
@login_required
def create_function():
    data = request.get_json()
    
    try:
        function = AssistantFunction(
            name=data['name'],
            description=data['description'],
            parameters=data['parameters'],
            api_key=data['api_key'],
            endpoint=data['endpoint'],
            is_active=True
        )
        
        db.session.add(function)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/functions/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def function_operations(id):
    function = AssistantFunction.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify({
            'name': function.name,
            'description': function.description,
            'parameters': function.parameters,
            'api_key': function.api_key,
            'endpoint': function.endpoint,
            'is_active': function.is_active
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        try:
            if 'is_active' in data:
                function.is_active = data['is_active']
            else:
                function.name = data['name']
                function.description = data['description']
                function.parameters = data['parameters']
                function.api_key = data['api_key']
                function.endpoint = data['endpoint']
            
            function.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(function)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/config', methods=['GET', 'POST'])
@login_required
def system_config():
    if request.method == 'POST':
        try:
            # Atualiza as configurações
            config = SystemConfig.query.first()
            if not config:
                config = SystemConfig()
                db.session.add(config)
            
            config.openai_api_key = request.form.get('openai_api_key')
            config.amadeus_api_key = request.form.get('amadeus_api_key')
            config.amadeus_api_secret = request.form.get('amadeus_api_secret')
            config.max_tokens = int(request.form.get('max_tokens', 2000))
            config.temperature = float(request.form.get('temperature', 0.7))
            
            db.session.commit()
            flash('Configurações atualizadas com sucesso!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar configurações: {str(e)}', 'error')
    
    # Carrega as configurações atuais
    config = SystemConfig.query.first()
    if not config:
        config = {}
    
    return render_template('admin/system_config.html', config=config)

@admin_bp.route('/stats')
@login_required
def usage_stats():
    # Estatísticas gerais
    total_requests = Usage.query.count()
    success_count = Usage.query.filter_by(success=True).count()
    success_rate = success_count / total_requests if total_requests > 0 else 0
    avg_response_time = db.session.query(db.func.avg(Usage.response_time)).scalar() or 0
    unique_users = db.session.query(db.func.count(db.distinct(Usage.user_id))).scalar() or 0
    
    # Histórico de uso (últimos 100 registros)
    usage_history = Usage.query.order_by(Usage.timestamp.desc()).limit(100).all()
    
    return render_template('admin/usage_stats.html',
                         total_requests=total_requests,
                         success_rate=success_rate,
                         avg_response_time=avg_response_time,
                         unique_users=unique_users,
                         usage_history=usage_history)

@admin_bp.route('/usage')
@login_required
def usage():
    # Estatísticas gerais
    total_usage = Usage.query.count()
    success_rate = Usage.query.filter_by(success=True).count() / total_usage if total_usage > 0 else 0
    avg_response_time = db.session.query(db.func.avg(Usage.response_time)).scalar() or 0
    
    # Uso por função
    function_usage = db.session.query(
        AssistantFunction.name,
        db.func.count(Usage.id).label('count'),
        db.func.avg(Usage.response_time).label('avg_time')
    ).join(Usage).group_by(AssistantFunction.name).all()
    
    # Histórico recente
    recent_usage = Usage.query.order_by(Usage.timestamp.desc()).limit(50).all()
    
    return render_template('admin/usage.html',
                         total_usage=total_usage,
                         success_rate=success_rate,
                         avg_response_time=avg_response_time,
                         function_usage=function_usage,
                         recent_usage=recent_usage)

def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Acesso não autorizado'}), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@admin_bp.route('/api/stats')
@admin_required
def get_stats():
    total_users = Admin.query.count()
    active_subscriptions = Admin.query.filter(
        Admin.subscription_end >= datetime.utcnow()
    ).count()
    
    # Estatísticas de uso por feature
    usage_stats = db.session.query(
        Usage.function,
        db.func.count(Usage.id)
    ).group_by(Usage.function).all()
    
    # Histórico de pagamentos
    recent_payments = Usage.query.filter_by(
        success=True
    ).order_by(Usage.timestamp.desc()).limit(10).all()
    
    return jsonify({
        'total_users': total_users,
        'active_subscriptions': active_subscriptions,
        'usage_stats': dict(usage_stats),
        'recent_payments': [{
            'user_email': payment.user_id,
            'amount': payment.response_time,
            'date': payment.timestamp.isoformat()
        } for payment in recent_payments]
    })

@admin_bp.route('/api/users')
@admin_required
def get_users():
    users = Admin.query.all()
    return jsonify([{
        'id': user.id,
        'email': user.username,
        'subscription_active': user.subscription_end >= datetime.utcnow(),
        'subscription_end': user.subscription_end.isoformat() if user.subscription_end else None,
        'free_uses_remaining': 0,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    } for user in users])

@admin_bp.route('/api/user/<int:user_id>/subscription', methods=['POST'])
@admin_required
def update_user_subscription(user_id):
    user = Admin.query.get_or_404(user_id)
    data = request.get_json()
    
    if data.get('action') == 'activate':
        duration = data.get('duration', 30)
        user.subscription_end = datetime.utcnow() + datetime.timedelta(days=duration)
        message = f'Assinatura ativada por {duration} dias'
    elif data.get('action') == 'deactivate':
        user.subscription_end = None
        message = 'Assinatura desativada'
    else:
        return jsonify({'error': 'Ação inválida'}), 400
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': message})

@admin_bp.route('/api/user/<int:user_id>/usage')
@admin_required
def get_user_usage(user_id):
    user = Admin.query.get_or_404(user_id)
    usage = Usage.query.filter_by(user_id=user.id)\
        .order_by(Usage.timestamp.desc())\
        .limit(50)\
        .all()
    
    return jsonify([{
        'feature': item.function,
        'timestamp': item.timestamp.isoformat(),
        'query': item.query,
        'response': item.response
    } for item in usage])
