from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os
import hmac
import hashlib
from datetime import datetime, timedelta
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configuração do Flask
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configuração do banco de dados
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'sua_chave_secreta')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração dos arquivos estáticos
static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
app.static_folder = static_folder
app.static_url_path = ''

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

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
    logger.info("Recebida solicitação de registro")
    
    data = request.json
    logger.info(f"Dados recebidos: {data}")
    
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        logger.error("Email e senha não fornecidos")
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400

    if User.query.filter_by(email=email).first():
        logger.error("Email já cadastrado")
        return jsonify({'error': 'Email já cadastrado'}), 400

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    logger.info("Usuário registrado com sucesso")
    
    return jsonify({
        'message': 'Usuário registrado com sucesso',
        'user_id': user.id,
        'email': user.email
    })

@app.route('/api/login', methods=['POST'])
def login():
    logger.info("Recebida solicitação de login")
    
    data = request.json
    logger.info(f"Dados recebidos: {data}")
    
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        logger.info("Login realizado com sucesso")
        
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user_id': user.id,
            'email': user.email,
            'subscription_active': user.check_subscription()
        })

    logger.error("Email ou senha inválidos")
    return jsonify({'error': 'Email ou senha inválidos'}), 401

@app.route('/api/logout')
def logout():
    logout_user()
    logger.info("Logout realizado com sucesso")
    
    return jsonify({'message': 'Logout realizado com sucesso'})

@app.route('/')
def index():
    logger.info("Recebida solicitação para página inicial")
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    logger.info(f"Recebida solicitação para arquivo estático: {path}")
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/check_usage')
def check_usage():
    ip = get_client_ip()
    count = free_usage_count.get(ip, 0)
    logger.info(f"Verificando uso para IP {ip}: {count} usos")
    return jsonify({
        'uses_remaining': max(3 - count, 0),
        'requires_login': count >= 3
    })

@app.route('/api/check_auth')
def check_auth():
    if current_user.is_authenticated:
        subscription_active = current_user.check_subscription()
        return jsonify({
            'authenticated': True,
            'user_id': current_user.id,
            'email': current_user.email,
            'subscription_active': subscription_active
        })
    return jsonify({
        'authenticated': False,
        'subscription_active': False
    })

def chatgpt_interaction(message, system_message="Você é um assistente de viagem especializado."):
    try:
        logger.info(f"Iniciando interação com ChatGPT. Mensagem: {message}")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ],
            max_tokens=1000
        )
        result = response.choices[0].message['content'].strip()
        logger.info("Resposta do ChatGPT gerada com sucesso")
        return result
    except Exception as e:
        logger.error(f"Erro na interação com ChatGPT: {str(e)}", exc_info=True)
        raise

