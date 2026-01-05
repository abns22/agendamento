"""
Endpoints administrativos para gerenciamento de Clientes (CRM Básico).

Estes endpoints requerem autenticação e garantem isolamento multi-tenant.
Apenas clientes do tenant autenticado podem ser acessados.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, extract, func
from uuid import UUID
from typing import Annotated, List, Optional
from datetime import date, datetime

from app.core.database import get_db
from app.core.dependencies import verify_subscription_access
from app.models.tenant import Tenant
from app.models.client import Client

from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse, BirthdayClientResponse

router = APIRouter(prefix="/admin/clients", tags=["Admin - Clients"])


@router.get(
    "/search",
    response_model=List[ClientResponse],
    summary="Buscar clientes (autocomplete)",
    description="Busca rápida de clientes por nome ou telefone. Retorna no máximo 10 resultados para autocomplete."
)
async def search_clients(
    q: str = Query(..., min_length=1, description="Termo de busca (nome ou telefone)"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Busca rápida de clientes para autocomplete.
    
    Busca clientes por nome ou telefone usando busca parcial (ILIKE).
    Retorna no máximo 10 resultados para manter a performance.
    
    Args:
        q: Termo de busca (mínimo 1 caractere)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[ClientResponse]: Lista de até 10 clientes encontrados
        
    Exemplo:
        GET /api/v1/admin/clients/search?q=joão
        - Busca clientes com "joão" no nome ou telefone
    """
    tenant_id_str = str(tenant.id)
    
    # Normalizar termo de busca (lowercase para busca case-insensitive)
    search_term = f"%{q.lower()}%"
    
    # Buscar clientes do tenant por nome ou telefone
    query = select(Client).where(
        and_(
            Client.tenant_id == tenant_id_str,
            or_(
                func.lower(Client.name).like(search_term),
                func.lower(Client.phone_number).like(search_term)
            )
        )
    ).order_by(
        Client.name.asc()
    ).limit(10)  # Limitar a 10 resultados para performance
    
    result = await db.execute(query)
    clients = result.scalars().all()
    
    return [ClientResponse.model_validate(client) for client in clients]


@router.get(
    "",
    response_model=List[ClientResponse],
    summary="Listar clientes",
    description="Retorna todos os clientes do tenant autenticado, opcionalmente filtrados por nome/telefone ou mês de aniversário."
)
async def list_clients(
    search: Optional[str] = Query(None, description="Buscar por nome ou telefone (busca parcial)"),
    birth_month: Optional[int] = Query(None, ge=1, le=12, description="Filtrar aniversariantes do mês (1-12, onde 1=Janeiro, 12=Dezembro)"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os clientes do tenant autenticado.
    
    Permite buscar por nome ou telefone e filtrar por mês de aniversário.
    
    Args:
        search: Termo de busca parcial por nome ou telefone (opcional)
        birth_month: Mês de aniversário para filtrar (1-12, opcional)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[ClientResponse]: Lista de clientes do tenant
        
    Exemplos:
        - GET /api/v1/admin/clients?search=joão - Busca clientes com "joão" no nome ou telefone
        - GET /api/v1/admin/clients?birth_month=5 - Lista aniversariantes de maio
        - GET /api/v1/admin/clients?search=maria&birth_month=12 - Busca "maria" que faz aniversário em dezembro
    """
    tenant_id_str = str(tenant.id)
    
    query = select(Client).where(Client.tenant_id == tenant_id_str)
    
    # Aplicar filtro de busca se fornecido
    # PostgreSQL suporta ilike, mas vamos usar func.lower() para compatibilidade
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Client.name).like(search_term),
                func.lower(Client.phone_number).like(search_term)
            )
        )
    
    # Aplicar filtro de mês de aniversário se fornecido
    # Usar EXTRACT(MONTH FROM birth_date) para PostgreSQL
    if birth_month is not None:
        # Filtrar apenas clientes que têm data de nascimento e o mês corresponde
        query = query.where(
            and_(
                Client.birth_date.isnot(None),
                extract('month', Client.birth_date) == birth_month
            )
        )
    
    # Ordenação:
    # - Se birth_month estiver ativo, ordenar por dia do nascimento (dia do mês)
    # - Caso contrário, ordenar por nome (alfabética)
    if birth_month is not None:
        # Ordenar por dia do mês do nascimento (1-31), depois por nome
        query = query.order_by(
            extract('day', Client.birth_date).asc(),
            Client.name.asc()
        )
    else:
        # Ordenar alfabeticamente por nome
        query = query.order_by(Client.name.asc())
    
    result = await db.execute(query)
    clients = result.scalars().all()
    
    return [ClientResponse.model_validate(client) for client in clients]


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Obter cliente",
    description="Retorna um cliente específico do tenant autenticado."
)
async def get_client(
    client_id: UUID = Path(..., description="UUID do cliente"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtém um cliente específico do tenant autenticado.
    
    Args:
        client_id: UUID do cliente
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ClientResponse: Cliente encontrado
        
    Raises:
        HTTPException 404: Se o cliente não for encontrado ou não pertencer ao tenant
    """
    client_id_str = str(client_id)
    tenant_id_str = str(tenant.id)
    
    result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id_str,
                Client.tenant_id == tenant_id_str
            )
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado ou não pertence a este estúdio"
        )
    
    return ClientResponse.model_validate(client)


