"""
Serviço de Autenticação.

Isola a lógica de autenticação, hashing de senha e geração de tokens JWT.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import uuid
from typing import Optional, Tuple
from datetime import timedelta

from app.models.user import User
from app.models.tenant import Tenant
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.config import settings


class AuthService:
    """
    Serviço responsável por autenticação de usuários.
    """
    
    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str,
        tenant_id: Optional[UUID] = None,
        tenant_slug: Optional[str] = None
    ) -> Tuple[User, Tenant]:
        """
        Registra um novo usuário.
        
        Se tenant_id for fornecido, anexa o usuário ao tenant existente.
        Se tenant_slug for fornecido, busca o tenant pelo slug.
        Se nenhum for fornecido, cria um novo tenant.
        
        Args:
            db: Sessão do banco de dados
            email: Email do usuário
            password: Senha em texto plano
            tenant_id: UUID do tenant existente (opcional)
            tenant_slug: Slug do tenant existente (opcional)
            
        Returns:
            Tuple[User, Tenant]: Usuário criado e tenant associado
            
        Raises:
            ValueError: Se o email já existir ou dados inválidos
        """
        # Verificar se o email já existe
        existing_user = await db.execute(
            select(User).where(User.email == email)
        )
        if existing_user.scalar_one_or_none():
            raise ValueError("Email já está em uso")
        
        # Obter ou criar tenant
        tenant = None
        
        if tenant_id:
            # Buscar tenant existente por ID
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            if not tenant:
                raise ValueError("Tenant não encontrado")
        
        elif tenant_slug:
            # Buscar tenant existente por slug
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.slug == tenant_slug)
            )
            tenant = tenant_result.scalar_one_or_none()
            if not tenant:
                raise ValueError("Tenant não encontrado")
        
        else:
            # Criar novo tenant (primeira vez)
            # Gerar slug a partir do email (ex: user@example.com -> user-example-com)
            slug_base = email.split("@")[0].replace(".", "-")
            slug = f"{slug_base}-{uuid.uuid4().hex[:8]}"
            
            tenant = Tenant(
                slug=slug,
                is_active=True
            )
            db.add(tenant)
            await db.flush()  # Para obter o ID do tenant
        
        # Criar usuário
        password_hash = get_password_hash(password)
        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=password_hash,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await db.refresh(tenant)
        
        return user, tenant
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Autentica um usuário com email e senha.
        
        Args:
            db: Sessão do banco de dados
            email: Email do usuário
            password: Senha em texto plano
            
        Returns:
            User se as credenciais forem válidas, None caso contrário
        """
        # Buscar usuário por email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Verificar se está ativo
        if not user.is_active:
            return None
        
        # Verificar senha
        try:
            if not verify_password(password, user.password_hash):
                return None
        except (ValueError, Exception) as e:
            # Log do erro para debug
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao verificar senha: {str(e)}")
            # Se houver erro na verificação (hash corrompido, etc), retornar None
            return None
        
        return user
    
    @staticmethod
    def create_tokens(user: User) -> Tuple[str, str]:
        """
        Cria tokens JWT (access e refresh) para um usuário.
        
        Args:
            user: Objeto User
            
        Returns:
            Tuple[str, str]: (access_token, refresh_token)
        """
        # Payload do token de acesso
        access_token_data = {
            "sub": str(user.id),  # subject (user_id)
            "email": user.email,
            "tenant_id": str(user.tenant_id),
            "role": user.role.value
        }
        
        # Payload do refresh token (sem dados sensíveis)
        refresh_token_data = {
            "sub": str(user.id)
        }
        
        # Criar tokens
        access_token = create_access_token(access_token_data)
        refresh_token = create_refresh_token(refresh_token_data)
        
        return access_token, refresh_token
    
    @staticmethod
    async def get_user_from_token(
        db: AsyncSession,
        token: str,
        token_type: str = "access"
    ) -> Optional[User]:
        """
        Obtém um usuário a partir de um token JWT.
        
        Args:
            db: Sessão do banco de dados
            token: JWT token string
            token_type: Tipo do token ("access" ou "refresh")
            
        Returns:
            User se o token for válido, None caso contrário
        """
        try:
            payload = decode_token(token)
            
            # Verificar tipo do token
            if payload.get("type") != token_type:
                return None
            
            # Extrair user_id
            user_id_str = payload.get("sub")
            if not user_id_str:
                return None
            
            # Validar formato UUID (mas usar string para MySQL)
            try:
                UUID(user_id_str)  # Validar formato
            except ValueError:
                return None
            
            # Buscar usuário (MySQL armazena UUIDs como String(36))
            result = await db.execute(
                select(User).where(
                    User.id == user_id_str,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()
            
            return user
            
        except Exception:
            return None