@app.route('/api/roteiro', methods=['POST'])
def roteiro():
    logger.info("Recebida solicitação de roteiro")
    
    # Verificar limite de uso gratuito
    ip = get_client_ip()
    count = free_usage_count.get(ip, 0)
    
    if count >= 3 and not current_user.is_authenticated:
        logger.warning(f"IP {ip} excedeu limite de uso gratuito")
        return jsonify({
            'error': 'login_required',
            'message': 'Por favor, faça login para continuar usando o assistente'
        }), 401

    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    message = data.get('message')
    
    if not message:
        logger.error("Mensagem não fornecida")
        return jsonify({'error': 'Message is required'}), 400

    try:
        # Incrementar contador de uso gratuito
        if not current_user.is_authenticated:
            free_usage_count[ip] = count + 1
            logger.info(f"Incrementado uso gratuito para IP {ip}: {free_usage_count[ip]}")

        # Extrair destino e dias da mensagem
        parts = message.lower().split()
        destino = parts[0]
        dias = next((p for p in parts if p.isdigit()), '3')
        
        prompt = f"Crie um roteiro detalhado para {dias} dias em {destino}, incluindo atrações turísticas, preços estimados e horários sugeridos."
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao gerar roteiro: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/festivais', methods=['POST'])
def festivais():
    logger.info("Recebida solicitação de festivais")
    
    # Verificar limite de uso gratuito
    ip = get_client_ip()
    count = free_usage_count.get(ip, 0)
    
    if count >= 3 and not current_user.is_authenticated:
        logger.warning(f"IP {ip} excedeu limite de uso gratuito")
        return jsonify({
            'error': 'login_required',
            'message': 'Por favor, faça login para continuar usando o assistente'
        }), 401

    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    message = data.get('message')
    
    if not message:
        logger.error("Mensagem não fornecida")
        return jsonify({'error': 'Message is required'}), 400

    try:
        # Incrementar contador de uso gratuito
        if not current_user.is_authenticated:
            free_usage_count[ip] = count + 1
            logger.info(f"Incrementado uso gratuito para IP {ip}: {free_usage_count[ip]}")

        prompt = f"Liste os principais festivais, eventos culturais e celebrações que acontecem em {message} ao longo do ano. Inclua datas aproximadas, descrições e dicas para participar."
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao buscar festivais: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/<feature>', methods=['POST'])
def handle_feature(feature):
    logger.info(f"Recebida solicitação para feature: {feature}")
    
    # Verificar limite de uso gratuito
    ip = get_client_ip()
    count = free_usage_count.get(ip, 0)
    
    if count >= 3 and not current_user.is_authenticated:
        logger.warning(f"IP {ip} excedeu limite de uso gratuito")
        return jsonify({
            'error': 'login_required',
            'message': 'Por favor, faça login para continuar usando o assistente'
        }), 401

    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    message = data.get('message')
    
    if not message:
        logger.error("Mensagem não fornecida")
        return jsonify({'error': 'Message is required'}), 400

    # Mapear features para prompts específicos
    feature_prompts = {
        'precos': f"Quanto custa uma viagem para {message} em um estilo de preço intermediário em reais?",
        'checklist': f"Quais itens devo levar em uma viagem para {message}?",
        'gastronomia': f"Quais são os melhores restaurantes e pratos típicos em {message}? Liste os pratos típicos e preços médios em reais.",
        'documentacao': f"Quais são os requisitos de documentação e visto para visitar {message}?",
        'guia': f"Crie um guia completo de {message}, incluindo principais atrações, dicas locais e informações práticas.",
        'hospedagem': f"Quais são as melhores áreas para se hospedar em {message}, considerando diferentes perfis de viagem?",
        'historias': f"Conte histórias e curiosidades interessantes sobre {message}.",
        'frases': f"Quais são as frases mais úteis para um turista em {message}?",
        'seguranca': f"Quais são as principais dicas de segurança para turistas em {message}?",
        'hospitais': f"Quais são os hospitais mais próximos e bem avaliados em {message}?",
        'consulados': f"Onde fica o consulado Brasileiro em {message}? Me informa detalhes de como entrar em contato e endereço e como agir em caso de problemas."
    }

    if feature not in feature_prompts:
        logger.error(f"Feature não suportada: {feature}")
        return jsonify({'error': 'Feature not supported'}), 400

    try:
        # Incrementar contador de uso gratuito
        if not current_user.is_authenticated:
            free_usage_count[ip] = count + 1
            logger.info(f"Incrementado uso gratuito para IP {ip}: {free_usage_count[ip]}")

        prompt = feature_prompts[feature]
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    logger.info("Recebida solicitação de chat")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    message = data.get('message')
    
    if not message:
        logger.error("Mensagem não fornecida")
        return jsonify({'error': 'Message is required'}), 400

    try:
        response = chatgpt_interaction(message)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/roteiro', methods=['POST'])
@login_required
def get_roteiro():
    logger.info("Recebida solicitação de roteiro")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    destino = data.get('destino')
    dias = data.get('dias')
    
    if not destino or not dias:
        logger.error("Destino e dias não fornecidos")
        return jsonify({'error': 'Destino e dias são obrigatórios'}), 400

    try:
        prompt = f"Crie um roteiro detalhado para {dias} dias em {destino}, incluindo atrações turísticas, preços estimados e horários sugeridos."
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/precos', methods=['POST'])
@login_required
def get_precos():
    logger.info("Recebida solicitação de preços")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    destino = data.get('destino')
    
    if not destino:
        logger.error("Destino não fornecido")
        return jsonify({'error': 'Destino é obrigatório'}), 400

    try:
        prompt = f"Quanto custa uma viagem para {destino} em um estilo de preço intermediário em reais?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/checklist', methods=['POST'])
@login_required
def get_checklist():
    logger.info("Recebida solicitação de checklist")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    destino = data.get('destino')
    
    if not destino:
        logger.error("Destino não fornecido")
        return jsonify({'error': 'Destino é obrigatório'}), 400

    try:
        prompt = f"Quais itens devo levar em uma viagem para {destino}?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/gastronomia', methods=['POST'])
@login_required
def get_gastronomia():
    logger.info("Recebida solicitação de gastronomia")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    destino = data.get('destino')
    
    if not destino:
        logger.error("Destino não fornecido")
        return jsonify({'error': 'Destino é obrigatório'}), 400

    try:
        prompt = f"Quais são os melhores restaurantes e pratos típicos em {destino}? Liste os pratos típicos e preços médios em reais."
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/documentacao', methods=['POST'])
@login_required
def get_documentacao():
    logger.info("Recebida solicitação de documentação")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    destino = data.get('destino')
    
    if not destino:
        logger.error("Destino não fornecido")
        return jsonify({'error': 'Destino é obrigatório'}), 400

    try:
        prompt = f"Quais são os requisitos de documentação e visto para visitar {destino}?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/trem', methods=['POST'])
@login_required
def get_trem():
    logger.info("Recebida solicitação de trem")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    destinos = data.get('destinos')
    
    if not destinos:
        logger.error("Destinos não fornecidos")
        return jsonify({'error': 'Destinos são obrigatórios'}), 400

    try:
        prompt = f"Crie um roteiro por {destinos} de trem com a rota mais viável, com 2 dias em cada cidade, com tempo de viagem entre as cidades e o nome das estações. No final, fale qual passe de trem utilizar e preço médio em reais."
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/guia', methods=['POST'])
@login_required
def get_guia():
    logger.info("Recebida solicitação de guia")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    local = data.get('local')
    tempo = data.get('tempo')
    
    if not local or not tempo:
        logger.error("Local e tempo não fornecidos")
        return jsonify({'error': 'Local e tempo são obrigatórios'}), 400

    try:
        prompt = f"Quais passeios posso fazer em {local} em {tempo}?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/festivais', methods=['POST'])
