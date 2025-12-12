# Synkhro - Sistema de Agendamento Multi-Tenant

Synkhro é um sistema de agendamento web para estúdios de estética com arquitetura multi-tenant.

## Stack Tecnológica

- **Backend**: Python 3.11+ com FastAPI, SQLAlchemy (Async), Pydantic
- **Frontend**: React (Vite) + Tailwind CSS
- **Banco de Dados**: MySQL
- **ORM**: SQLAlchemy (Async)

## Estrutura do Projeto

```
.
├── backend/          # API FastAPI
│   └── app/
│       ├── core/     # Configurações e dependências
│       ├── api/      # Rotas HTTP
│       ├── services/ # Lógica de negócios
│       ├── models/   # Modelos SQLAlchemy
│       └── schemas/  # Modelos Pydantic
│
└── frontend/         # Aplicação React
    └── src/
        ├── components/  # Componentes UI
        ├── features/    # Features específicas
        ├── hooks/       # Custom hooks
        └── utils/       # Utilitários
```

## Início Rápido

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
cp .env.example .env
# Configure o .env com suas credenciais
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Multi-Tenant

O sistema utiliza isolamento de dados por tenant através do header `X-Tenant-ID` em todas as rotas protegidas. Cada empresa (tenant) possui seus próprios dados isolados.

## 🐳 Docker Compose

Para executar todo o sistema com um único comando:

```bash
# 1. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env conforme necessário

# 2. Iniciar todos os serviços
docker-compose up -d

# 3. Acessar
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

Veja [DOCKER_COMPOSE.md](./DOCKER_COMPOSE.md) para mais detalhes.

## 📦 Deploy

### Render.com

Este projeto está configurado para deploy no Render:
- Backend: FastAPI com Uvicorn
- Frontend: React/Vite com Nginx
- Banco de Dados: MySQL (Render MySQL ou externo)

Veja [README_DEPLOY.md](./README_DEPLOY.md) para instruções de deploy.

## 📚 Documentação

- Backend API: http://localhost:8000/docs (Swagger UI)
- Frontend: http://localhost:5173
- Docker Compose: [DOCKER_COMPOSE.md](./DOCKER_COMPOSE.md)

## 🔗 Links

- Repositório: https://github.com/abns22/synkhro


