"""
Endpoints administrativos para gerenciamento de Inventário.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID
from typing import List
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.stock_entry import StockEntry, UnitType
from app.schemas.stock_entry import (
    StockEntryCreate,
    StockEntryUpdate,
    StockEntryResponse,
    InventorySummaryResponse,
    InventorySummaryItem
)

router = APIRouter(prefix="/admin/inventory", tags=["Admin - Inventory"])


@router.get(
    "/summary",
    response_model=InventorySummaryResponse,
    summary="Resumo de Inventário",
    description="Retorna o resumo completo do inventário com quantidades e valores totais."
)
async def get_inventory_summary(
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna o resumo do inventário calculando:
    - Quantidade total em estoque por produto
    - Valor total de estoque (custo) por produto
    - Valor total geral do inventário
    """
    try:
        tenant_id_str = str(tenant.id)
        
        # Buscar todos os produtos do tenant
        products_query = select(Product).where(
            Product.tenant_id == tenant_id_str
        ).order_by(Product.name)
        products_result = await db.execute(products_query)
        products = products_result.scalars().all()
        
        summary_items = []
        total_value = Decimal('0.00')
        
        for product in products:
            # Buscar todas as entradas de estoque deste produto
            stock_query = select(StockEntry).where(
                StockEntry.product_id == str(product.id)
            )
            stock_result = await db.execute(stock_query)
            stock_entries = stock_result.scalars().all()
            
            # Calcular quantidade total (soma de todas as entradas)
            total_quantity = sum(entry.quantity for entry in stock_entries)
            
            # Calcular valor total (unit_cost * total_quantity)
            unit_cost = Decimal(str(product.unit_cost))
            product_total_value = unit_cost * Decimal(str(total_quantity))
            total_value += product_total_value
            
            # Buscar nome da categoria
            category_name = None
            if product.category_id:
                category_query = select(ProductCategory).where(
                    ProductCategory.id == str(product.category_id)
                )
                category_result = await db.execute(category_query)
                category = category_result.scalar_one_or_none()
                if category:
                    category_name = category.name
            
            summary_items.append(
                InventorySummaryItem(
                    product_id=UUID(str(product.id)),
                    product_name=product.name,
                    category_name=category_name,
                    unit_cost=unit_cost,
                    total_quantity=total_quantity,
                    total_value=product_total_value
                )
            )
        
        return InventorySummaryResponse(
            items=summary_items,
            total_products=len(products),
            total_value=total_value
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao calcular resumo de inventário: {str(e)}"
        )


@router.get(
    "/stock-entries",
    response_model=List[StockEntryResponse],
    summary="Listar entradas de estoque",
    description="Retorna todas as entradas de estoque, opcionalmente filtradas por produto."
)
async def list_stock_entries(
    product_id: UUID = None,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas as entradas de estoque."""
    tenant_id_str = str(tenant.id)
    
    query = select(StockEntry)
    
    if product_id:
        # Validar que o produto pertence ao tenant
        product_query = select(Product).where(
            and_(
                Product.id == str(product_id),
                Product.tenant_id == tenant_id_str
            )
        )
        product_result = await db.execute(product_query)
        if not product_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado"
            )
        
        query = query.where(StockEntry.product_id == str(product_id))
    else:
        # Se não filtrar por produto, buscar apenas produtos do tenant
        products_query = select(Product.id).where(
            Product.tenant_id == tenant_id_str
        )
        products_result = await db.execute(products_query)
        product_ids = [str(p[0]) for p in products_result.all()]
        
        if product_ids:
            from sqlalchemy import or_
            query = query.where(
                or_(*[StockEntry.product_id == pid for pid in product_ids])
            )
        else:
            # Nenhum produto, retornar lista vazia
            return []
    
    result = await db.execute(query.order_by(StockEntry.created_at.desc()))
    entries = result.scalars().all()
    return [StockEntryResponse.model_validate(entry) for entry in entries]


@router.post(
    "/stock-entries",
    response_model=StockEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar entrada de estoque",
    description="Cria uma nova entrada de estoque para um produto."
)
async def create_stock_entry(
    entry_data: StockEntryCreate,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Cria uma nova entrada de estoque."""
    tenant_id_str = str(tenant.id)
    
    # Validar que o produto pertence ao tenant
    product_query = select(Product).where(
        and_(
            Product.id == str(entry_data.product_id),
            Product.tenant_id == tenant_id_str
        )
    )
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    
    new_entry = StockEntry(**entry_data.model_dump())
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)
    return StockEntryResponse.model_validate(new_entry)


@router.put(
    "/stock-entries/{entry_id}",
    response_model=StockEntryResponse,
    summary="Atualizar entrada de estoque",
    description="Atualiza uma entrada de estoque existente."
)
async def update_stock_entry(
    update_data: StockEntryUpdate,
    entry_id: UUID = Path(..., description="UUID da entrada de estoque"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Atualiza uma entrada de estoque existente."""
    tenant_id_str = str(tenant.id)
    
    # Buscar entrada
    entry_query = select(StockEntry).where(
        StockEntry.id == str(entry_id)
    )
    entry_result = await db.execute(entry_query)
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrada de estoque não encontrada"
        )
    
    # Validar que o produto da entrada pertence ao tenant
    product_query = select(Product).where(
        and_(
            Product.id == str(entry.product_id),
            Product.tenant_id == tenant_id_str
        )
    )
    product_result = await db.execute(product_query)
    if not product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta entrada de estoque"
        )
    
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    
    await db.commit()
    await db.refresh(entry)
    return StockEntryResponse.model_validate(entry)


@router.delete(
    "/stock-entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar entrada de estoque",
    description="Deleta uma entrada de estoque específica."
)
async def delete_stock_entry(
    entry_id: UUID = Path(..., description="UUID da entrada de estoque"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Deleta uma entrada de estoque existente."""
    tenant_id_str = str(tenant.id)
    
    # Buscar entrada
    entry_query = select(StockEntry).where(
        StockEntry.id == str(entry_id)
    )
    entry_result = await db.execute(entry_query)
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrada de estoque não encontrada"
        )
    
    # Validar que o produto da entrada pertence ao tenant
    product_query = select(Product).where(
        and_(
            Product.id == str(entry.product_id),
            Product.tenant_id == tenant_id_str
        )
    )
    product_result = await db.execute(product_query)
    if not product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta entrada de estoque"
        )
    
    await db.delete(entry)
    await db.commit()
    return None

