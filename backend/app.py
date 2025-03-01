from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import hmac
import hashlib
from os import environ

app = Flask(__name__)
app.config['SECRET_KEY'] = environ.get('SECRET_KEY', 'dev_key_change_this')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
CORS(app, supports_credentials=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    usage_count = db.Column(db.Integer, default=0)
    subscription_active = db.Column(db.Boolean, default=False)
    subscription_expiry = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def check_subscription(self):
        if not self.subscription_active:
            return False
        if self.subscription_expiry and self.subscription_expiry < datetime.utcnow():
            self.subscription_active = False
            db.session.commit()
            return False
        return True

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email já cadastrado'}), 400

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({
        'message': 'Usuário registrado com sucesso',
        'user_id': user.id,
        'email': user.email
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user_id': user.id,
            'email': user.email,
            'subscription_active': user.check_subscription()
        })

    return jsonify({'error': 'Email ou senha inválidos'}), 401

@app.route('/api/logout')
def logout():
    logout_user()
    return jsonify({'message': 'Logout realizado com sucesso'})

@app.route('/api/check_auth')
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user_id': current_user.id,
            'email': current_user.email,
            'subscription_active': current_user.check_subscription()
        })
    return jsonify({'authenticated': False})

def verify_kiwify_signature(payload, signature):
    """Verifica a assinatura do webhook da Kiwify"""
    if not signature:
        return False
    
    webhook_secret = environ.get('KIWIFY_WEBHOOK_SECRET', 'yfpccex6uk4')
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

@app.route('/webhook/kiwify', methods=['POST'])
def kiwify_webhook():
    # Verificar a assinatura do webhook
    payload = request.get_data()
    signature = request.headers.get('X-Kiwify-Signature')
    
    if not verify_kiwify_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.json
    
    if data.get('event') == 'order.paid':
        # Extrair email do cliente do payload
        customer_email = data.get('customer', {}).get('email')
        if customer_email:
            user = User.query.filter_by(email=customer_email).first()
            if user:
                user.subscription_active = True
                user.subscription_expiry = datetime.utcnow() + timedelta(days=30)
                db.session.commit()
                
                # Log para debug
                print(f"Assinatura ativada para o usuário: {customer_email}")
            else:
                print(f"Usuário não encontrado: {customer_email}")
    
    return jsonify({'status': 'success'})

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='../frontend')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure OpenAI
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    logger.error("OpenAI API key not found!")
    raise ValueError("OpenAI API key not found in environment variables")

openai.api_key = api_key

def chatgpt_interaction(prompt, system_message=None):
    try:
        if system_message is None:
            system_message = "Você é um assistente de viagem profissional, especializado em dar informações precisas e úteis sobre destinos, roteiros, documentação e dicas de viagem. Seja sempre claro e organizado em suas respostas."
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message['content'].strip()
    except Exception as e:
        logger.error(f"Error in chatgpt_interaction: {str(e)}")
        raise

# Variável global para contar usos por IP
free_usage_count = {}

def get_client_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR']
    return request.remote_addr

def check_usage_limit():
    ip = get_client_ip()
    count = free_usage_count.get(ip, 0)
    if count >= 3:
        return True
    free_usage_count[ip] = count + 1
    return False

