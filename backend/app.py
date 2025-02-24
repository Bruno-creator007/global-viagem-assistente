from flask import Flask, request, jsonify
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

app = Flask(__name__)
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

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Welcome to Global Viagem Assistente API"})

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
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        response = chatgpt_interaction(user_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
