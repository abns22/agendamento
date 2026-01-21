"""
Endpoints administrativos para gerenciamento de Despesas.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import verify_subscription_access
from app.models.tenant import Tenant
from app.models.expense import Expense, PaymentMethodEnum

from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse

router = APIRouter(prefix="/admin/expenses", tags=["Admin - Expenses"])


@router.get(
    "",
    response_model=List[ExpenseResponse],
    summary="Listar despesas",
    description="Retorna todas as despesas do tenant autenticado filtradas por período obrigatório e filtros opcionais."
)
async def list_expenses(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD) - obrigatório"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD) - obrigatório"),
    search: Optional[str] = Query(None, description="Busca em descrição ou item_name (opcional)"),
    payment_method: Optional[PaymentMethodEnum] = Query(None, description="Filtrar por método de pagamento (opcional)"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas as despesas do tenant.
    
    Args:
        start_date: Data inicial para filtrar (obrigatório)
        end_date: Data final para filtrar (obrigatório)
        search: Busca em descrição ou item_name (opcional)
        payment_method: Método de pagamento para filtrar (opcional)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[ExpenseResponse]: Lista de despesas ordenadas por payment_date (mais recente primeiro)
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="tenant_id inválido")
    
    # Validar e converter datas
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Datas devem estar no formato YYYY-MM-DD")
    
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="Data de início deve ser anterior ou igual à data de fim")
    
    query = select(Expense).where(
        and_(
            Expense.tenant_id == tenant_id_str,
            Expense.payment_date >= start_dt,
            Expense.payment_date <= end_dt
        )
    )
    
    # Aplicar filtro de busca (em description ou item_name)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Expense.description.ilike(search_pattern),
                Expense.item_name.ilike(search_pattern)
            )
        )
    
    # Aplicar filtro de método de pagamento
    if payment_method:
        query = query.where(Expense.payment_method == payment_method)
    
    # Ordenar por payment_date (mais recente primeiro)
    query = query.order_by(Expense.payment_date.desc())
    
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
    
    # Validar que o valor é positivo
    if expense_data.amount <= 0:
        raise HTTPException(status_code=400, detail="O valor da despesa deve ser positivo")
    
    # Converter payment_date para timezone-naive se necessário
    payment_date = expense_data.payment_date
    if payment_date.tzinfo is not None:
        payment_date = payment_date.replace(tzinfo=None)
    
    new_expense = Expense(
        tenant_id=tenant_id_str,
        description=expense_data.description,
        item_name=expense_data.item_name,
        amount=expense_data.amount,
        payment_method=expense_data.payment_method,
        payment_date=payment_date,
        category=expense_data.category
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
    if update_data.item_name is not None:
        expense.item_name = update_data.item_name
    if update_data.amount is not None:
        if update_data.amount <= 0:
            raise HTTPException(status_code=400, detail="O valor da despesa deve ser positivo")
        expense.amount = update_data.amount
    if update_data.payment_method is not None:
        expense.payment_method = update_data.payment_method
    if update_data.payment_date is not None:
        payment_date = update_data.payment_date
        if payment_date.tzinfo is not None:
            payment_date = payment_date.replace(tzinfo=None)
        expense.payment_date = payment_date
    if update_data.category is not None:
        expense.category = update_data.category
    
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

