# Backend - Synkhro

Backend desenvolvido com FastAPI, SQLAlchemy (Async) e MySQL.

## Estrutura do Projeto

```
backend/
├── app/
│   ├── core/           # Configurações e utilitários
│   ├── api/            # Rotas HTTP
│   │   └── v1/
│   │       └── endpoints/
│   ├── services/       # Lógica de negócios
│   ├── models/         # Modelos SQLAlchemy
│   └── schemas/        # Modelos Pydantic
├── requirements.txt
└── .env.example
```

## Instalação

1. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

4. Execute o servidor:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A documentação interativa estará disponível em: http://localhost:8000/docs

## Multi-Tenant

O sistema utiliza isolamento de dados por tenant através do header `X-Tenant-ID` em todas as rotas protegidas.


