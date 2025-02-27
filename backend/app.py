from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import openai
import os
import logging
from backend.travel_api import TravelAPI
from admin import admin_bp, login_manager
from models import db, AssistantFunction, Usage
from datetime import datetime
from config import OPENAI_API_KEY, SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    logger.error("OpenAI API key not found!")
    raise ValueError("OpenAI API key not found in environment variables")

app = Flask(__name__, 
    static_folder='../frontend/static',
    template_folder='../frontend/templates'
)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = SECRET_KEY

# Inicializa as extensões
db.init_app(app)
login_manager.init_app(app)

# Registra o blueprint do admin
app.register_blueprint(admin_bp)

# Cria as tabelas do banco de dados
with app.app_context():
    db.create_all()

CORS(app, resources={r"/api/*": {"origins": "*"}})
travel_api = TravelAPI()

def get_available_functions():
    """Retorna todas as funções ativas do assistente"""
    return AssistantFunction.query.filter_by(is_active=True).all()

def execute_function(function_name, user_message):
    """Executa uma função específica do assistente"""
    try:
        function = AssistantFunction.query.filter_by(name=function_name, is_active=True).first()
        if not function:
            return None
            
        # Registra o uso da função
        usage = Usage(
            function_name=function_name,
            user_id="anonymous",  # Você pode modificar isso para usar IDs reais de usuários
            timestamp=datetime.utcnow(),
            success=True
        )
        
        start_time = datetime.utcnow()
        
        # Se a função tem um endpoint personalizado, use-o
        if function.endpoint and function.api_key:
            # Aqui você implementaria a chamada para o endpoint personalizado
            response = "Função com endpoint personalizado ainda não implementada"
        else:
            # Caso contrário, use o ChatGPT com os parâmetros da função
            response = chatgpt_interaction(
                user_message,
                system_message=function.description,
                parameters=function.parameters
            )
        
        # Atualiza o tempo de resposta
        usage.response_time = (datetime.utcnow() - start_time).total_seconds()
        db.session.add(usage)
        db.session.commit()
        
        return response
        
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        if 'usage' in locals():
            usage.success = False
            usage.response_time = (datetime.utcnow() - start_time).total_seconds()
            db.session.add(usage)
            db.session.commit()
        return None

def chatgpt_interaction(prompt, system_message=None, parameters=None):
    try:
        if system_message is None:
            system_message = "Você é um assistente de viagem profissional, especializado em dar informações precisas e úteis sobre destinos, roteiros, documentação e dicas de viagem. Seja sempre claro e organizado em suas respostas."
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # Se houver parâmetros específicos para a função, use-os
        if parameters:
            completion_params = {
                "model": parameters.get("model", "gpt-3.5-turbo"),
                "temperature": parameters.get("temperature", 0.7),
                "max_tokens": parameters.get("max_tokens", 1000)
            }
        else:
            completion_params = {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        
        response = openai.ChatCompletion.create(
            messages=messages,
            **completion_params
        )
        
        return response.choices[0].message['content'].strip()
    except Exception as e:
        logger.error(f"Error in chatgpt_interaction: {str(e)}")
        raise

@app.route('/')
def serve_index():
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
            "OPENAI_API_KEY": "configured" if openai.api_key else "missing",
            "PORT": os.getenv('PORT', '5000')
        }
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        function_name = data.get('function', 'chat')  # Se nenhuma função específica for solicitada, use o chat padrão
        
        # Tenta executar uma função específica
        response = execute_function(function_name, user_message)
        
        # Se não houver resposta da função específica, use o chat padrão
        if response is None:
            response = chatgpt_interaction(user_message)
        
        return jsonify({"success": True, "response": response})
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/functions', methods=['GET'])
def list_functions():
    """Retorna a lista de funções disponíveis para o frontend"""
    functions = get_available_functions()
    return jsonify({
        "success": True,
        "functions": [{"name": f.name, "description": f.description} for f in functions]
    })

@app.route('/api/roteiro', methods=['POST'])
def get_roteiro():
    try:
        data = request.json
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
def get_precos():
    try:
        data = request.json
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
def get_checklist():
    try:
        data = request.json
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
def get_gastronomia():
    try:
        data = request.json
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
def get_documentacao():
    try:
        data = request.json
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
def get_trem():
    try:
        data = request.json
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
def get_guia():
    try:
        data = request.json
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
def get_festivais():
    try:
        data = request.json
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
def get_hospedagem():
    try:
        data = request.json
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
def get_historias():
    try:
        data = request.json
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
def get_frases():
    try:
        data = request.json
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
def get_seguranca():
    try:
        data = request.json
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
def get_hospitais():
    try:
        data = request.json
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
def get_consulados():
    try:
        data = request.json
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

@app.route('/api/flights', methods=['POST'])
def search_flights():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    departure_date = data.get('departure_date')
    return_date = data.get('return_date')
    
    if not all([origin, destination, departure_date]):
        return jsonify({"error": "Parâmetros incompletos"}), 400
        
    results = travel_api.search_flights(origin, destination, departure_date, return_date)
    return jsonify(results)

@app.route('/api/hotels', methods=['POST'])
def search_hotels():
    data = request.json
    city_code = data.get('city_code')
    check_in_date = data.get('check_in_date')
    check_out_date = data.get('check_out_date')
    
    if not all([city_code, check_in_date, check_out_date]):
        return jsonify({"error": "Parâmetros incompletos"}), 400
        
    results = travel_api.search_hotels(city_code, check_in_date, check_out_date)
    return jsonify(results)

@app.route('/api/activities', methods=['POST'])
def search_activities():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not all([latitude, longitude]):
        return jsonify({"error": "Parâmetros incompletos"}), 400
        
    results = travel_api.search_activities(latitude, longitude)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
