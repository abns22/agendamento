"""
Endpoints administrativos para gerenciamento de Despesas.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import verify_subscription_access
from app.models.tenant import Tenant
from app.models.expense import Expense

from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse

router = APIRouter(prefix="/admin/expenses", tags=["Admin - Expenses"])


@router.get(
    "",
    response_model=List[ExpenseResponse],
    summary="Listar despesas",
    description="Retorna todas as despesas do tenant autenticado, opcionalmente filtradas por período."
)
async def list_expenses(
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas as despesas do tenant.
    
    Args:
        start_date: Data inicial para filtrar (opcional)
        end_date: Data final para filtrar (opcional)
        category: Categoria para filtrar (opcional)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[ExpenseResponse]: Lista de despesas ordenadas por data (mais recente primeiro)
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="tenant_id inválido")
    
    query = select(Expense).where(Expense.tenant_id == tenant_id_str)
    
    # Aplicar filtros
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.where(Expense.date_time >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date deve estar no formato YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            query = query.where(Expense.date_time <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date deve estar no formato YYYY-MM-DD")
    
    if category:
        query = query.where(Expense.category == category)
    
    # Ordenar por data (mais recente primeiro)
    query = query.order_by(Expense.date_time.desc())
    
    result = await db.execute(query)
    expenses = result.scalars().all()
    
    return [ExpenseResponse.model_validate(expense) for expense in expenses]


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=201,
    summary="Criar despesa",
    description="Cria uma nova despesa para o tenant autenticado."
)
async def create_expense(
    expense_data: ExpenseCreate,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria uma nova despesa.
    
    Args:
        expense_data: Dados da despesa
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ExpenseResponse: Despesa criada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="tenant_id inválido")
    
    # Se date_time não for fornecido, usar data/hora atual (timezone-naive para compatibilidade com PostgreSQL)
    expense_date_time = expense_data.date_time
    if not expense_date_time:
        expense_date_time = datetime.utcnow()
    elif expense_date_time.tzinfo is not None:
        # Remover timezone se presente (converter para UTC e remover tzinfo)
        expense_date_time = expense_date_time.replace(tzinfo=None)
    
    new_expense = Expense(
        tenant_id=tenant_id_str,
        description=expense_data.description,
        value=expense_data.value,
        category=expense_data.category,
        date_time=expense_date_time
    )
    
    db.add(new_expense)
    await db.commit()
    await db.refresh(new_expense)
    
    return ExpenseResponse.model_validate(new_expense)


@router.get(
    "/{expense_id}",
    response_model=ExpenseResponse,
    summary="Obter despesa",
    description="Retorna uma despesa específica do tenant autenticado."
)
async def get_expense(
    expense_id: UUID = Path(..., description="UUID da despesa"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtém uma despesa específica.
    
    Args:
        expense_id: UUID da despesa
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ExpenseResponse: Dados da despesa
        
    Raises:
        HTTPException 404: Se a despesa não for encontrada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    expense_id_str = str(expense_id) if expense_id else None
    
    if not tenant_id_str or not expense_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    result = await db.execute(
        select(Expense).where(
            and_(
                Expense.id == expense_id_str,
                Expense.tenant_id == tenant_id_str
            )
        )
    )
    expense = result.scalar_one_or_none()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Despesa não encontrada")
    
    return ExpenseResponse.model_validate(expense)


@router.put(
    "/{expense_id}",
    response_model=ExpenseResponse,
    summary="Atualizar despesa",
    description="Atualiza uma despesa existente."
)
async def update_expense(
    expense_id: UUID = Path(..., description="UUID da despesa"),
    update_data: ExpenseUpdate = ...,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza uma despesa.
    
    Args:
        expense_id: UUID da despesa
        update_data: Dados para atualização
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ExpenseResponse: Despesa atualizada
        
    Raises:
        HTTPException 404: Se a despesa não for encontrada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    expense_id_str = str(expense_id) if expense_id else None
    
    if not tenant_id_str or not expense_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    result = await db.execute(
        select(Expense).where(
            and_(
                Expense.id == expense_id_str,
                Expense.tenant_id == tenant_id_str
            )
        )
    )
    expense = result.scalar_one_or_none()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Despesa não encontrada")
    
    # Atualizar campos fornecidos
    if update_data.description is not None:
        expense.description = update_data.description
    if update_data.value is not None:
        expense.value = update_data.value
    if update_data.category is not None:
        expense.category = update_data.category
    if update_data.date_time is not None:
        expense_date_time = update_data.date_time
        if expense_date_time.tzinfo is not None:
            # Remover timezone se presente (converter para UTC e remover tzinfo)
            expense_date_time = expense_date_time.replace(tzinfo=None)
        expense.date_time = expense_date_time
    
    await db.commit()
    await db.refresh(expense)
    
    return ExpenseResponse.model_validate(expense)


@router.delete(
    "/{expense_id}",
    status_code=204,
    summary="Deletar despesa",
    description="Remove uma despesa."
)
async def delete_expense(
    expense_id: UUID = Path(..., description="UUID da despesa"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove uma despesa.
    
    Args:
        expense_id: UUID da despesa
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Raises:
        HTTPException 404: Se a despesa não for encontrada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    expense_id_str = str(expense_id) if expense_id else None
    
    if not tenant_id_str or not expense_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    result = await db.execute(
        select(Expense).where(
            and_(
                Expense.id == expense_id_str,
                Expense.tenant_id == tenant_id_str
            )
        )
    )
    expense = result.scalar_one_or_none()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Despesa não encontrada")
    
    await db.delete(expense)
    await db.commit()
    
    return None

