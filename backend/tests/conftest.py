"""
Configuração de fixtures para testes de integração.
"""
import pytest
import asyncio
import inspect
from typing import AsyncGenerator, Optional, Any
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import Depends

from app.main import app
from app.core.database import get_db, Base
from app.core.security import create_access_token
from app.core.dependencies import get_current_admin_user, get_current_active_tenant
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.service import Service
from app.models.appointment import Appointment, AppointmentStatus
from app.models.transaction import Transaction
from app.models.payment_entry import PaymentEntry
from app.models.payment_method_config import PaymentMethodConfig
from app.models.expense import Expense
from app.core.config import settings


# Configurar banco de teste (usar o mesmo banco ou criar um separado)
# Para testes, vamos usar o mesmo banco mas com isolamento por tenant
TEST_DATABASE_URL = settings.DATABASE_URL

# Criar engine de teste
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

# Criar sessionmaker de teste
TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture para criar uma sessão de banco de dados de teste.
    Cada teste recebe uma nova sessão que é fechada após o teste.
    """
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Ignorar erros de rollback/close no teardown (problema conhecido com event loop no Windows)
            try:
                await session.rollback()
            except Exception:
                pass  # Ignorar erros de rollback no teardown
            try:
                await session.close()
            except Exception:
                pass  # Ignorar erros de close no teardown


def create_override_get_current_admin_user(mock_user: User):
    """
    Cria uma função override para get_current_admin_user com o usuário mockado.
    Retorna o objeto SQLAlchemy User diretamente, que será convertido automaticamente
    pelo FastAPI usando from_attributes=True do schema UserResponse.
    
    IMPORTANTE: Não usar anotações de tipo que o FastAPI possa analisar incorretamente.
    """
    async def override_get_current_admin_user(token=None, db=None):
        # Retornar o objeto SQLAlchemy User diretamente
        # O FastAPI converterá automaticamente usando from_attributes=True do UserResponse
        # Os parâmetros token e db são ignorados quando fazemos override
        return mock_user
    # Remover todas as anotações de tipo para evitar análise incorreta pelo FastAPI
    override_get_current_admin_user.__annotations__ = {}
    return override_get_current_admin_user


def create_override_get_current_active_tenant(mock_tenant: Tenant, mock_user: User):
    """
    Cria uma função override para get_current_active_tenant com o tenant mockado.
    Retorna o objeto SQLAlchemy Tenant diretamente, que será convertido automaticamente
    pelo FastAPI usando from_attributes=True do schema TenantResponse.
    
    IMPORTANTE: Não usar anotações de tipo que o FastAPI possa analisar incorretamente.
    """
    async def override_get_current_active_tenant(current_user=None, db=None):
        # Retornar o objeto SQLAlchemy Tenant diretamente
        # O FastAPI converterá automaticamente usando from_attributes=True do TenantResponse
        # Os parâmetros current_user e db são ignorados quando fazemos override
        return mock_tenant
    # Remover todas as anotações de tipo para evitar análise incorreta pelo FastAPI
    override_get_current_active_tenant.__annotations__ = {}
    return override_get_current_active_tenant


@pytest.fixture(scope="function")
def test_client(db_session: AsyncSession) -> TestClient:
    """
    Fixture base para criar um cliente de teste do FastAPI.
    Substitui apenas a dependência get_db.
    """
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Fazer override apenas do get_db
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    yield client
    
    # Limpar overrides após o teste
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client_a(test_client: TestClient, admin_user_a: User, tenant_a: Tenant, db_session: AsyncSession) -> TestClient:
    """
    Fixture que retorna um cliente de teste autenticado com o Admin A.
    """
    # Criar overrides específicos para este usuário
    override_user = create_override_get_current_admin_user(admin_user_a)
    override_tenant = create_override_get_current_active_tenant(tenant_a, admin_user_a)
    
    # Aplicar overrides
    app.dependency_overrides[get_current_admin_user] = override_user
    app.dependency_overrides[get_current_active_tenant] = override_tenant
    
    yield test_client
    
    # Limpar overrides específicos (get_db já é limpo pela fixture test_client)
    if get_current_admin_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_admin_user]
    if get_current_active_tenant in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_tenant]


@pytest.fixture(scope="function")
def authenticated_client_b(test_client: TestClient, admin_user_b: User, tenant_b: Tenant, db_session: AsyncSession) -> TestClient:
    """
    Fixture que retorna um cliente de teste autenticado com o Admin B.
    """
    # Criar overrides específicos para este usuário
    override_user = create_override_get_current_admin_user(admin_user_b)
    override_tenant = create_override_get_current_active_tenant(tenant_b, admin_user_b)
    
    # Aplicar overrides
    app.dependency_overrides[get_current_admin_user] = override_user
    app.dependency_overrides[get_current_active_tenant] = override_tenant
    
    yield test_client
    
    # Limpar overrides específicos (get_db já é limpo pela fixture test_client)
    if get_current_admin_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_admin_user]
    if get_current_active_tenant in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_tenant]


@pytest.fixture(scope="function")
async def tenant_a(db_session: AsyncSession) -> Tenant:
    """Cria um tenant A para testes."""
    tenant_id = str(uuid4())
    tenant = Tenant(
        id=tenant_id,
        slug=f"tenant-a-{uuid4().hex[:8]}",
        name="Tenant A",
        is_active=True
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
async def tenant_b(db_session: AsyncSession) -> Tenant:
    """Cria um tenant B para testes."""
    tenant_id = str(uuid4())
    tenant = Tenant(
        id=tenant_id,
        slug=f"tenant-b-{uuid4().hex[:8]}",
        name="Tenant B",
        is_active=True
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
async def admin_user_a(db_session: AsyncSession, tenant_a: Tenant) -> User:
    """Cria um usuário admin para o Tenant A."""
    user_id = str(uuid4())
    user = User(
        id=user_id,
        tenant_id=str(tenant_a.id),
        email=f"admin-a-{uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def admin_user_b(db_session: AsyncSession, tenant_b: Tenant) -> User:
    """Cria um usuário admin para o Tenant B."""
    user_id = str(uuid4())
    user = User(
        id=user_id,
        tenant_id=str(tenant_b.id),
        email=f"admin-b-{uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def token_a(admin_user_a: User) -> str:
    """Gera um token JWT para o Admin A."""
    token_data = {
        "sub": str(admin_user_a.id),
        "tenant_id": str(admin_user_a.tenant_id),
        "email": admin_user_a.email
    }
    return create_access_token(token_data)


@pytest.fixture(scope="function")
def token_b(admin_user_b: User) -> str:
    """Gera um token JWT para o Admin B."""
    token_data = {
        "sub": str(admin_user_b.id),
        "tenant_id": str(admin_user_b.tenant_id),
        "email": admin_user_b.email
    }
    return create_access_token(token_data)


@pytest.fixture(scope="function")
async def service_with_promotion(db_session: AsyncSession, tenant_a: Tenant) -> Service:
    """Cria um serviço com promoção ativa para testes."""
    service_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    service = Service(
        id=service_id,
        tenant_id=str(tenant_a.id),
        name="Serviço com Promoção",
        duration_minutes=60,
        price=Decimal("100.00"),
        fixed_cost_value=Decimal("30.00"),  # Custo fixo
        is_promotional=True,
        promotional_value=Decimal("80.00"),  # Valor promocional (20% de desconto)
        promotion_start_date=now - timedelta(days=1),
        promotion_end_date=now + timedelta(days=1)
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    return service


@pytest.fixture(scope="function")
async def payment_method_credit_card(db_session: AsyncSession, tenant_a: Tenant) -> PaymentMethodConfig:
    """Cria uma forma de pagamento com taxa (Cartão de Débito 5%)."""
    method_id = str(uuid4())
    method = PaymentMethodConfig(
        id=method_id,
        tenant_id=str(tenant_a.id),
        method_name="Cartão de Débito",
        debit_tax_type="%",
        debit_tax_value=Decimal("5.00")  # 5% de taxa
    )
    db_session.add(method)
    await db_session.commit()
    await db_session.refresh(method)
    return method


@pytest.fixture(scope="function")
async def payment_method_cash(db_session: AsyncSession, tenant_a: Tenant) -> PaymentMethodConfig:
    """Cria uma forma de pagamento sem taxa (Dinheiro)."""
    method_id = str(uuid4())
    method = PaymentMethodConfig(
        id=method_id,
        tenant_id=str(tenant_a.id),
        method_name="Dinheiro"
    )
    db_session.add(method)
    await db_session.commit()
    await db_session.refresh(method)
    return method

