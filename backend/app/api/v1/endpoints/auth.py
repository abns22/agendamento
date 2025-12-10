"""
Endpoints de autenticação e autorização.

Gerencia registro, login e validação de tokens JWT para administradores do estúdio.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme para JWT Bearer tokens
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependência para obter o usuário atual a partir do token JWT.
    
    Valida o token e retorna o usuário autenticado.
    
    Args:
        credentials: Credenciais HTTP Bearer (token JWT)
        db: Sessão do banco de dados
        
    Returns:
        User: Usuário autenticado
        
    Raises:
        HTTPException: 401 se o token for inválido ou o usuário não existir
    """
    token = credentials.credentials
    
    user = await AuthService.get_user_from_token(db, token, token_type="access")
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário",
    description="Cria um novo usuário administrador. Se não fornecer tenant_id ou tenant_slug, cria um novo tenant."
)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Registra um novo usuário administrador.
    
    Fluxo:
    1. Valida que o email não está em uso
    2. Se tenant_id ou tenant_slug for fornecido, anexa ao tenant existente
    3. Se não, cria um novo tenant
    4. Cria o usuário com senha hasheada
    5. Retorna o usuário criado
    
    Args:
        user_data: Dados do usuário (UserRegister)
        db: Sessão do banco de dados
        
    Returns:
        UserResponse: Usuário criado
        
    Raises:
        HTTPException 400: Se o email já estiver em uso ou dados inválidos
        HTTPException 500: Erro interno do servidor
    """
    try:
        user, tenant = await AuthService.register_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            tenant_id=user_data.tenant_id,
            tenant_slug=user_data.tenant_slug
        )
        
        return UserResponse.model_validate(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar usuário: {str(e)}"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login de usuário",
    description="Autentica um usuário e retorna tokens JWT (access e refresh)."
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Autentica um usuário e retorna tokens JWT.
    
    Fluxo:
    1. Valida email e senha
    2. Se válido, gera tokens JWT (access e refresh)
    3. Retorna os tokens
    
    O access token contém:
    - user_id (sub)
    - email
    - tenant_id (crucial para isolamento multi-tenant)
    - role
    
    Args:
        credentials: Credenciais de login (UserLogin)
        db: Sessão do banco de dados
        
    Returns:
        TokenResponse: Tokens JWT (access e refresh)
        
    Raises:
        HTTPException 401: Se as credenciais forem inválidas
    """
    user = await AuthService.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Gerar tokens
    access_token, refresh_token = AuthService.create_tokens(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obter usuário atual",
    description="Retorna os dados do usuário autenticado (rota protegida)."
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Retorna os dados do usuário autenticado.
    
    Esta rota é protegida e requer um token JWT válido no header Authorization.
    
    Args:
        current_user: Usuário autenticado (injetado via get_current_user)
        
    Returns:
        UserResponse: Dados do usuário autenticado
    """
    return UserResponse.model_validate(current_user)


