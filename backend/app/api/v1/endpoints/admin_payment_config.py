"""
Endpoints administrativos para gerenciamento de Configurações de Pagamento.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.payment_method_config import PaymentMethodConfig
from app.models.payment_installment_config import PaymentInstallmentConfig, TaxType

from app.schemas.payment_config import (
    PaymentMethodConfigCreate,
    PaymentMethodConfigUpdate,
    PaymentMethodConfigResponse,
    PaymentMethodConfigWithInstallments,
    PaymentInstallmentConfigCreate,
    PaymentInstallmentConfigUpdate,
    PaymentInstallmentConfigResponse
)

router = APIRouter(prefix="/admin/payment-config", tags=["Admin - Payment Config"])


# ============================================
# PaymentMethodConfig Endpoints
# ============================================

@router.get(
    "/methods",
    response_model=List[PaymentMethodConfigWithInstallments],
    summary="Listar formas de pagamento",
    description="Retorna todas as formas de pagamento configuradas do tenant autenticado."
)
async def list_payment_methods(
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas as formas de pagamento do tenant.
    
    Args:
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[PaymentMethodConfigWithInstallments]: Lista de formas de pagamento com suas configurações de parcelamento
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="tenant_id inválido")
    
    # Buscar formas de pagamento (sem duplicatas)
    methods_query = select(PaymentMethodConfig).where(
        PaymentMethodConfig.tenant_id == tenant_id_str
    ).order_by(PaymentMethodConfig.method_name)
    methods_result = await db.execute(methods_query)
    methods = list(methods_result.scalars().all())
    
    # Inicializar formas de pagamento padrão se não existirem
    default_methods = [
        {'name': 'Dinheiro', 'is_editable': False},
        {'name': 'PIX', 'is_editable': False}
    ]
    
    existing_names = {method.method_name.lower() for method in methods}
    created_new = False
    
    for default_method in default_methods:
        if default_method['name'].lower() not in existing_names:
            # Criar forma de pagamento padrão
            new_method = PaymentMethodConfig(
                tenant_id=tenant_id_str,
                method_name=default_method['name'],
                is_editable=default_method['is_editable'],
                max_installments=None,
                debit_tax_type=None,
                debit_tax_value=None
            )
            db.add(new_method)
            await db.flush()  # Para obter o ID sem fazer commit
            methods.append(new_method)
            created_new = True
    
    # Fazer commit se criou novos métodos
    if created_new:
        await db.commit()
        # Recarregar métodos após commit para garantir que estão atualizados
        methods_result = await db.execute(methods_query)
        methods = list(methods_result.scalars().all())
    
    # Remover duplicatas baseado no nome (caso existam)
    seen_names = set()
    unique_methods = []
    for method in methods:
        method_name_lower = method.method_name.lower()
        if method_name_lower not in seen_names:
            seen_names.add(method_name_lower)
            unique_methods.append(method)
    
    # Para cada método, buscar configurações de parcelamento
    result = []
    for method in unique_methods:
        method_dict = PaymentMethodConfigResponse.model_validate(method).model_dump()
        
        # Buscar parcelamentos se for cartão de crédito
        if method.method_name.lower() in ['credit card', 'cartão de crédito', 'crédito']:
            installments_query = select(PaymentInstallmentConfig).where(
                PaymentInstallmentConfig.payment_method_id == str(method.id)
            )
            installments_result = await db.execute(installments_query)
            installments = installments_result.scalars().all()
            method_dict['installments'] = [PaymentInstallmentConfigResponse.model_validate(inst).model_dump() for inst in installments]
        else:
            method_dict['installments'] = []
        
        result.append(PaymentMethodConfigWithInstallments(**method_dict))
    
    return result


@router.post(
    "/methods",
    response_model=PaymentMethodConfigResponse,
    status_code=201,
    summary="Criar forma de pagamento",
    description="Cria uma nova forma de pagamento para o tenant autenticado."
)
async def create_payment_method(
    method_data: PaymentMethodConfigCreate,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria uma nova forma de pagamento.
    
    Args:
        method_data: Dados da forma de pagamento
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        PaymentMethodConfigResponse: Forma de pagamento criada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="tenant_id inválido")
    
    # Verificar se já existe uma forma de pagamento com o mesmo nome
    existing_query = select(PaymentMethodConfig).where(
        and_(
            PaymentMethodConfig.tenant_id == tenant_id_str,
            PaymentMethodConfig.method_name == method_data.method_name
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Já existe uma forma de pagamento com o nome '{method_data.method_name}'"
        )
    
    # Criar nova forma de pagamento
    new_method = PaymentMethodConfig(
        tenant_id=tenant_id_str,
        method_name=method_data.method_name,
        is_editable=method_data.is_editable,
        max_installments=method_data.max_installments,
        debit_tax_type=method_data.debit_tax_type,
        debit_tax_value=method_data.debit_tax_value
    )
    
    db.add(new_method)
    await db.commit()
    await db.refresh(new_method)
    
    return PaymentMethodConfigResponse.model_validate(new_method)


@router.put(
    "/methods/{method_id}",
    response_model=PaymentMethodConfigResponse,
    summary="Atualizar forma de pagamento",
    description="Atualiza uma forma de pagamento existente."
)
async def update_payment_method(
    method_id: UUID = Path(..., description="UUID da forma de pagamento"),
    update_data: PaymentMethodConfigUpdate = ...,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza uma forma de pagamento.
    
    Args:
        method_id: UUID da forma de pagamento
        update_data: Dados para atualização
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        PaymentMethodConfigResponse: Forma de pagamento atualizada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    method_id_str = str(method_id) if method_id else None
    
    if not tenant_id_str or not method_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    # Buscar forma de pagamento
    method_query = select(PaymentMethodConfig).where(
        and_(
            PaymentMethodConfig.id == method_id_str,
            PaymentMethodConfig.tenant_id == tenant_id_str
        )
    )
    method_result = await db.execute(method_query)
    method = method_result.scalar_one_or_none()
    
    if not method:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Verificar se é editável (exceto para atualização de taxas de débito)
    # Permitir atualização de taxas mesmo para métodos não editáveis
    can_update_taxes = (
        update_data.debit_tax_type is not None or 
        update_data.debit_tax_value is not None
    )
    
    if not method.is_editable and not can_update_taxes:
        raise HTTPException(
            status_code=400,
            detail="Esta forma de pagamento não pode ser editada"
        )
    
    # Atualizar campos
    if update_data.is_editable is not None and method.is_editable:
        method.is_editable = update_data.is_editable
    if update_data.max_installments is not None:
        method.max_installments = update_data.max_installments
    if update_data.debit_tax_type is not None:
        method.debit_tax_type = update_data.debit_tax_type
    if update_data.debit_tax_value is not None:
        method.debit_tax_value = update_data.debit_tax_value
    
    await db.commit()
    await db.refresh(method)
    
    return PaymentMethodConfigResponse.model_validate(method)


# ============================================
# PaymentInstallmentConfig Endpoints
# ============================================

@router.get(
    "/methods/{method_id}/installments",
    response_model=List[PaymentInstallmentConfigResponse],
    summary="Listar configurações de parcelamento",
    description="Retorna todas as configurações de parcelamento de uma forma de pagamento."
)
async def list_installments(
    method_id: UUID = Path(..., description="UUID da forma de pagamento"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista configurações de parcelamento de uma forma de pagamento.
    
    Args:
        method_id: UUID da forma de pagamento
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[PaymentInstallmentConfigResponse]: Lista de configurações de parcelamento
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    method_id_str = str(method_id) if method_id else None
    
    if not tenant_id_str or not method_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    # Verificar se a forma de pagamento pertence ao tenant
    method_query = select(PaymentMethodConfig).where(
        and_(
            PaymentMethodConfig.id == method_id_str,
            PaymentMethodConfig.tenant_id == tenant_id_str
        )
    )
    method_result = await db.execute(method_query)
    method = method_result.scalar_one_or_none()
    
    if not method:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Buscar configurações de parcelamento
    installments_query = select(PaymentInstallmentConfig).where(
        PaymentInstallmentConfig.payment_method_id == method_id_str
    ).order_by(PaymentInstallmentConfig.installments_count)
    
    installments_result = await db.execute(installments_query)
    installments = installments_result.scalars().all()
    
    return [PaymentInstallmentConfigResponse.model_validate(inst) for inst in installments]


@router.post(
    "/methods/{method_id}/installments",
    response_model=PaymentInstallmentConfigResponse,
    status_code=201,
    summary="Criar configuração de parcelamento",
    description="Cria uma nova configuração de parcelamento para uma forma de pagamento."
)
async def create_installment(
    method_id: UUID = Path(..., description="UUID da forma de pagamento"),
    installment_data: PaymentInstallmentConfigCreate = ...,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria uma nova configuração de parcelamento.
    
    Args:
        method_id: UUID da forma de pagamento
        installment_data: Dados da configuração de parcelamento
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        PaymentInstallmentConfigResponse: Configuração de parcelamento criada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    method_id_str = str(method_id) if method_id else None
    
    if not tenant_id_str or not method_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    # Verificar se a forma de pagamento pertence ao tenant
    method_query = select(PaymentMethodConfig).where(
        and_(
            PaymentMethodConfig.id == method_id_str,
            PaymentMethodConfig.tenant_id == tenant_id_str
        )
    )
    method_result = await db.execute(method_query)
    method = method_result.scalar_one_or_none()
    
    if not method:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Verificar se já existe configuração para este número de parcelas
    existing_query = select(PaymentInstallmentConfig).where(
        and_(
            PaymentInstallmentConfig.payment_method_id == method_id_str,
            PaymentInstallmentConfig.installments_count == installment_data.installments_count
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Já existe uma configuração para {installment_data.installments_count}x parcelas"
        )
    
    # Validar e converter string para valor do enum
    tax_type_value = None
    if installment_data.tax_type == '%':
        tax_type_value = TaxType.PERCENT.value  # '%'
    elif installment_data.tax_type == 'R$':
        tax_type_value = TaxType.FIXED.value  # 'R$'
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de taxa inválido: '{installment_data.tax_type}'. Use '%' ou 'R$'"
        )
    
    # Criar nova configuração de parcelamento
    new_installment = PaymentInstallmentConfig(
        payment_method_id=method_id_str,
        installments_count=installment_data.installments_count,
        tax_type=tax_type_value,  # Usar o valor string diretamente
        tax_value=installment_data.tax_value
    )
    
    db.add(new_installment)
    await db.commit()
    await db.refresh(new_installment)
    
    return PaymentInstallmentConfigResponse.model_validate(new_installment)


@router.put(
    "/installments/{installment_id}",
    response_model=PaymentInstallmentConfigResponse,
    summary="Atualizar configuração de parcelamento",
    description="Atualiza uma configuração de parcelamento existente."
)
async def update_installment(
    installment_id: UUID = Path(..., description="UUID da configuração de parcelamento"),
    update_data: PaymentInstallmentConfigUpdate = ...,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza uma configuração de parcelamento.
    
    Args:
        installment_id: UUID da configuração de parcelamento
        update_data: Dados para atualização
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        PaymentInstallmentConfigResponse: Configuração atualizada
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    installment_id_str = str(installment_id) if installment_id else None
    
    if not tenant_id_str or not installment_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    # Buscar configuração de parcelamento
    installment_query = select(PaymentInstallmentConfig).where(
        PaymentInstallmentConfig.id == installment_id_str
    )
    installment_result = await db.execute(installment_query)
    installment = installment_result.scalar_one_or_none()
    
    if not installment:
        raise HTTPException(status_code=404, detail="Configuração de parcelamento não encontrada")
    
    # Verificar se a forma de pagamento pertence ao tenant
    method_query = select(PaymentMethodConfig).where(
        and_(
            PaymentMethodConfig.id == str(installment.payment_method_id),
            PaymentMethodConfig.tenant_id == tenant_id_str
        )
    )
    method_result = await db.execute(method_query)
    method = method_result.scalar_one_or_none()
    
    if not method:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Atualizar campos
    if update_data.tax_type is not None:
        # Converter string para valor do enum
        if update_data.tax_type == '%':
            installment.tax_type = TaxType.PERCENT.value  # '%'
        elif update_data.tax_type == 'R$':
            installment.tax_type = TaxType.FIXED.value  # 'R$'
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de taxa inválido: '{update_data.tax_type}'. Use '%' ou 'R$'"
            )
    if update_data.tax_value is not None:
        installment.tax_value = update_data.tax_value
    
    await db.commit()
    await db.refresh(installment)
    
    return PaymentInstallmentConfigResponse.model_validate(installment)


@router.delete(
    "/installments/{installment_id}",
    status_code=204,
    summary="Deletar configuração de parcelamento",
    description="Remove uma configuração de parcelamento."
)
async def delete_installment(
    installment_id: UUID = Path(..., description="UUID da configuração de parcelamento"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove uma configuração de parcelamento.
    
    Args:
        installment_id: UUID da configuração de parcelamento
        tenant: Tenant autenticado
        db: Sessão do banco de dados
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    installment_id_str = str(installment_id) if installment_id else None
    
    if not tenant_id_str or not installment_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    # Buscar configuração de parcelamento
    installment_query = select(PaymentInstallmentConfig).where(
        PaymentInstallmentConfig.id == installment_id_str
    )
    installment_result = await db.execute(installment_query)
    installment = installment_result.scalar_one_or_none()
    
    if not installment:
        raise HTTPException(status_code=404, detail="Configuração de parcelamento não encontrada")
    
    # Verificar se a forma de pagamento pertence ao tenant
    method_query = select(PaymentMethodConfig).where(
        and_(
            PaymentMethodConfig.id == str(installment.payment_method_id),
            PaymentMethodConfig.tenant_id == tenant_id_str
        )
    )
    method_result = await db.execute(method_query)
    method = method_result.scalar_one_or_none()
    
    if not method:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Deletar
    await db.delete(installment)
    await db.commit()
    
    return None

