document.addEventListener('DOMContentLoaded', () => {
    // Elementos existentes
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const chatHistory = document.getElementById('chatHistory');
    const featureButtons = document.querySelectorAll('.feature-btn');

    // Novos elementos de autenticação
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const userDashboardBtn = document.getElementById('userDashboardBtn');
    const loginModal = document.getElementById('loginModal');
    const registerModal = document.getElementById('registerModal');
    const userDashboardModal = document.getElementById('userDashboardModal');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const logoutBtn = document.getElementById('logoutBtn');
    const upgradeBtn = document.getElementById('upgradeBtn');

    // API URL configuration
    const API_URL = window.location.hostname === 'localhost' 
        ? 'http://localhost:5000'
        : window.location.origin;

    // Estado do usuário
    let userState = {
        authenticated: false,
        subscriptionActive: false,
        freeUsesRemaining: 3
    };

    // Funções de autenticação
    async function checkAuth() {
        try {
            const response = await fetch(`${API_URL}/api/check_auth`, {
                credentials: 'include'
            });
            const data = await response.json();
            
            updateUserState(data);
        } catch (error) {
            console.error('Erro ao verificar autenticação:', error);
        }
    }

    function updateUserState(data) {
        userState = {
            authenticated: data.authenticated,
            subscriptionActive: data.subscription_active,
            freeUsesRemaining: data.free_uses_remaining
        };

        // Atualiza UI
        loginBtn.style.display = data.authenticated ? 'none' : 'block';
        registerBtn.style.display = data.authenticated ? 'none' : 'block';
        userDashboardBtn.style.display = data.authenticated ? 'block' : 'none';

        if (data.authenticated) {
            document.getElementById('subscriptionStatus').textContent = 
                data.subscription_active ? 'Assinatura ativa' : 'Assinatura inativa';
            document.getElementById('freeUsesRemaining').textContent = 
                `Usos gratuitos restantes: ${data.free_uses_remaining}`;
        }
    }

    async function handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const response = await fetch(`${API_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            if (data.success) {
                updateUserState({
                    authenticated: true,
                    subscription_active: data.subscription_active,
                    free_uses_remaining: 3
                });
                closeModal(loginModal);
                loginForm.reset();
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Erro ao fazer login:', error);
            alert('Erro ao fazer login. Tente novamente.');
        }
    }

    async function handleRegister(e) {
        e.preventDefault();
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        if (password !== confirmPassword) {
            alert('As senhas não coincidem');
            return;
        }

        try {
            const response = await fetch(`${API_URL}/api/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            if (data.success) {
                updateUserState({
                    authenticated: true,
                    subscription_active: false,
                    free_uses_remaining: 3
                });
                closeModal(registerModal);
                registerForm.reset();
                window.location.href = 'https://kiwify.com.br/seu-produto'; // Substitua pelo link real
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Erro ao registrar:', error);
            alert('Erro ao criar conta. Tente novamente.');
        }
    }

    async function handleLogout() {
        try {
            await fetch(`${API_URL}/api/logout`, {
                method: 'POST',
                credentials: 'include'
            });
            
            updateUserState({
                authenticated: false,
                subscription_active: false,
                free_uses_remaining: 3
            });
            
            closeModal(userDashboardModal);
        } catch (error) {
            console.error('Erro ao fazer logout:', error);
        }
    }

    // Funções de modal
    function openModal(modal) {
        modal.style.display = 'block';
    }

    function closeModal(modal) {
        modal.style.display = 'none';
    }

    // Event listeners para autenticação
    loginBtn.addEventListener('click', () => openModal(loginModal));
    registerBtn.addEventListener('click', () => openModal(registerModal));
    userDashboardBtn.addEventListener('click', () => openModal(userDashboardModal));
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    logoutBtn.addEventListener('click', handleLogout);
    upgradeBtn.addEventListener('click', () => {
        window.location.href = 'https://pay.kiwify.com.br/Ug7fYhB';
    });

    // Fecha modais quando clica no X
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            closeModal(closeBtn.closest('.modal'));
        });
    });

    // Fecha modais quando clica fora
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target);
        }
    });

    // API URL configuration
    const API_URL = window.location.hostname === 'localhost' 
        ? 'http://localhost:5000'
        : window.location.origin;

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
            const response = await fetch(`${API_URL}/api/${endpoint}`, {
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

        // Verifica acesso
        if (!userState.authenticated && userState.freeUsesRemaining === 0) {
            openModal(registerModal);
            return;
        }

        const feature = userInput.getAttribute('data-feature') || 'chat';
        addMessage(message, true);
        userInput.value = '';

        try {
            const response = await fetch(`${API_URL}/api/feature/${feature}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            if (!data.success) {
                if (data.error === 'Faça login para continuar') {
                    openModal(loginModal);
                    return;
                }
                throw new Error(data.error);
            }

            addMessage(data.response);

        } catch (error) {
            console.error('Error:', error);
            addMessage('Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.');
        }
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

    // Verifica autenticação ao carregar a página
    checkAuth();
});
