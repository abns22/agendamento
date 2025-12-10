"""
Endpoints administrativos para gerenciamento de Produtos.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse
)

router = APIRouter(prefix="/admin/products", tags=["Admin - Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar produto",
    description="Cria um novo produto para o tenant autenticado."
)
async def create_product(
    product_data: ProductCreate,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Cria um novo produto."""
    tenant_id_str = str(tenant.id)
    
    # Validar categoria se fornecida
    if product_data.category_id:
        category_result = await db.execute(
            select(ProductCategory).where(
                and_(
                    ProductCategory.id == str(product_data.category_id),
                    ProductCategory.tenant_id == tenant_id_str
                )
            )
        )
        if not category_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada"
            )
    
    new_product = Product(
        tenant_id=tenant_id_str,
        **product_data.model_dump()
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return ProductResponse.model_validate(new_product)


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="Listar produtos",
    description="Retorna todos os produtos do tenant autenticado, com opções de filtro."
)
async def list_products(
    category_id: Optional[UUID] = Query(None, description="Filtrar por categoria"),
    search: Optional[str] = Query(None, description="Buscar por nome"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos os produtos do tenant autenticado."""
    tenant_id_str = str(tenant.id)
    query = select(Product).where(Product.tenant_id == tenant_id_str)
    
    if category_id:
        query = query.where(Product.category_id == str(category_id))
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(func.lower(Product.name).like(search_term))
    
    query = query.order_by(Product.name)
    
    result = await db.execute(query)
    products = result.scalars().all()
    return [ProductResponse.model_validate(product) for product in products]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Obter produto por ID",
    description="Retorna um produto específico do tenant autenticado."
)
async def get_product(
    product_id: UUID = Path(..., description="UUID do produto"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtém um produto específico."""
    tenant_id_str = str(tenant.id)
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == str(product_id),
                Product.tenant_id == tenant_id_str
            )
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    return ProductResponse.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Atualizar produto",
    description="Atualiza os dados de um produto existente."
)
async def update_product(
    update_data: ProductUpdate,
    product_id: UUID = Path(..., description="UUID do produto"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Atualiza um produto existente."""
    tenant_id_str = str(tenant.id)
    
    # Validar categoria se fornecida
    if update_data.category_id:
        category_result = await db.execute(
            select(ProductCategory).where(
                and_(
                    ProductCategory.id == str(update_data.category_id),
                    ProductCategory.tenant_id == tenant_id_str
                )
            )
        )
        if not category_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada"
            )
    
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == str(product_id),
                Product.tenant_id == tenant_id_str
            )
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar produto",
    description="Deleta um produto específico do tenant autenticado."
)
async def delete_product(
    product_id: UUID = Path(..., description="UUID do produto"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Deleta um produto existente."""
    tenant_id_str = str(tenant.id)
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == str(product_id),
                Product.tenant_id == tenant_id_str
            )
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )

    await db.delete(product)
    await db.commit()
    return None