@login_required
def get_festivais():
    logger.info("Recebida solicitação de festivais")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    cidade = data.get('cidade')
    
    if not cidade:
        logger.error("Cidade não fornecida")
        return jsonify({'error': 'Cidade é obrigatória'}), 400

    try:
        prompt = f"Quais são os principais festivais e eventos acontecendo em {cidade} nos próximos meses?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/hospedagem', methods=['POST'])
@login_required
def get_hospedagem():
    logger.info("Recebida solicitação de hospedagem")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    cidade = data.get('cidade')
    
    if not cidade:
        logger.error("Cidade não fornecida")
        return jsonify({'error': 'Cidade é obrigatória'}), 400

    try:
        prompt = f"Quais são as melhores áreas para se hospedar em {cidade}, considerando diferentes perfis de viagem?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/historias', methods=['POST'])
@login_required
def get_historias():
    logger.info("Recebida solicitação de histórias")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    cidade = data.get('cidade')
    
    if not cidade:
        logger.error("Cidade não fornecida")
        return jsonify({'error': 'Cidade é obrigatória'}), 400

    try:
        prompt = f"Conte histórias e curiosidades interessantes sobre {cidade}."
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/frases', methods=['POST'])
@login_required
def get_frases():
    logger.info("Recebida solicitação de frases")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    idioma = data.get('idioma')
    
    if not idioma:
        logger.error("Idioma não fornecido")
        return jsonify({'error': 'Idioma é obrigatório'}), 400

    try:
        prompt = f"Quais são as frases mais úteis para um turista em {idioma}?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/seguranca', methods=['POST'])
@login_required
def get_seguranca():
    logger.info("Recebida solicitação de segurança")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    cidade = data.get('cidade')
    
    if not cidade:
        logger.error("Cidade não fornecida")
        return jsonify({'error': 'Cidade é obrigatória'}), 400

    try:
        prompt = f"Quais são as principais dicas de segurança para turistas em {cidade}?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/hospitais', methods=['POST'])
@login_required
def get_hospitais():
    logger.info("Recebida solicitação de hospitais")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    cidade = data.get('cidade')
    
    if not cidade:
        logger.error("Cidade não fornecida")
        return jsonify({'error': 'Cidade é obrigatória'}), 400

    try:
        prompt = f"Quais são os hospitais mais próximos e bem avaliados em {cidade}?"
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/api/consulados', methods=['POST'])
@login_required
def get_consulados():
    logger.info("Recebida solicitação de consulados")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    cidade = data.get('cidade')
    
    if not cidade:
        logger.error("Cidade não fornecida")
        return jsonify({'error': 'Cidade é obrigatória'}), 400

    try:
        prompt = f"Onde fica o consulado Brasileiro em {cidade}? Me informa detalhes de como entrar em contato e endereço e como agir em caso de problemas."
        response = chatgpt_interaction(prompt)
        
        logger.info("Resposta gerada com sucesso")
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

@app.route('/webhook/kiwify', methods=['POST'])
def kiwify_webhook():
    logger.info("Recebida solicitação de webhook Kiwify")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    signature = request.args.get('signature')
    if not signature:
        logger.error("Assinatura não fornecida")
        return jsonify({'error': 'No signature provided'}), 401

    # Verificar a assinatura
    webhook_secret = os.getenv('KIWIFY_WEBHOOK_SECRET', 'yfpccex6uk4')
    expected_signature = hmac.new(
        webhook_secret.encode(),
        request.get_data(),
        hashlib.sha1
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        logger.error("Assinatura inválida")
        return jsonify({'error': 'Invalid signature'}), 401

    data = request.json
    if not data:
        logger.error("Dados não fornecidos")
        return jsonify({'error': 'No data provided'}), 400

    event_type = data.get('event')
    if not event_type:
        logger.error("Tipo de evento não fornecido")
        return jsonify({'error': 'No event type provided'}), 400

    if event_type == 'order.paid':
        try:
            order = data.get('order', {})
            customer = order.get('customer', {})
            customer_email = customer.get('email')
            
            if not customer_email:
                logger.error("Email do cliente não fornecido")
                return jsonify({'error': 'No customer email provided'}), 400

            user = User.query.filter_by(email=customer_email).first()
            if not user:
                logger.error("Usuário não encontrado")
                return jsonify({'error': 'User not found'}), 404

            user.subscription_active = True
            db.session.commit()
            
            logger.info("Assinatura ativada com sucesso")
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {str(e)}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    logger.info("Tipo de evento não suportado")
    
    return jsonify({'success': True})

def get_client_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR']
    return request.remote_addr

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
