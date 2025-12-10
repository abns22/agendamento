"""
Endpoints administrativos para gerenciamento de Categorias de Produtos.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.product_category import ProductCategory
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCategoryResponse
)

router = APIRouter(prefix="/admin/product-categories", tags=["Admin - Product Categories"])


@router.post(
    "",
    response_model=ProductCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar categoria de produto",
    description="Cria uma nova categoria de produto para o tenant autenticado."
)
async def create_category(
    category_data: ProductCategoryCreate,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Cria uma nova categoria de produto."""
    new_category = ProductCategory(
        tenant_id=str(tenant.id),
        **category_data.model_dump()
    )
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return ProductCategoryResponse.model_validate(new_category)


@router.get(
    "",
    response_model=List[ProductCategoryResponse],
    summary="Listar categorias",
    description="Retorna todas as categorias de produtos do tenant autenticado."
)
async def list_categories(
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas as categorias do tenant autenticado."""
    tenant_id_str = str(tenant.id)
    query = select(ProductCategory).where(
        ProductCategory.tenant_id == tenant_id_str
    ).order_by(ProductCategory.name)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    return [ProductCategoryResponse.model_validate(cat) for cat in categories]


@router.get(
    "/{category_id}",
    response_model=ProductCategoryResponse,
    summary="Obter categoria por ID",
    description="Retorna uma categoria específica do tenant autenticado."
)
async def get_category(
    category_id: UUID = Path(..., description="UUID da categoria"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtém uma categoria específica."""
    tenant_id_str = str(tenant.id)
    result = await db.execute(
        select(ProductCategory).where(
            and_(
                ProductCategory.id == str(category_id),
                ProductCategory.tenant_id == tenant_id_str
            )
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada"
        )
    return ProductCategoryResponse.model_validate(category)


@router.put(
    "/{category_id}",
    response_model=ProductCategoryResponse,
    summary="Atualizar categoria",
    description="Atualiza os dados de uma categoria existente."
)
async def update_category(
    update_data: ProductCategoryUpdate,
    category_id: UUID = Path(..., description="UUID da categoria"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Atualiza uma categoria existente."""
    tenant_id_str = str(tenant.id)
    result = await db.execute(
        select(ProductCategory).where(
            and_(
                ProductCategory.id == str(category_id),
                ProductCategory.tenant_id == tenant_id_str
            )
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada"
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return ProductCategoryResponse.model_validate(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar categoria",
    description="Deleta uma categoria específica do tenant autenticado."
)
async def delete_category(
    category_id: UUID = Path(..., description="UUID da categoria"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Deleta uma categoria existente."""
    tenant_id_str = str(tenant.id)
    result = await db.execute(
        select(ProductCategory).where(
            and_(
                ProductCategory.id == str(category_id),
                ProductCategory.tenant_id == tenant_id_str
            )
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada"
        )

    await db.delete(category)
    await db.commit()
    return None

