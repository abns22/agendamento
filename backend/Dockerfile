# Dockerfile para Backend FastAPI
# Imagem base oficial do Python
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Variáveis de ambiente para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependências do sistema (necessárias para algumas bibliotecas Python)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivo de dependências
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código da aplicação
COPY app/ ./app/
COPY pytest.ini .

# Criar diretório para uploads (se necessário)
RUN mkdir -p uploads/logos

# Expor porta padrão do Uvicorn
EXPOSE 8000

# Comando de execução em modo produção
# Usando uvicorn com workers para melhor performance
# --host 0.0.0.0 para aceitar conexões de qualquer IP
# --workers 4 para múltiplos workers (ajuste conforme necessário)
# Sem --reload em produção
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

