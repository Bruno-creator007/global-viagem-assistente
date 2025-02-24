# Global Viagem Assistente 

Um assistente de viagem inteligente com interface web minimalista, inspirado no design do Google.

## Funcionalidades 

- Chat interativo para dúvidas sobre viagens
- Geração de roteiros personalizados
- Alertas de preços
- Checklist de viagem
- Sugestões gastronômicas
- Informações sobre documentação
- E muito mais!

## Requisitos 

- Python 3.8+
- Node.js (opcional, para desenvolvimento frontend)
- Chave de API do OpenAI

## Configuração do Ambiente 

1. Clone o repositório:
```bash
git clone <seu-repositorio>
cd global-viagem-assistente
```

2. Instale as dependências do backend:
```bash
cd backend
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
1. Crie um arquivo `.env` na raiz do projeto
2. Adicione sua chave da API OpenAI no arquivo `.env`:
```
OPENAI_API_KEY=sua-chave-api-aqui
```

## Executando o Projeto 

1. Inicie o backend:
```bash
cd backend
python app.py
```

2. Abra o arquivo `frontend/index.html` em seu navegador

O servidor backend estará rodando em `http://localhost:5000`

## Estrutura do Projeto 

```
global-viagem-assistente/
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── backend/
│   ├── app.py
│   └── requirements.txt
└── README.md
```

## Contribuindo 

Sinta-se à vontade para contribuir com o projeto! Abra uma issue ou envie um pull request.