@app.route('/api/check_usage', methods=['GET'])
def check_usage():
    ip = get_client_ip()
    count = free_usage_count.get(ip, 0)
    return jsonify({
        'uses_remaining': max(3 - count, 0),
        'requires_login': count >= 3
    })

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/health')
def health_check():
    logger.info("Health check endpoint called")
    return jsonify({
        "status": "ok",
        "message": "Server is running",
        "environment": {
            "OPENAI_API_KEY": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
            "PORT": os.getenv('PORT', '5000')
        }
    })

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    if check_usage_limit():
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'login_required',
                'message': 'Você atingiu o limite de 3 usos gratuitos. Por favor, faça login para continuar.'
            })
        if not current_user.check_subscription():
            return jsonify({
                'success': False,
                'error': 'subscription_required',
                'message': 'Você precisa de uma assinatura ativa para continuar usando o assistente.'
            })

    try:
        data = request.json
        user_id = current_user.id
        user_message = data.get('message')
        response = chatgpt_interaction(user_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/roteiro', methods=['POST'])
@login_required
def get_roteiro():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        destino = data.get('destino')
        dias = data.get('dias')
        system_message = """Você é um especialista em roteiros de viagem. Formate sua resposta de forma clara e organizada:
        - Comece com uma breve introdução sobre o destino
        - Divida o roteiro por dias
        - Use pontos para atividades dentro de cada dia
        - Inclua horários e preços estimados entre parênteses
        - Use emojis para diferentes tipos de atividades (🏛️ pontos turísticos, 🍴 comida, etc.)
        - Adicione dicas de viagem no final
        - Mantenha parágrafos curtos e focados
        - Use negrito para informações importantes"""
        
        prompt = f"Crie um roteiro detalhado para {dias} dias em {destino}, incluindo atrações turísticas, preços estimados e horários sugeridos."
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/precos', methods=['POST'])
@login_required
def get_precos():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        destino = data.get('destino')
        system_message = """Formate sua resposta com seções claras:
        - Comece com um resumo dos custos totais estimados
        - Divida os custos por categoria (alojamento, comida, transporte, etc.)
        - Use pontos para detalhes
        - Inclua faixas de preços em negrito
        - Adicione dicas para economizar dinheiro no final
        - Use emojis para diferentes categorias
        - Apresente comparações de preços em tabelas quando relevante"""
        
        prompt = f"Quanto custa uma viagem para {destino} em um estilo de preço intermediário em reais?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/checklist', methods=['POST'])
@login_required
def get_checklist():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        destino = data.get('destino')
        system_message = """Formate sua resposta de checklist de forma clara:
        - Organize itens por categoria
        - Use pontos para todos os itens
        - Negrite itens essenciais
        - Adicione explicações breves entre parênteses quando necessário
        - Use emojis para diferentes categorias
        - Inclua recomendações específicas para o destino
        - Adicione dicas para empacotar de forma eficiente"""
        
        prompt = f"Quais itens devo levar em uma viagem para {destino}?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/gastronomia', methods=['POST'])
@login_required
def get_gastronomia():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        destino = data.get('destino')
        tipo = data.get('tipo', 'intermediária')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre a culinária local
        - Divida recomendações por categoria (restaurantes, cafés, etc.)
        - Use pontos para detalhes
        - Inclua faixas de preços em negrito
        - Adicione dicas para jantar no final
        - Use emojis para diferentes categorias
        - Apresente comparações em tabelas quando relevante"""
        
        prompt = f"Quais são os melhores restaurantes em {destino} para um orçamento {tipo}? Liste os pratos típicos e preços médios em reais."
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/documentacao', methods=['POST'])
@login_required
def get_documentacao():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        destino = data.get('destino')
        origem = data.get('origem')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre o destino
        - Divida requisitos por categoria (visto, passaporte, etc.)
        - Use pontos para detalhes
        - Inclua prazos e taxas importantes em negrito
        - Adicione dicas para o processo de solicitação no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Quais os requisitos de visto para uma pessoa de {origem} visitar {destino}?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/trem', methods=['POST'])
@login_required
def get_trem():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        destinos = data.get('destinos')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre a rota de trem
        - Divida o itinerário por dias
        - Use pontos para atividades dentro de cada dia
        - Inclua horários e preços estimados entre parênteses
        - Use emojis para diferentes tipos de atividades (🚂 trem, 🏛️ pontos turísticos, etc.)
        - Adicione dicas de viagem no final
        - Mantenha parágrafos curtos e focados
        - Use negrito para informações importantes"""
        
        prompt = f"Crie um roteiro por {destinos} de trem com a rota mais viável, com 2 dias em cada cidade, com tempo de viagem entre as cidades e o nome das estações. No final, fale qual passe de trem utilizar e preço médio em reais."
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/guia', methods=['POST'])
@login_required
def get_guia():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        local = data.get('local')
        tempo = data.get('tempo')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre o destino
        - Divida recomendações por categoria (pontos turísticos, atividades, etc.)
        - Use pontos para detalhes
        - Inclua horários e preços estimados entre parênteses
        - Use emojis para diferentes tipos de atividades (🏛️ pontos turísticos, 🍴 comida, etc.)
        - Adicione dicas para a visita no final
        - Mantenha parágrafos curtos e focados
        - Use negrito para informações importantes"""
        
        prompt = f"Quais passeios posso fazer em {local} em {tempo}?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/festivais', methods=['POST'])
@login_required
def get_festivais():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        cidade = data.get('cidade')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre os festivais
        - Divida recomendações por categoria (música, comida, etc.)
        - Use pontos para detalhes
        - Inclua datas e preços em negrito
        - Adicione dicas para participar dos festivais no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Quais são os principais festivais e eventos acontecendo em {cidade} nos próximos meses?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/hospedagem', methods=['POST'])
@login_required
def get_hospedagem():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        cidade = data.get('cidade')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre as acomodações
        - Divida recomendações por categoria (hotéis, pousadas, etc.)
        - Use pontos para detalhes
        - Inclua faixas de preços em negrito
        - Adicione dicas para reservar no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Quais são as melhores áreas para se hospedar em {cidade}, considerando diferentes perfis de viagem?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/historias', methods=['POST'])
@login_required
def get_historias():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        cidade = data.get('cidade')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre a cidade
        - Divida histórias por categoria (história, cultura, etc.)
        - Use pontos para detalhes
        - Inclua fatos interessantes e anedotas
        - Adicione dicas para explorar a cidade no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Conte histórias e curiosidades interessantes sobre {cidade}."
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/frases', methods=['POST'])
@login_required
def get_frases():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        idioma = data.get('idioma')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre o idioma
        - Divida frases por categoria (cumprimentos, direções, etc.)
        - Use pontos para detalhes
        - Inclua guias de pronúncia e exemplos
        - Adicione dicas para comunicação no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Quais são as frases mais úteis para um turista em {idioma}?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/seguranca', methods=['POST'])
@login_required
def get_seguranca():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        cidade = data.get('cidade')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre a segurança na cidade
        - Divida dicas por categoria (crime, saúde, etc.)
        - Use pontos para detalhes
        - Inclua números importantes e recursos
        - Adicione conselhos gerais para ficar seguro no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Quais são as principais dicas de segurança para turistas em {cidade}?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/hospitais', methods=['POST'])
@login_required
def get_hospitais():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        cidade = data.get('cidade')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre os cuidados médicos na cidade
        - Divida recomendações por categoria (hospitais, clínicas, etc.)
        - Use pontos para detalhes
        - Inclua endereços, números de telefone e horários de funcionamento
        - Adicione dicas para emergências médicas no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Quais são os hospitais mais próximos e bem avaliados em {cidade}?"
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/consulados', methods=['POST'])
@login_required
def get_consulados():
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            return jsonify({
                'subscription_required': True,
                'message': 'Assinatura necessária'
            }), 402
        
        cidade = data.get('cidade')
        system_message = """Formate sua resposta com seções claras:
        - Comece com uma breve introdução sobre o consulado
        - Divida informações por categoria (horários, contato, etc.)
        - Use pontos para detalhes
        - Inclua endereços, números de telefone e e-mail
        - Adicione dicas para entrar em contato com o consulado no final
        - Use emojis para diferentes categorias"""
        
        prompt = f"Onde fica o consulado Brasileiro em {cidade}? Me informa detalhes de como entrar em contato e endereço e como agir em caso de problemas."
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def record_usage(user_id, endpoint):
    if user_id:
        user = User.query.get(user_id)
        if user:
            user.usage_count += 1
            usage = Usage(user_id=user_id, endpoint=endpoint)
            db.session.add(usage)
            db.session.commit()

@app.before_request
def check_subscription_status():
    if current_user.is_authenticated:
        current_user.check_subscription()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
