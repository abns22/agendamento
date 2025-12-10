# Dockerfile Multi-Stage para Frontend React/Vite
# Stage 1: Build da aplicação
FROM node:20-alpine AS builder

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY package.json package-lock.json ./

# Instalar dependências (incluindo devDependencies para o build)
RUN npm ci

# Copiar código fonte
COPY . .

# Executar build da aplicação
# O Vite gera os arquivos estáticos no diretório /dist
RUN npm run build

# Stage 2: Servir com Nginx
FROM nginx:stable-alpine

# Copiar arquivos estáticos do stage de build para o diretório do Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuração customizada do Nginx para SPA (Single Page Application)
# Isso garante que todas as rotas sejam redirecionadas para index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expor porta padrão do Nginx
EXPOSE 80

# Nginx já inicia automaticamente, mas podemos especificar explicitamente
CMD ["nginx", "-g", "daemon off;"]

