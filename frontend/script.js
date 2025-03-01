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

    // Estado global
    let usesRemaining = 3;
    let requiresLogin = false;

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
                alert(data.error || 'Erro ao fazer login');
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
                alert(data.error || 'Erro ao registrar');
            }
        } catch (error) {
            console.error('Erro ao registrar:', error);
            alert('Erro ao registrar. Tente novamente.');
        }
    }

    async function logout() {
        try {
            await fetch(`${API_URL}/api/logout`, {
                method: 'POST',
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
        userInfo.style.display = 'flex';
        logoutButton.style.display = 'block';
        userEmail.textContent = currentUser.email;
    }

    function updateUIForLoggedOutUser() {
        loginButton.style.display = 'block';
        registerButton.style.display = 'block';
        userInfo.style.display = 'none';
        logoutButton.style.display = 'none';
        userEmail.textContent = '';
    }

    function showLoginModal() {
        loginModal.style.display = 'block';
    }

    function hideLoginModal() {
        loginModal.style.display = 'none';
        loginForm.reset();
    }

    function showRegisterModal() {
        registerModal.style.display = 'block';
    }

    function hideRegisterModal() {
        registerModal.style.display = 'none';
        registerForm.reset();
    }

    function scrollToInput() {
        const inputRect = userInput.getBoundingClientRect();
        const windowHeight = window.innerHeight;
        
        if (inputRect.bottom > windowHeight) {
            window.scrollTo({
                top: window.scrollY + (inputRect.bottom - windowHeight) + 20,
                behavior: 'smooth'
            });
        }
    }

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
        
        // Formata o conteúdo com quebras de linha
        const formattedContent = content.replace(/\n/g, '<br>');
        messageDiv.innerHTML = formattedContent;
        
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    async function handleFeatureClick(feature) {
        try {
            const response = await fetch(`${API_URL}/api/check_auth`, {
                credentials: 'include'
            });
            const authData = await response.json();

            if (!authData.authenticated) {
                showLoginModal();
                addMessage("Por favor, faça login para continuar usando o assistente.", false);
                return;
            }

            if (!authData.subscription_active) {
                addMessage("Você precisa de uma assinatura ativa para usar esta função. Redirecionando para a página de pagamento...", false);
                setTimeout(() => {
                    window.location.href = 'https://pay.kiwify.com.br/Ug7fYhB';
                }, 3000);
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
                    prompt = 'Para qual cidade você gostaria de recomendações de hospedagem?';
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
            }
            
            userInput.setAttribute('data-feature', feature);
            userInput.placeholder = prompt;
            userInput.value = '';
            scrollToInput();
        } catch (error) {
            console.error('Erro:', error);
            addMessage("Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.", false);
        }
    }

    async function handleSend() {
        try {
            const message = userInput.value.trim();
            if (!message) return;

            const feature = userInput.getAttribute('data-feature');
            if (!feature) {
                addMessage('Por favor, selecione uma função antes de enviar sua mensagem.');
                return;
            }

            const authResponse = await fetch(`${API_URL}/api/check_auth`, {
                credentials: 'include'
            });
            const authData = await authResponse.json();

            if (!authData.authenticated) {
                showLoginModal();
                addMessage("Por favor, faça login para continuar usando o assistente.", false);
                return;
            }

            if (!authData.subscription_active) {
                addMessage("Você precisa de uma assinatura ativa para usar esta função. Redirecionando para a página de pagamento...", false);
                setTimeout(() => {
                    window.location.href = 'https://pay.kiwify.com.br/Ug7fYhB';
                }, 3000);
                return;
            }

            addMessage(message, true);
            userInput.value = '';

            const response = await fetch(`${API_URL}/api/feature/${feature}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    message: message
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Erro ao processar sua solicitação');
            }

            const data = await response.json();
            addMessage(data.response, false);
            scrollToInput();

        } catch (error) {
            console.error('Erro:', error);
            addMessage("Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.", false);
        }
    }

    // Event Listeners
    loginButton.addEventListener('click', showLoginModal);
    registerButton.addEventListener('click', showRegisterModal);
    logoutButton.addEventListener('click', logout);

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        await login(email, password);
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        await register(email, password);
    });

    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            hideLoginModal();
            hideRegisterModal();
        });
    });

    window.addEventListener('click', (e) => {
        if (e.target === loginModal) hideLoginModal();
        if (e.target === registerModal) hideRegisterModal();
    });

    featureButtons.forEach(button => {
        button.addEventListener('click', () => {
            handleFeatureClick(button.getAttribute('data-feature'));
        });
    });

    sendButton.addEventListener('click', handleSend);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    // Inicialização
    checkAuthStatus();
});
