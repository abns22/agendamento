# Frontend - Synkhro

Frontend desenvolvido com React (Vite) e Tailwind CSS, otimizado para mobile-first.

## Estrutura do Projeto

```
frontend/
├── src/
│   ├── components/     # Componentes UI genéricos
│   ├── features/       # Features específicas (public-booking, admin-dashboard)
│   ├── hooks/          # Custom hooks (chamadas de API)
│   ├── utils/          # Utilitários (formatadores, etc)
│   ├── App.jsx
│   └── main.jsx
├── package.json
└── vite.config.js
```

## Instalação

1. Instale as dependências:
```bash
npm install
```

2. Execute o servidor de desenvolvimento:
```bash
npm run dev
```

A aplicação estará disponível em: http://localhost:5173

## Mobile-First

O layout foi projetado para ser otimizado para dispositivos móveis, com largura máxima de 420px e centralização automática em telas maiores.


