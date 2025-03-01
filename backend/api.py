from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from .models import db, User, UsageHistory
import openai
import os

api_bp = Blueprint('api', __name__)

def check_access():
    """Verifica se o usuário tem acesso às funcionalidades"""
    if not current_user.is_authenticated:
        return False, "Faça login para continuar"
    
    if current_user.check_subscription():
        return True, None
        
    if current_user.free_uses_remaining > 0:
        return True, None
        
    return False, "Assine o plano para continuar usando"

def log_usage(feature, query, response):
    """Registra o uso da funcionalidade"""
    if current_user.is_authenticated:
        usage = UsageHistory(
            user_id=current_user.id,
            feature=feature,
            query=query,
            response=response
        )
        db.session.add(usage)
        
        if not current_user.check_subscription():
            current_user.use_free_trial()
            
        db.session.commit()

def get_ai_response(prompt, feature):
    """Obtém resposta da API do OpenAI"""
    try:
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        # Adiciona contexto específico para cada feature
        feature_context = {
            'roteiro': "Você é um especialista em criar roteiros de viagem. ",
            'trem': "Você é um especialista em viagens de trem pela Europa. ",
            'precos': "Você é um especialista em custos de viagem. ",
            'checklist': "Você é um especialista em preparação para viagens. ",
            'gastronomia': "Você é um chef especialista em gastronomia mundial. ",
            'documentacao': "Você é um especialista em documentação para viagens. ",
            'guia': "Você é um guia turístico local experiente. ",
            'festivais': "Você é um especialista em eventos e festivais. ",
            'hospedagem': "Você é um especialista em hospedagem. ",
            'historias': "Você é um historiador e conhecedor de curiosidades. ",
            'frases': "Você é um professor de idiomas. ",
            'seguranca': "Você é um especialista em segurança para viajantes. ",
            'hospitais': "Você é um especialista em saúde para viajantes. ",
            'consulados': "Você é um especialista em serviços consulares. "
        }
        
        system_prompt = feature_context.get(feature, "") + "Forneça informações precisas e úteis."
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message['content']
    except Exception as e:
        print(f"Erro na API OpenAI: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente."

@api_bp.route('/api/feature/<feature>', methods=['POST'])
def handle_feature(feature):
    # Verifica acesso
    has_access, error_message = check_access()
    if not has_access:
        return jsonify({
            'success': False,
            'error': error_message
        }), 403
    
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({
            'success': False,
            'error': 'Mensagem não fornecida'
        }), 400
    
    # Obtém resposta da IA
    response = get_ai_response(data['message'], feature)
    
    # Registra uso
    log_usage(feature, data['message'], response)
    
    return jsonify({
        'success': True,
        'response': response
    })

@api_bp.route('/api/user/usage')
@login_required
def get_user_usage():
    usage = UsageHistory.query.filter_by(user_id=current_user.id)\
        .order_by(UsageHistory.timestamp.desc())\
        .limit(50)\
        .all()
    
    return jsonify({
        'success': True,
        'usage': [{
            'feature': item.feature,
            'timestamp': item.timestamp.isoformat(),
            'query': item.query
        } for item in usage]
    })
