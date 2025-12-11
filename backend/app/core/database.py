"""
Configuração e conexão com o banco de dados PostgreSQL usando SQLAlchemy Async.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Engine assíncrono
# A URL do Render virá como 'postgresql://...', mudamos para 'postgresql+asyncpg://...'
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,  # Log SQL queries (desabilitar em produção)
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base para os modelos
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency para obter uma sessão do banco de dados.
    Usado em rotas FastAPI via Depends(get_db).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


