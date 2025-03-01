// Elementos do DOM
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');
const loginModal = document.getElementById('login-modal');
const registerModal = document.getElementById('register-modal');
const userDashboardModal = document.getElementById('user-dashboard-modal');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');
const logoutBtn = document.getElementById('logout-btn');
const userDashboardBtn = document.getElementById('user-dashboard-btn');
const upgradeBtn = document.getElementById('upgrade-btn');
const closeButtons = document.querySelectorAll('.close-button');

// Estado do usuário
let userAuthenticated = false;
let userSubscriptionActive = false;
let freeUsesRemaining = 3;

// Funções de utilidade
function showMessage(message, isError = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isError ? 'error' : ''}`;
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function openModal(modal) {
    modal.style.display = 'block';
}

function closeModal(modal) {
    modal.style.display = 'none';
}

// Funções de API
async function checkAuth() {
    try {
        const response = await fetch('/api/check_auth');
        const data = await response.json();
        userAuthenticated = data.authenticated;
        userSubscriptionActive = data.subscription_active;
        freeUsesRemaining = data.free_uses_remaining;
        updateUI();
    } catch (error) {
        console.error('Erro ao verificar autenticação:', error);
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const formData = new FormData(loginForm);
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: formData.get('email'),
                password: formData.get('password'),
            }),
        });
        const data = await response.json();
        if (response.ok) {
            userAuthenticated = true;
            closeModal(loginModal);
            checkAuth();
            showMessage('Login realizado com sucesso!');
        } else {
            showMessage(data.error || 'Erro ao fazer login', true);
        }
    } catch (error) {
        showMessage('Erro ao conectar com o servidor', true);
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const formData = new FormData(registerForm);
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: formData.get('email'),
                password: formData.get('password'),
                name: formData.get('name'),
            }),
        });
        const data = await response.json();
        if (response.ok) {
            closeModal(registerModal);
            showMessage('Cadastro realizado com sucesso! Faça login para continuar.');
        } else {
            showMessage(data.error || 'Erro ao fazer cadastro', true);
        }
    } catch (error) {
        showMessage('Erro ao conectar com o servidor', true);
    }
}

async function handleLogout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        userAuthenticated = false;
        userSubscriptionActive = false;
        updateUI();
        showMessage('Logout realizado com sucesso!');
    } catch (error) {
        showMessage('Erro ao fazer logout', true);
    }
}

async function handleChatSubmit(event) {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    // Verificar se o usuário pode usar o serviço
    if (!userAuthenticated && freeUsesRemaining <= 0) {
        openModal(registerModal);
        showMessage('Crie uma conta para continuar usando o assistente!', true);
        return;
    }

    if (userAuthenticated && !userSubscriptionActive && freeUsesRemaining <= 0) {
        openModal(userDashboardModal);
        showMessage('Assine para continuar usando o assistente!', true);
        return;
    }

    showMessage(`Você: ${message}`);
    chatInput.value = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        });
        
        if (!response.ok) {
            throw new Error('Erro na resposta do servidor');
        }

        const data = await response.json();
        showMessage(`Assistente: ${data.response}`);
        
        // Atualizar contagem de usos gratuitos
        if (!userSubscriptionActive) {
            freeUsesRemaining = data.free_uses_remaining;
            updateUI();
        }
    } catch (error) {
        showMessage('Erro ao processar sua mensagem. Tente novamente.', true);
    }
}

function updateUI() {
    // Atualizar visibilidade dos botões
    if (userAuthenticated) {
        loginBtn.style.display = 'none';
        registerBtn.style.display = 'none';
        logoutBtn.style.display = 'block';
        userDashboardBtn.style.display = 'block';
    } else {
        loginBtn.style.display = 'block';
        registerBtn.style.display = 'block';
        logoutBtn.style.display = 'none';
        userDashboardBtn.style.display = 'none';
    }

    // Atualizar informações do dashboard
    const usageInfo = document.getElementById('usage-info');
    if (usageInfo) {
        if (userSubscriptionActive) {
            usageInfo.textContent = 'Assinatura ativa';
            upgradeBtn.style.display = 'none';
        } else {
            usageInfo.textContent = `Usos gratuitos restantes: ${freeUsesRemaining}`;
            upgradeBtn.style.display = 'block';
        }
    }
}

// Event Listeners
chatForm.addEventListener('submit', handleChatSubmit);

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

// Fechar modais quando clica no X
closeButtons.forEach(button => {
    button.addEventListener('click', () => {
        const modal = button.closest('.modal');
        closeModal(modal);
    });
});

// Fechar modal quando clica fora
window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
        closeModal(event.target);
    }
});

// Verificar autenticação ao carregar a página
document.addEventListener('DOMContentLoaded', checkAuth);
