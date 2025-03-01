document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const chatHistory = document.getElementById('chatHistory');
    const featureButtons = document.querySelectorAll('.feature-btn');

    // API URL configuration
    const API_URL = window.location.hostname === 'localhost' 
        ? 'http://localhost:5000'
        : window.location.origin;

    let currentUser = null;

    // Elementos DOM
    const loginButton = document.getElementById('loginButton');
    const registerButton = document.getElementById('registerButton');
    const logoutButton = document.getElementById('logoutButton');
    const userInfo = document.getElementById('userInfo');
    const userEmail = document.getElementById('userEmail');
    const loginModal = document.getElementById('loginModal');
    const registerModal = document.getElementById('registerModal');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    // Funções de autenticação
    async function checkAuthStatus() {
        try {
            const response = await fetch(`${API_URL}/api/check_auth`, {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.authenticated) {
                currentUser = {
                    id: data.user_id,
                    email: data.email,
                    subscription_active: data.subscription_active
                };
                updateUIForLoggedInUser();
            } else {
                currentUser = null;
                updateUIForLoggedOutUser();
            }
        } catch (error) {
            console.error('Erro ao verificar autenticação:', error);
        }
    }

    async function login(email, password) {
        try {
            const response = await fetch(`${API_URL}/api/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                currentUser = {
                    id: data.user_id,
                    email: data.email,
                    subscription_active: data.subscription_active
                };
                updateUIForLoggedInUser();
                hideLoginModal();
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Erro ao fazer login:', error);
            alert('Erro ao fazer login. Tente novamente.');
        }
    }

    async function register(email, password) {
        try {
            const response = await fetch(`${API_URL}/api/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                currentUser = {
                    id: data.user_id,
                    email: data.email,
                    subscription_active: false
                };
                updateUIForLoggedInUser();
                hideRegisterModal();
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Erro ao registrar:', error);
            alert('Erro ao registrar. Tente novamente.');
        }
    }

    async function logout() {
        try {
            await fetch(`${API_URL}/api/logout`, {
                credentials: 'include'
            });
            currentUser = null;
            updateUIForLoggedOutUser();
        } catch (error) {
            console.error('Erro ao fazer logout:', error);
        }
    }

    // Funções UI
    function updateUIForLoggedInUser() {
        loginButton.style.display = 'none';
        registerButton.style.display = 'none';
        userInfo.style.display = 'inline-flex';
        userEmail.textContent = currentUser.email;
    }

    function updateUIForLoggedOutUser() {
        loginButton.style.display = 'inline-block';
        registerButton.style.display = 'inline-block';
        userInfo.style.display = 'none';
        userEmail.textContent = '';
    }

    function showLoginModal() {
        loginModal.classList.add('show');
    }

    function hideLoginModal() {
        loginModal.classList.remove('show');
        loginForm.reset();
    }

    function showRegisterModal() {
        registerModal.classList.add('show');
    }

    function hideRegisterModal() {
        registerModal.classList.remove('show');
        registerForm.reset();
    }

    // Event Listeners
    loginButton.addEventListener('click', showLoginModal);
    registerButton.addEventListener('click', showRegisterModal);
    logoutButton.addEventListener('click', logout);

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        login(email, password);
    });

    registerForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        register(email, password);
    });

    // Fechar modais ao clicar fora
    window.addEventListener('click', (e) => {
        if (e.target === loginModal) hideLoginModal();
        if (e.target === registerModal) hideRegisterModal();
    });

    // Verificar assinatura antes de cada requisição
    async function checkSubscription() {
        if (!currentUser) {
            showLoginModal();
            return false;
        }
        
        if (currentUser.subscription_active) {
            return true;
        }
        
        try {
            const response = await fetch(`${API_URL}/api/check_subscription/${currentUser.id}`, {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.subscription_required) {
                showSubscriptionModal();
                return false;
            }
            return true;
        } catch (error) {
            console.error('Erro ao verificar assinatura:', error);
            return false;
        }
    }

    async function checkUsageLimit() {
        try {
            const response = await fetch(`${API_URL}/api/check_usage`, {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.requires_login) {
                if (!currentUser) {
                    showLoginModal();
                    return false;
                }
                if (!currentUser.subscription_active) {
                    showSubscriptionModal();
                    return false;
                }
            }
            return true;
        } catch (error) {
            console.error('Erro ao verificar limite de uso:', error);
            return true;
        }
    }

    async function handleFeatureClick(feature) {
        if (!await checkUsageLimit()) {
            return;
        }
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
        if (!await checkUsageLimit()) {
            return;
        }
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
                    response = await fetch(`${API_URL}/api/roteiro`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ destino, dias: dias || '5' })
                    });
                    break;
                case 'trem':
                    response = await fetch(`${API_URL}/api/trem`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ destinos: message })
                    });
                    break;
                case 'precos':
                    response = await fetch(`${API_URL}/api/precos`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ destino: message })
                    });
                    break;
                case 'checklist':
                    response = await fetch(`${API_URL}/api/checklist`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ destino: message })
                    });
                    break;
                case 'gastronomia':
                    response = await fetch(`${API_URL}/api/gastronomia`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ destino: message })
                    });
                    break;
                case 'documentacao':
                    response = await fetch(`${API_URL}/api/documentacao`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ destino: message, origem: 'Brasil' })
                    });
                    break;
                case 'guia':
                    response = await fetch(`${API_URL}/api/guia`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ local: message })
                    });
                    break;
                case 'festivais':
                    response = await fetch(`${API_URL}/api/festivais`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'hospedagem':
                    response = await fetch(`${API_URL}/api/hospedagem`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'historias':
                    response = await fetch(`${API_URL}/api/historias`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'frases':
                    response = await fetch(`${API_URL}/api/frases`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ idioma: message })
                    });
                    break;
                case 'seguranca':
                    response = await fetch(`${API_URL}/api/seguranca`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'hospitais':
                    response = await fetch(`${API_URL}/api/hospitais`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                case 'consulados':
                    response = await fetch(`${API_URL}/api/consulados`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ cidade: message })
                    });
                    break;
                default:
                    response = await fetch(`${API_URL}/api/chat`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
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

    async function updateUsageUI() {
        try {
            const response = await fetch(`${API_URL}/api/check_usage`, {
                credentials: 'include'
            });
            const data = await response.json();
            
            const usageInfo = document.getElementById('usageInfo');
            if (data.uses_remaining > 0) {
                usageInfo.textContent = `${data.uses_remaining} usos gratuitos restantes`;
                usageInfo.style.display = 'block';
            } else {
                usageInfo.style.display = 'none';
            }
        } catch (error) {
            console.error('Erro ao atualizar informações de uso:', error);
        }
    }

    sendButton.addEventListener('click', async () => {
        if (!await checkSubscription()) {
            return;
        }
        handleSend();
    });
    userInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            if (!await checkSubscription()) {
                return;
            }
            handleSend();
        }
    });

    featureButtons.forEach(button => {
        if (!button.classList.contains('reserva')) {
            button.addEventListener('click', () => {
                const feature = button.getAttribute('data-feature');
                handleFeatureClick(feature);
            });
        }
    });

    checkAuthStatus();
    updateUsageUI();
});
