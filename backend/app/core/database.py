"""
Configuração e conexão com o banco de dados PostgreSQL usando SQLAlchemy Async.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Engine assíncrono
# A URL do Render virá como 'postgresql://...', mudamos para 'postgresql+asyncpg://...'
def get_database_url():
    """Converte a URL do banco de dados para o formato asyncpg."""
    db_url = settings.DATABASE_URL
    print(f"🔍 DATABASE_URL original: {db_url[:50]}...")  # Mostrar apenas primeiros 50 chars por segurança
    
    # Se já tem postgresql+asyncpg://, usar direto
    if "postgresql+asyncpg://" in db_url:
        print("✅ URL já está no formato postgresql+asyncpg://")
        return db_url
    
    # Se tem postgresql://, converter para postgresql+asyncpg://
    if "postgresql://" in db_url:
        converted_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        print(f"✅ URL convertida para: {converted_url[:50]}...")
        return converted_url
    
    # Se tem postgres:// (sem 'ql'), também converter
    if "postgres://" in db_url:
        converted_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        print(f"✅ URL convertida de postgres:// para: {converted_url[:50]}...")
        return converted_url
    
    # Se não reconheceu, retornar como está (pode causar erro, mas pelo menos sabemos)
    print(f"⚠️ URL não reconhecida, usando como está: {db_url[:50]}...")
    return db_url

database_url = get_database_url()

try:
    engine = create_async_engine(
        database_url,
        echo=True,  # Log SQL queries (desabilitar em produção)
        future=True,
    )
    print("✅ Engine SQLAlchemy criado com sucesso!")
except Exception as e:
    print(f"❌ ERRO ao criar engine SQLAlchemy: {e}")
    import traceback
    print(traceback.format_exc())
    raise

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


