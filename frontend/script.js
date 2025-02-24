document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const chatHistory = document.getElementById('chatHistory');
    const featureButtons = document.querySelectorAll('.feature-btn');

    const API_URL = 'http://localhost:5000/api';

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
        
        if (isUser) {
            messageDiv.textContent = content;
        } else {
            // Convert line breaks to HTML and handle markdown-style formatting
            const formattedContent = content
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/^- /gm, '• ');

            messageDiv.innerHTML = `<p>${formattedContent}</p>`;
        }
        
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    async function sendMessage(message, endpoint = 'chat') {
        try {
            const response = await fetch(`${API_URL}/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }

            return data.response;
        } catch (error) {
            console.error('Error:', error);
            return 'Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.';
        }
    }

    async function handleFeatureClick(feature) {
        let prompt;
        switch (feature) {
            case 'roteiro':
                prompt = 'Por favor, me diga para qual destino você gostaria de um roteiro e por quantos dias?';
                break;
            case 'trem':
                prompt = 'Informe quais países da Europa você quer conhecer e quantos dias de viagem no total:';
                break;
            case 'precos':
                prompt = 'Para qual destino você gostaria de saber os preços e quantos dias de viagem?';
                break;
            case 'checklist':
                prompt = 'Para qual destino você precisa de um checklist de viagem?';
                break;
            case 'gastronomia':
                prompt = 'Qual cidade você quer conhecer a gastronomia? (Informe também se prefere opções econômicas, intermediárias ou luxuosas)';
                break;
            case 'documentacao':
                prompt = 'Para qual país você precisa de informações sobre documentação?';
                break;
            case 'guia':
                prompt = 'Em qual cidade você está e quanto tempo tem disponível para passeios?';
                break;
            case 'festivais':
                prompt = 'Para qual cidade você deseja saber sobre festivais e eventos?';
                break;
            case 'hospedagem':
                prompt = 'Para qual cidade você gostaria de recomendações de áreas para hospedagem?';
                break;
            case 'historias':
                prompt = 'Sobre qual cidade você gostaria de saber histórias e curiosidades?';
                break;
            case 'frases':
                prompt = 'Para qual idioma você gostaria de receber frases úteis? (Ex: francês, espanhol)';
                break;
            case 'seguranca':
                prompt = 'Para qual cidade você gostaria de dicas de segurança?';
                break;
            case 'hospitais':
                prompt = 'Em qual cidade você precisa de informações sobre hospitais próximos?';
                break;
            case 'consulados':
                prompt = 'Em qual cidade você gostaria de encontrar consulados?';
                break;
            default:
                return;
        }

        addMessage(prompt, false);
        userInput.focus();
        userInput.setAttribute('data-feature', feature);
    }

    async function handleSend() {
        const message = userInput.value.trim();
        if (!message) return;

        const feature = userInput.getAttribute('data-feature') || 'chat';
        addMessage(message, true);
        userInput.value = '';

        let response;
        try {
            const requestBody = { message };

            // Add specific parameters based on the feature
            switch (feature) {
                case 'roteiro':
                    const [destino, dias] = message.split(' por ');
                    response = await fetch(`${API_URL}/roteiro`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ destino, dias: dias || '5' })
                    });
                    break;
                case 'trem':
                    response = await fetch(`${API_URL}/trem`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ destinos: message })
                    });
                    break;
                case 'precos':
                    response = await fetch(`${API_URL}/precos`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ destino: message })
                    });
                    break;
                case 'checklist':
                    response = await fetch(`${API_URL}/checklist`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ destino: message })
                    });
                    break;
                case 'gastronomia':
                    response = await fetch(`${API_URL}/gastronomia`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ destino: message })
                    });
                    break;
                case 'documentacao':
                    response = await fetch(`${API_URL}/documentacao`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ destino: message, origem: 'Brasil' })
                    });
                    break;
                case 'guia':
                    response = await fetch(`${API_URL}/guia`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ local: message })
                    });
                    break;
                case 'festivais':
                    response = await fetch(`${API_URL}/festivais`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'hospedagem':
                    response = await fetch(`${API_URL}/hospedagem`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'historias':
                    response = await fetch(`${API_URL}/historias`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'frases':
                    response = await fetch(`${API_URL}/frases`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ idioma: message })
                    });
                    break;
                case 'seguranca':
                    response = await fetch(`${API_URL}/seguranca`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'hospitais':
                    response = await fetch(`${API_URL}/hospitais`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'consulados':
                    response = await fetch(`${API_URL}/consulados`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                default:
                    response = await fetch(`${API_URL}/chat`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message })
                    });
            }

            const data = await response.json();
            if (data.success) {
                addMessage(data.response, false);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.', false);
        }

        userInput.removeAttribute('data-feature');
    }

    sendButton.addEventListener('click', handleSend);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    featureButtons.forEach(button => {
        if (!button.classList.contains('reserva')) {
            button.addEventListener('click', () => {
                const feature = button.getAttribute('data-feature');
                handleFeatureClick(feature);
            });
        }
    });
});