@router.post(
    "",
    response_model=ClientResponse,
    status_code=201,
    summary="Criar cliente",
    description="Cria um novo cliente para o tenant autenticado."
)
async def create_client(
    client_data: ClientCreate,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria um novo cliente para o tenant autenticado.
    
    Args:
        client_data: Dados do cliente a ser criado
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ClientResponse: Cliente criado
    """
    tenant_id_str = str(tenant.id)
    
    # Verificar se já existe cliente com mesmo telefone no tenant
    existing_client = await db.execute(
        select(Client).where(
            and_(
                Client.tenant_id == tenant_id_str,
                Client.phone_number == client_data.phone_number
            )
        )
    )
    if existing_client.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Já existe um cliente cadastrado com este telefone"
        )
    
    new_client = Client(
        tenant_id=tenant_id_str,
        name=client_data.name,
        phone_number=client_data.phone_number,
        email=client_data.email,
        birth_date=client_data.birth_date
    )
    
    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)
    
    return ClientResponse.model_validate(new_client)


@router.put(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Atualizar cliente",
    description="Atualiza um cliente existente do tenant autenticado."
)
async def update_client(
    client_id: UUID = Path(..., description="UUID do cliente"),
    client_data: ClientUpdate = ...,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza um cliente existente do tenant autenticado.
    
    Args:
        client_id: UUID do cliente
        client_data: Dados atualizados do cliente
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ClientResponse: Cliente atualizado
        
    Raises:
        HTTPException 404: Se o cliente não for encontrado ou não pertencer ao tenant
    """
    client_id_str = str(client_id)
    tenant_id_str = str(tenant.id)
    
    result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id_str,
                Client.tenant_id == tenant_id_str
            )
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado ou não pertence a este estúdio"
        )
    
    # Verificar se o novo telefone já está em uso por outro cliente
    update_data = client_data.model_dump(exclude_unset=True)
    if 'phone_number' in update_data:
        existing_client = await db.execute(
            select(Client).where(
                and_(
                    Client.tenant_id == tenant_id_str,
                    Client.phone_number == update_data['phone_number'],
                    Client.id != client_id_str
                )
            )
        )
        if existing_client.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Já existe outro cliente cadastrado com este telefone"
            )
    
    # Atualizar campos fornecidos
    for field, value in update_data.items():
        setattr(client, field, value)
    
    await db.commit()
    await db.refresh(client)
    
    return ClientResponse.model_validate(client)


@router.delete(
    "/{client_id}",
    status_code=204,
    summary="Deletar cliente",
    description="Remove um cliente do tenant autenticado."
)
async def delete_client(
    client_id: UUID = Path(..., description="UUID do cliente"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove um cliente do tenant autenticado.
    
    Args:
        client_id: UUID do cliente
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Raises:
        HTTPException 404: Se o cliente não for encontrado ou não pertencer ao tenant
    """
    client_id_str = str(client_id)
    tenant_id_str = str(tenant.id)
    
    result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id_str,
                Client.tenant_id == tenant_id_str
            )
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado ou não pertence a este estúdio"
        )
    
    await db.delete(client)
    await db.commit()
    
    return None

