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

app = Flask(__name__, 
    static_url_path='',
    static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend')))

CORS(app, supports_credentials=True)

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'sua_chave_secreta')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

@app.route('/api/check_auth')
def check_auth():
    if current_user.is_authenticated:
        logger.info("Usuário autenticado")
        
        return jsonify({
            'authenticated': True,
            'user_id': current_user.id,
            'email': current_user.email,
            'subscription_active': current_user.check_subscription()
        })
    logger.info("Usuário não autenticado")
    
    return jsonify({'authenticated': False})

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
        
        logger.info("Resposta gerada com sucesso")
        
        return response.choices[0].message['content'].strip()
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
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
    logger.info(f"Verificando uso para IP {ip}")
    
    return jsonify({
        'uses_remaining': max(3 - count, 0),
        'requires_login': count >= 3
    })

@app.route('/')
def index():
    logger.info("Recebida solicitação para página inicial")
    
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    logger.info(f"Recebida solicitação para arquivo estático {path}")
    
    return send_from_directory(app.static_folder, path)

@app.route('/api/health')
def health_check():
    logger.info("Recebida solicitação de verificação de saúde")
    
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
    logger.info("Recebida solicitação de chat")
    
    if check_usage_limit():
        if not current_user.is_authenticated:
            logger.error("Usuário não autenticado")
            return jsonify({
                'success': False,
                'error': 'login_required',
                'message': 'Você atingiu o limite de 3 usos gratuitos. Por favor, faça login para continuar.'
            })
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/roteiro', methods=['POST'])
@login_required
def get_roteiro():
    logger.info("Recebida solicitação de roteiro")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/precos', methods=['POST'])
@login_required
def get_precos():
    logger.info("Recebida solicitação de preços")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/checklist', methods=['POST'])
@login_required
def get_checklist():
    logger.info("Recebida solicitação de checklist")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/gastronomia', methods=['POST'])
@login_required
def get_gastronomia():
    logger.info("Recebida solicitação de gastronomia")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/documentacao', methods=['POST'])
@login_required
def get_documentacao():
    logger.info("Recebida solicitação de documentação")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/trem', methods=['POST'])
@login_required
def get_trem():
    logger.info("Recebida solicitação de trem")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/guia', methods=['POST'])
@login_required
def get_guia():
    logger.info("Recebida solicitação de guia")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/festivais', methods=['POST'])
@login_required
def get_festivais():
    logger.info("Recebida solicitação de festivais")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/hospedagem', methods=['POST'])
@login_required
def get_hospedagem():
    logger.info("Recebida solicitação de hospedagem")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/historias', methods=['POST'])
@login_required
def get_historias():
    logger.info("Recebida solicitação de histórias")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/frases', methods=['POST'])
@login_required
def get_frases():
    logger.info("Recebida solicitação de frases")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/seguranca', methods=['POST'])
@login_required
def get_seguranca():
    logger.info("Recebida solicitação de segurança")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/hospitais', methods=['POST'])
@login_required
def get_hospitais():
    logger.info("Recebida solicitação de hospitais")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/consulados', methods=['POST'])
@login_required
def get_consulados():
    logger.info("Recebida solicitação de consulados")
    
    try:
        data = request.json
        user_id = current_user.id
        if not current_user.check_subscription():
            logger.error("Assinatura não ativa")
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
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Erro na interação com o ChatGPT: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/roteiro', methods=['POST'])
def roteiro():
    logger.info("Recebida solicitação de roteiro")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    logger.info(f"Dados recebidos: {data}")
    
    message = data.get('message')
    if not message:
        logger.error("Mensagem não fornecida")
        return jsonify({'error': 'Message is required'}), 400

    try:
        # Extrair destino e dias da mensagem
        parts = message.lower().split()
        destino = parts[0]
        dias = next((p for p in parts if p.isdigit()), '3')
        
        logger.info(f"Processando roteiro para {destino} por {dias} dias")

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente de viagem especializado em criar roteiros detalhados."},
                {"role": "user", "content": f"Crie um roteiro detalhado para {destino} em {dias} dias, incluindo atrações, horários e dicas práticas."}
            ]
        )
        
        result = response.choices[0].message['content']
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({
            'success': True,
            'response': result
        })
    except Exception as e:
        logger.error(f"Erro ao gerar roteiro: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate response', 'details': str(e)}), 500

@app.route('/api/festivais', methods=['POST'])
def festivais():
    logger.info("Recebida solicitação de festivais")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    logger.info(f"Dados recebidos: {data}")
    
    message = data.get('message')
    if not message:
        logger.error("Mensagem não fornecida")
        return jsonify({'error': 'Message is required'}), 400

    try:
        logger.info(f"Processando festivais para {message}")
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em eventos culturais e festivais ao redor do mundo."},
                {"role": "user", "content": f"Liste os principais festivais, eventos culturais e celebrações que acontecem em {message} ao longo do ano. Inclua datas aproximadas, descrições e dicas para participar."}
            ]
        )
        
        result = response.choices[0].message['content']
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({
            'success': True,
            'response': result
        })
    except Exception as e:
        logger.error(f"Erro ao buscar festivais: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate response', 'details': str(e)}), 500

@app.route('/api/<feature>', methods=['POST'])
def handle_feature(feature):
    logger.info(f"Recebida solicitação de recurso {feature}")
    
    if not request.is_json:
        logger.error("Solicitação não é JSON")
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    logger.info(f"Dados recebidos: {data}")
    
    message = data.get('message')
    if not message:
        logger.error("Mensagem não fornecida")
        return jsonify({'error': 'Message is required'}), 400

    # Mapeia cada feature para sua prompt específica
    feature_prompts = {
        'precos': f"Forneça informações detalhadas sobre custos de viagem em {message}, incluindo hospedagem, alimentação, transporte e atrações turísticas.",
        'checklist': f"Crie uma lista completa do que levar para uma viagem a {message}.",
        'gastronomia': f"Descreva detalhadamente a gastronomia de {message}, incluindo pratos típicos, restaurantes recomendados e experiências culinárias imperdíveis.",
        'documentacao': f"Liste todos os documentos necessários para viajar para {message}, incluindo vistos, passaportes e outros requisitos.",
        'guia': f"Crie um guia completo de {message}, incluindo principais atrações, dicas locais e informações práticas.",
        'festivais': f"Liste os principais festivais e eventos culturais que acontecem em {message} ao longo do ano.",
        'hospedagem': f"Recomende as melhores regiões e opções de hospedagem em {message} para diferentes orçamentos.",
        'historias': f"Conte histórias interessantes e curiosidades sobre {message}.",
        'frases': f"Liste frases úteis em {message} para viajantes, incluindo pronúncia e tradução.",
        'seguranca': f"Forneça dicas de segurança importantes para viajantes em {message}.",
        'hospitais': f"Liste os principais hospitais e informações médicas importantes em {message}.",
        'consulados': f"Forneça informações sobre consulados e embaixadas brasileiras em {message}."
    }

    if feature not in feature_prompts:
        logger.error("Recurso não suportado")
        return jsonify({'error': 'Invalid feature'}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente de viagem especializado."},
                {"role": "user", "content": feature_prompts[feature]}
            ]
        )
        
        result = response.choices[0].message['content']
        logger.info("Resposta gerada com sucesso")
        
        return jsonify({
            'success': True,
            'response': result
        })
    except Exception as e:
        logger.error(f"Erro ao chamar o OpenAI: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate response', 'details': str(e)}), 500

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
