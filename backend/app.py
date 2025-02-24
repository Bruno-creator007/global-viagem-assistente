from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure OpenAI
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

def chatgpt_interaction(prompt, system_message=None):
    try:
        if system_message is None:
            system_message = """You are a helpful travel assistant providing information about destinations, travel tips, and itineraries.
            Format your responses in a clear, organized way using these guidelines:
            - Use line breaks between sections
            - Use bullet points for lists
            - Use bold text for important information
            - Use emojis to make the content more visual
            - Break down information into clear sections
            - Use tables when comparing information
            - Keep paragraphs short and focused
            - Highlight key points and recommendations"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return str(e)

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
        system_message = """You are a travel itinerary specialist. Format your response in a clear, organized way:
        - Start with a brief introduction about the destination
        - Break down the itinerary day by day
        - Use bullet points for activities within each day
        - Include estimated times and prices in parentheses
        - Use emojis for different types of activities (🏛️ sights, 🍴 food, etc.)
        - Add travel tips at the end
        - Keep paragraphs short and focused
        - Use bold for important information"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a summary of estimated total costs
        - Break down costs by category (accommodations, food, transportation, etc.)
        - Use bullet points for detailed breakdowns
        - Include price ranges in bold
        - Add money-saving tips at the end
        - Use emojis for different categories
        - Present price comparisons in tables when relevant"""
        
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
        system_message = """Format your checklist response clearly:
        - Organize items by category
        - Use bullet points for all items
        - Bold essential items
        - Add brief explanations in parentheses when needed
        - Use emojis for different categories
        - Include specific recommendations for the destination
        - Add tips for packing efficiently"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the local cuisine
        - Break down recommendations by category (restaurants, cafes, etc.)
        - Use bullet points for detailed breakdowns
        - Include price ranges in bold
        - Add tips for dining at the end
        - Use emojis for different categories
        - Present comparisons in tables when relevant"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the destination
        - Break down requirements by category (visa, passport, etc.)
        - Use bullet points for detailed breakdowns
        - Include important deadlines and fees in bold
        - Add tips for the application process at the end
        - Use emojis for different categories"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the train route
        - Break down the itinerary day by day
        - Use bullet points for activities within each day
        - Include estimated times and prices in parentheses
        - Use emojis for different types of activities (🚂 train, 🏛️ sights, etc.)
        - Add travel tips at the end
        - Keep paragraphs short and focused
        - Use bold for important information"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the destination
        - Break down recommendations by category (sights, activities, etc.)
        - Use bullet points for detailed breakdowns
        - Include estimated times and prices in parentheses
        - Use emojis for different types of activities (🏛️ sights, 🍴 food, etc.)
        - Add tips for the visit at the end
        - Keep paragraphs short and focused
        - Use bold for important information"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the festivals
        - Break down recommendations by category (music, food, etc.)
        - Use bullet points for detailed breakdowns
        - Include dates and prices in bold
        - Add tips for attending the festivals at the end
        - Use emojis for different categories"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the accommodations
        - Break down recommendations by category (hotels, hostels, etc.)
        - Use bullet points for detailed breakdowns
        - Include price ranges in bold
        - Add tips for booking at the end
        - Use emojis for different categories"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the city
        - Break down stories by category (history, culture, etc.)
        - Use bullet points for detailed breakdowns
        - Include interesting facts and anecdotes
        - Add tips for exploring the city at the end
        - Use emojis for different categories"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the language
        - Break down phrases by category (greetings, directions, etc.)
        - Use bullet points for detailed breakdowns
        - Include pronunciation guides and examples
        - Add tips for communication at the end
        - Use emojis for different categories"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about safety in the city
        - Break down tips by category (crime, health, etc.)
        - Use bullet points for detailed breakdowns
        - Include important phone numbers and resources
        - Add general advice for staying safe at the end
        - Use emojis for different categories"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about medical care in the city
        - Break down recommendations by category (hospitals, clinics, etc.)
        - Use bullet points for detailed breakdowns
        - Include addresses, phone numbers, and hours of operation
        - Add tips for medical emergencies at the end
        - Use emojis for different categories"""
        
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
        system_message = """Format your response with clear sections:
        - Start with a brief introduction about the consulate
        - Break down information by category (hours, contact, etc.)
        - Use bullet points for detailed breakdowns
        - Include addresses, phone numbers, and email
        - Add tips for contacting the consulate at the end
        - Use emojis for different categories"""
        
        prompt = f"Onde fica o consulado Brasileiro em {cidade}? Me informa detalhes de como entrar em contato e endereço e como agir em caso de problemas."
        response = chatgpt_interaction(prompt, system_message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
