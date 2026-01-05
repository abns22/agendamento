"""
Injeção de Dependências do FastAPI.
Inclui a função crítica para obter o Tenant a partir do header HTTP.
"""
from fastapi import Header, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.core.security import decode_token
from sqlalchemy import select


async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> UUID:
    """
    Extrai o tenant_id do cabeçalho HTTP X-Tenant-ID.
    
    Args:
        x_tenant_id: Valor do header X-Tenant-ID
        
    Returns:
        UUID do tenant
        
    Raises:
        HTTPException: 400 se o header não for fornecido ou inválido
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Header X-Tenant-ID é obrigatório"
        )
    
    try:
        tenant_uuid = UUID(x_tenant_id)
        return tenant_uuid
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="X-Tenant-ID deve ser um UUID válido"
        )


async def get_active_tenant(
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Obtém o Tenant ativo a partir do tenant_id do header.
    Esta é a dependência principal para garantir isolamento multi-tenant.
    
    Args:
        tenant_id: UUID do tenant (extraído do header)
        db: Sessão do banco de dados
        
    Returns:
        Objeto Tenant se estiver ativo
        
    Raises:
        HTTPException: 403 se o tenant não existir ou não estiver ativo
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.is_active == True
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=403,
            detail="Tenant não encontrado ou inativo"
        )
    
    return tenant


# OAuth2 scheme para JWT Bearer tokens
# auto_error=False permite que requisições OPTIONS (preflight) passem sem erro
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_admin_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependência para obter o usuário administrador autenticado a partir do JWT.
    
    Esta função:
    1. Obtém o JWT do cabeçalho Authorization (Bearer Token) via OAuth2PasswordBearer
    2. Decodifica e valida o token usando AuthService
    3. Extrai user_id e tenant_id do payload
    4. Busca o usuário ativo no banco de dados
    5. Retorna o objeto User
    
    Esta dependência deve ser usada em todos os endpoints administrativos para garantir
    autenticação e isolamento multi-tenant.
    
    Exemplo de uso:
        @router.get("/admin/services")
        async def list_services(
            current_user: User = Depends(get_current_admin_user),
            db: AsyncSession = Depends(get_db)
        ):
            # current_user já contém user_id e tenant_id
            ...
    
    Args:
        token: JWT token extraído do header Authorization (Bearer)
        db: Sessão do banco de dados
        
    Returns:
        User: Usuário autenticado e ativo
        
    Raises:
        HTTPException 401: Se o token for inválido, expirado, ou o usuário não existir/inativo
    """
    try:
        # Decodificar token
        payload = decode_token(token)
        
        # Verificar tipo do token (deve ser access)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tipo de token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extrair user_id do payload (campo "sub")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: user_id não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extrair tenant_id do payload (para validação adicional)
        tenant_id_str = payload.get("tenant_id")
        if not tenant_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: tenant_id não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validar formato de UUID (mas manter como string para MySQL)
        try:
            # Validar que são UUIDs válidos
            UUID(user_id_str)
            UUID(tenant_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: formato de ID incorreto",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Buscar usuário no banco de dados
        # Nota: MySQL armazena UUIDs como String(36), então comparamos diretamente
        result = await db.execute(
            select(User).where(
                User.id == user_id_str,
                User.tenant_id == tenant_id_str,
                User.is_active == True
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais Inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validação adicional: verificar se o tenant está ativo
        tenant_result = await db.execute(
            select(Tenant).where(
                Tenant.id == tenant_id_str,
                Tenant.is_active == True
            )
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant não encontrado ou inativo"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        # Qualquer outro erro (JWT inválido, expirado, etc.)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais Inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_tenant(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Dependência para obter o tenant ativo do usuário autenticado.
    
    Esta função obtém o tenant a partir do usuário autenticado via JWT.
    Deve ser usada em conjunto com get_current_admin_user.
    
    IMPORTANTE: Esta dependência automaticamente usa get_current_admin_user,
    então você não precisa injetar ambas separadamente.
    
    Exemplo:
        @router.get("/endpoint")
        async def my_endpoint(
            tenant: Tenant = Depends(get_current_active_tenant)
        ):
            # O tenant já está garantido como ativo e do usuário autenticado
            ...
    
    Args:
        current_user: Usuário autenticado (injetado automaticamente via get_current_admin_user)
        db: Sessão do banco de dados
        
    Returns:
        Tenant ativo do usuário autenticado
        
    Raises:
        HTTPException: 401 se não autenticado
        HTTPException: 403 se tenant inativo
    """
    # Buscar tenant do usuário
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == current_user.tenant_id,
            Tenant.is_active == True
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não encontrado ou inativo"
        )
    
    return tenant


async def get_super_admin_user(
    current_user: User = Depends(get_current_admin_user)
) -> User:
    """
    Dependência para verificar se o usuário é Super Admin.
    
    Esta dependência garante que apenas usuários com role SUPER_ADMIN
    possam acessar endpoints críticos do sistema.
    
    IMPORTANTE: Esta dependência usa get_current_admin_user internamente,
    então o usuário já está autenticado. Apenas verifica a role.
    
    Exemplo de uso:
        @router.post("/super-admin/onboard-tenant")
        async def onboard_tenant(
            super_admin: User = Depends(get_super_admin_user),
            db: AsyncSession = Depends(get_db)
        ):
            # super_admin é garantido como SUPER_ADMIN
            ...
    
    Args:
        current_user: Usuário autenticado (injetado via get_current_admin_user)
        
    Returns:
        User: Usuário autenticado com role SUPER_ADMIN
        
    Raises:
        HTTPException 403: Se o usuário não for SUPER_ADMIN
    """
    # Verificar se o usuário é SUPER_ADMIN
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas Super Administradores podem acessar este recurso."
        )
    
    return current_user


async def verify_subscription_access(
    tenant: Tenant = Depends(get_current_active_tenant)
) -> Tenant:
    """
    Middleware de verificação de assinatura.
    
    Verifica se o tenant tem assinatura ativa antes de permitir acesso às rotas.
    
    Lógica (em ordem de prioridade):
    1. PRIORIDADE MÁXIMA: Se is_exempt for True, permite acesso imediatamente (isento de pagamento)
    2. Se subscription_status for 'active', permite acesso
    3. Se subscription_status não for 'active' E a data atual for maior que 
       current_period_end + 3 dias (carência), bloqueia com erro 402 Payment Required
    4. Se estiver dentro do período de carência (até 3 dias após current_period_end), permite acesso
    
    IMPORTANTE: Esta dependência deve ser aplicada em todas as rotas administrativas,
    EXCETO nas rotas de autenticação (login, register) e pagamento (billing).
    
    Exemplo de uso:
        @router.get("/admin/services")
        async def list_services(
            tenant: Tenant = Depends(verify_subscription_access),
            db: AsyncSession = Depends(get_db)
        ):
            # Só chega aqui se a assinatura estiver ativa ou dentro da carência
            ...
    
    Args:
        tenant: Tenant autenticado (injetado via get_current_active_tenant)
        
    Returns:
        Tenant: Tenant com assinatura válida
        
    Raises:
        HTTPException 402: Se a assinatura não estiver ativa e estiver fora do período de carência
    """
    # PRIORIDADE 1: Verificar se o tenant está isento de pagamento
    # Se is_exempt for True, permite acesso imediatamente (antes de qualquer verificação)
    if tenant.is_exempt:
        return tenant
    
    # PRIORIDADE 2: Se o status for 'active', permite acesso imediatamente
    if tenant.subscription_status == 'active':
        return tenant
    
    # Se não houver current_period_end definido, permite acesso (tenant novo ou sem assinatura configurada)
    if not tenant.current_period_end:
        # Se está em trial e ainda não expirou, permite
        if tenant.trial_ends_at and datetime.utcnow() <= tenant.trial_ends_at:
            return tenant
        # Se não tem período definido e não está em trial, permite acesso (será bloqueado quando configurar)
        return tenant
    
    # Calcular data limite (current_period_end + 3 dias de carência)
    grace_period_end = tenant.current_period_end + timedelta(days=3)
    current_time = datetime.utcnow()
    
    # Se ainda está dentro do período de carência, permite acesso
    if current_time <= grace_period_end:
        return tenant
    
    # Se passou do período de carência e não está ativo, bloqueia acesso
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Assinatura inativa ou expirada. Por favor, renove sua assinatura para continuar usando o sistema.",
        headers={"X-Subscription-Status": tenant.subscription_status or "unknown"}
    )

