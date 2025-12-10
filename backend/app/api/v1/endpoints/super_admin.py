"""
Endpoints de Super Admin para onboarding manual de tenants.

Estes endpoints são acessíveis apenas por usuários com role SUPER_ADMIN.
Permitem criar novos tenants e seus administradores de forma manual.
Também permitem listar e editar tenants existentes.
"""
from fastapi import APIRouter, HTTPException, Depends, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import secrets
import string
import logging

from app.core.database import get_db
from app.core.dependencies import get_super_admin_user
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.schedule_config import ScheduleConfig
from app.core.security import get_password_hash
from app.schemas.super_admin import OnboardTenantRequest, OnboardTenantResponse
from app.schemas.tenant import TenantResponse, TenantUpdate
from datetime import time

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])

logger = logging.getLogger(__name__)


def generate_temporary_password(length: int = 12) -> str:
    """
    Gera uma senha temporária aleatória e segura.
    
    Args:
        length: Comprimento da senha (padrão: 12)
        
    Returns:
        str: Senha temporária gerada
    """
    # Caracteres permitidos: letras, números e símbolos especiais
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


@router.post(
    "/onboard-tenant",
    response_model=OnboardTenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboarding de novo tenant",
    description=(
        "Cria um novo tenant (estúdio) e seu administrador em uma única transação atômica. "
        "Esta é a ÚNICA rota que permite criar novos tenants no sistema. "
        "Apenas usuários com role SUPER_ADMIN podem acessar este endpoint. "
        "Retorna o nome do tenant e as credenciais temporárias do administrador recém-criado."
    )
)
async def onboard_tenant(
    request_data: OnboardTenantRequest,
    super_admin: User = Depends(get_super_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria um novo tenant (estúdio) e seu administrador em uma transação atômica.
    
    PROPÓSITO EXCLUSIVO: Esta rota é dedicada exclusivamente ao onboarding manual de novos estúdios.
    Ela não deve ser usada para outras operações. Configurações do tenant após a criação
    são responsabilidade do Admin do estúdio através dos endpoints /admin/*.
    
    SEGURANÇA:
    - Protegida por Depends(get_super_admin_user), que verifica:
      1. Autenticação JWT válida (via get_current_admin_user)
      2. Role do usuário = SUPER_ADMIN
    - Retorna HTTP 403 se o usuário não for SUPER_ADMIN
    
    FLUXO DE CRIAÇÃO:
    1. Valida que o slug não existe (único no sistema)
    2. Valida que o email do admin não existe (único no sistema)
    3. Gera senha temporária segura se não fornecida
    4. Em uma transação atômica (tudo ou nada):
       a) Cria o Tenant com is_active=True
       b) Cria o User (Admin) com role TENANT_ADMIN vinculado ao tenant
    5. Retorna dados completos incluindo senha temporária
    
    TRANSAÇÃO ATÔMICA:
    - Se qualquer erro ocorrer durante a criação, toda a operação é revertida (rollback)
    - Garante que não haverá tenant sem admin ou admin sem tenant
    
    CREDENCIAIS TEMPORÁRIAS:
    - A senha temporária é retornada APENAS UMA VEZ nesta resposta
    - O Super Admin DEVE armazená-la de forma segura e entregá-la ao novo administrador
    - Recomenda-se que o administrador altere a senha no primeiro login
    
    Args:
        request_data: Dados do novo tenant e administrador (OnboardTenantRequest)
            - company_name: Nome da empresa/estúdio (usado apenas na resposta)
            - slug: Slug único do tenant (ex: 'estudio-bella')
            - admin_email: Email do administrador (único no sistema)
            - admin_name: Nome do administrador (opcional, não salvo)
            - notification_phone: Telefone para notificações (opcional)
            - password: Senha do admin (opcional, será gerada se não fornecida)
        super_admin: Usuário Super Admin autenticado (injetado via get_super_admin_user)
            - Garantido como SUPER_ADMIN pela dependência
        db: Sessão do banco de dados (injetada)
        
    Returns:
        OnboardTenantResponse: Resposta completa com:
            - tenant_id: UUID do tenant criado
            - tenant_slug: Slug do tenant (usado na URL pública)
            - company_name: Nome da empresa (do request)
            - admin_id: UUID do administrador criado
            - admin_email: Email do administrador
            - temporary_password: Senha temporária (IMPORTANTE: retornada apenas uma vez)
            - message: Mensagem de sucesso
        
    Raises:
        HTTPException 400: Se o slug ou email já existirem, ou dados inválidos
        HTTPException 401: Se o token JWT for inválido ou expirado
        HTTPException 403: Se o usuário não for SUPER_ADMIN
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Log da operação
        logger.info(
            f"Super Admin {super_admin.email} (ID: {super_admin.id}) iniciando onboarding de tenant: "
            f"slug='{request_data.slug}', company_name='{request_data.company_name}', "
            f"admin_email='{request_data.admin_email}'"
        )
        
        # Validação 1: Verificar se o slug já existe
        existing_tenant = await db.execute(
            select(Tenant).where(Tenant.slug == request_data.slug)
        )
        if existing_tenant.scalar_one_or_none():
            logger.warning(f"Tentativa de criar tenant com slug duplicado: '{request_data.slug}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slug '{request_data.slug}' já está em uso. Escolha outro slug único."
            )
        
        # Validação 2: Verificar se o email já existe
        existing_user = await db.execute(
            select(User).where(User.email == request_data.admin_email)
        )
        if existing_user.scalar_one_or_none():
            logger.warning(f"Tentativa de criar admin com email duplicado: '{request_data.admin_email}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{request_data.admin_email}' já está em uso por outro usuário."
            )
        
        # Gerar senha temporária se não fornecida
        if request_data.password:
            temporary_password = request_data.password
            password_was_generated = False
            logger.info(f"Senha fornecida pelo Super Admin para {request_data.admin_email}")
        else:
            temporary_password = generate_temporary_password()
            password_was_generated = True
            logger.info(f"Senha temporária gerada automaticamente para {request_data.admin_email}")
        
        # Hash da senha (usando bcrypt)
        password_hash = get_password_hash(temporary_password)
        
        # TRANSAÇÃO ATÔMICA: Criar Tenant, User e Configurações Padrão
        try:
            # Passo 1: Criar Tenant
            new_tenant = Tenant(
                slug=request_data.slug,
                name=request_data.company_name,  # Salvar o nome da empresa
                notification_phone_number=request_data.notification_phone,
                is_active=True
            )
            db.add(new_tenant)
            await db.flush()  # Para obter o ID do tenant sem fazer commit
            
            # Passo 2: Criar User (Admin) para o tenant
            new_admin = User(
                tenant_id=new_tenant.id,
                email=request_data.admin_email,
                password_hash=password_hash,
                role=UserRole.TENANT_ADMIN,
                is_active=True
            )
            db.add(new_admin)
            
            # Passo 3: Criar configurações de horário padrão para todos os dias da semana
            # Horário padrão: Segunda a Sexta (09:00 - 18:00), Sábado e Domingo fechados
            default_start_time = time(9, 0)  # 09:00
            default_end_time = time(18, 0)   # 18:00
            
            for day_of_week in range(7):  # 0=Segunda, 1=Terça, ..., 6=Domingo
                is_closed = day_of_week >= 5  # Sábado (5) e Domingo (6) fechados
                
                schedule_config = ScheduleConfig(
                    tenant_id=new_tenant.id,
                    day_of_week=day_of_week,
                    start_time=default_start_time if not is_closed else time(0, 0),
                    end_time=default_end_time if not is_closed else time(0, 0),
                    is_closed=is_closed
                )
                db.add(schedule_config)
            
            logger.info(
                f"Configurações de horário padrão criadas para tenant {new_tenant.slug}: "
                f"Segunda a Sexta (09:00-18:00), Sábado e Domingo (fechados)"
            )
            
            # Commit da transação (tudo é salvo junto ou nada)
            await db.commit()
            
            # Refresh para obter dados atualizados
            await db.refresh(new_tenant)
            await db.refresh(new_admin)
            
            logger.info(
                f"✅ Super Admin {super_admin.email} (ID: {super_admin.id}) criou com sucesso: "
                f"Tenant '{request_data.company_name}' (slug: '{new_tenant.slug}', ID: {new_tenant.id}) "
                f"com Admin {new_admin.email} (ID: {new_admin.id})"
            )
            
            # Construir mensagem de sucesso detalhada
            password_source = "gerada automaticamente" if password_was_generated else "definida pelo Super Admin"
            message = (
                f"Tenant '{request_data.company_name}' criado com sucesso. "
                f"Administrador '{request_data.admin_email}' criado. "
                f"Senha temporária {password_source}. "
                f"IMPORTANTE: A senha temporária é exibida apenas nesta resposta."
            )
            
            # Retornar resposta completa e clara
            response = OnboardTenantResponse(
                tenant_id=new_tenant.id,
                tenant_slug=new_tenant.slug,
                company_name=request_data.company_name,
                admin_id=new_admin.id,
                admin_email=new_admin.email,
                temporary_password=temporary_password,
                message=message
            )
            
            logger.info(
                f"📋 Credenciais temporárias retornadas para Super Admin {super_admin.email}: "
                f"tenant_slug='{new_tenant.slug}', admin_email='{new_admin.email}'"
            )
            
            return response
            
        except HTTPException:
            # Re-raise HTTPExceptions (validações já tratadas)
            await db.rollback()
            raise
        except Exception as e:
            # Rollback em caso de erro (garante atomicidade)
            await db.rollback()
            logger.error(
                f"❌ Erro ao criar tenant e admin (rollback executado): {str(e)}",
                exc_info=True,
                extra={
                    "super_admin_id": super_admin.id,
                    "super_admin_email": super_admin.email,
                    "requested_slug": request_data.slug,
                    "requested_admin_email": request_data.admin_email
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar tenant e administrador. A operação foi revertida. Detalhes: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTPExceptions (validações de slug/email duplicados)
        raise
    except Exception as e:
        logger.error(
            f"❌ Erro inesperado no onboarding: {str(e)}",
            exc_info=True,
            extra={
                "super_admin_id": super_admin.id if 'super_admin' in locals() else None,
                "super_admin_email": super_admin.email if 'super_admin' in locals() else None
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado durante o onboarding: {str(e)}"
        )


@router.get(
    "/tenants",
    response_model=List[TenantResponse],
    summary="Listar todos os tenants",
    description=(
        "Retorna uma lista de todos os tenants cadastrados no sistema. "
        "Apenas usuários com role SUPER_ADMIN podem acessar este endpoint."
    )
)
async def list_all_tenants(
    super_admin: User = Depends(get_super_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os tenants cadastrados no sistema.
    
    Esta rota permite ao Super Admin visualizar todos os estúdios cadastrados,
    incluindo informações como slug, nome, status de ativação, etc.
    
    Args:
        super_admin: Usuário Super Admin autenticado (injetado via get_super_admin_user)
        db: Sessão do banco de dados
        
    Returns:
        List[TenantResponse]: Lista de todos os tenants cadastrados
        
    Raises:
        HTTPException 401: Se o token JWT for inválido ou expirado
        HTTPException 403: Se o usuário não for SUPER_ADMIN
    """
    try:
        logger.info(f"Super Admin {super_admin.email} (ID: {super_admin.id}) listando todos os tenants")
        
        result = await db.execute(select(Tenant).order_by(Tenant.slug))
        tenants = result.scalars().all()
        
        logger.info(f"✅ {len(tenants)} tenant(s) encontrado(s)")
        
        return [TenantResponse.model_validate(tenant) for tenant in tenants]
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar tenants: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar tenants: {str(e)}"
        )


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Obter detalhes de um tenant",
    description=(
        "Retorna os detalhes completos de um tenant específico. "
        "Apenas usuários com role SUPER_ADMIN podem acessar este endpoint."
    )
)
async def get_tenant_details(
    tenant_id: UUID = Path(..., description="ID do tenant"),
    super_admin: User = Depends(get_super_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna os detalhes completos de um tenant específico.
    
    Args:
        tenant_id: UUID do tenant a ser consultado
        super_admin: Usuário Super Admin autenticado
        db: Sessão do banco de dados
        
    Returns:
        TenantResponse: Dados completos do tenant
        
    Raises:
        HTTPException 404: Se o tenant não for encontrado
        HTTPException 401: Se o token JWT for inválido ou expirado
        HTTPException 403: Se o usuário não for SUPER_ADMIN
    """
    try:
        logger.info(f"Super Admin {super_admin.email} consultando tenant {tenant_id}")
        
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant com ID {tenant_id} não encontrado"
            )
        
        return TenantResponse.model_validate(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao consultar tenant {tenant_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar tenant: {str(e)}"
        )


@router.put(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Atualizar um tenant",
    description=(
        "Permite ao Super Admin atualizar os dados de um tenant existente. "
        "Apenas usuários com role SUPER_ADMIN podem acessar este endpoint."
    )
)
async def update_tenant(
    tenant_id: UUID = Path(..., description="ID do tenant a ser atualizado"),
    tenant_data: TenantUpdate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza os dados de um tenant existente.
    
    Permite atualizar campos como:
    - slug (com validação de unicidade)
    - name, logo_url, description, address, phone_contact, schedule_display_text
    - whatsapp_phone_id, stripe_subscription_id
    - is_active (para ativar/desativar o tenant)
    
    IMPORTANTE: A atualização do slug é validada para garantir que não haja duplicatas.
    
    Args:
        tenant_id: UUID do tenant a ser atualizado
        tenant_data: Dados a serem atualizados (TenantUpdate)
        super_admin: Usuário Super Admin autenticado
        db: Sessão do banco de dados
        
    Returns:
        TenantResponse: Dados atualizados do tenant
        
    Raises:
        HTTPException 404: Se o tenant não for encontrado
        HTTPException 400: Se o slug já estiver em uso por outro tenant
        HTTPException 401: Se o token JWT for inválido ou expirado
        HTTPException 403: Se o usuário não for SUPER_ADMIN
    """
    try:
        logger.info(
            f"Super Admin {super_admin.email} (ID: {super_admin.id}) atualizando tenant {tenant_id}. "
            f"Dados: {tenant_data.model_dump(exclude_unset=True)}"
        )
        
        # Buscar tenant
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant com ID {tenant_id} não encontrado"
            )
        
        # Validar slug se estiver sendo atualizado
        if tenant_data.slug is not None and tenant_data.slug != tenant.slug:
            existing_tenant = await db.execute(
                select(Tenant).where(Tenant.slug == tenant_data.slug, Tenant.id != tenant_id)
            )
            if existing_tenant.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Slug '{tenant_data.slug}' já está em uso por outro tenant."
                )
            tenant.slug = tenant_data.slug
            logger.info(f"Slug atualizado para: {tenant_data.slug}")
        
        # Atualizar outros campos
        update_data = tenant_data.model_dump(exclude_unset=True, exclude={'slug'})
        for field, value in update_data.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)
                logger.debug(f"Campo '{field}' atualizado para: {value}")
        
        # Salvar alterações
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"✅ Tenant {tenant_id} atualizado com sucesso por Super Admin {super_admin.email}")
        
        return TenantResponse.model_validate(tenant)
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Erro ao atualizar tenant {tenant_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar tenant: {str(e)}"
        )

