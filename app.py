from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import openai
import os
import logging
from backend.travel_api import TravelAPI
from backend.admin import admin_bp, login_manager
from backend.models import db, AssistantFunction, Usage
from backend.config import OPENAI_API_KEY, SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    logger.error("OpenAI API key not found!")
    raise ValueError("OpenAI API key not found in environment variables")

# Initialize Flask app
app = Flask(__name__, 
    static_folder='frontend',
    template_folder='frontend/templates'
)

# Configure Flask app
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

# Initialize extensions
CORS(app)
db.init_app(app)
login_manager.init_app(app)

# Register blueprints
app.register_blueprint(admin_bp)

# Create database tables
with app.app_context():
    db.create_all()

# Initialize TravelAPI
travel_api = TravelAPI()

def get_available_functions():
    """Retorna todas as funções ativas do assistente"""
    return AssistantFunction.query.filter_by(active=True).all()

def execute_function(function_name, user_message):
    """Executa uma função específica do assistente"""
    function = AssistantFunction.query.filter_by(name=function_name, active=True).first()
    if not function:
        return jsonify({"error": "Function not found"}), 404
    
    try:
        # Log usage
        usage = Usage(
            function_id=function.id,
            user_message=user_message,
            timestamp=datetime.utcnow()
        )
        db.session.add(usage)
        db.session.commit()

        # Execute function
        if function_name == "search_flights":
            return travel_api.search_flights(user_message)
        elif function_name == "search_hotels":
            return travel_api.search_hotels(user_message)
        elif function_name == "search_activities":
            return travel_api.search_activities(user_message)
        else:
            # Use ChatGPT for other functions
            system_message = function.system_message
            return chatgpt_interaction(user_message, system_message)

    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def chatgpt_interaction(prompt, system_message=None, parameters=None):
    """Interage com o ChatGPT"""
    try:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        default_params = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 800
        }

        if parameters:
            default_params.update(parameters)

        response = openai.ChatCompletion.create(
            messages=messages,
            **default_params
        )

        return jsonify({
            "response": response.choices[0].message.content,
            "usage": response.usage
        })

    except Exception as e:
        logger.error(f"Error in ChatGPT interaction: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

@app.route('/health')
def health_check():
    """Endpoint para verificar a saúde do serviço"""
    try:
        # Verifica a conexão com o banco de dados
        db.session.execute('SELECT 1')
        db.session.commit()
        return jsonify({
            "status": "healthy",
            "database": "connected"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint principal para interação com o chatbot"""
    try:
        data = request.get_json()
        message = data.get('message')
        function_name = data.get('function')

        if not message:
            return jsonify({"error": "No message provided"}), 400

        if function_name:
            return execute_function(function_name, message)
        else:
            return chatgpt_interaction(message)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/functions', methods=['GET'])
def list_functions():
    """Retorna a lista de funções disponíveis para o frontend"""
    try:
        functions = get_available_functions()
        return jsonify([{
            'id': f.id,
            'name': f.name,
            'description': f.description
        } for f in functions])
    except Exception as e:
        logger.error(f"Error listing functions: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
