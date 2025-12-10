"""
Serviço de Cálculos Financeiros.

Este serviço implementa a lógica de cálculo de taxas de pagamento,
acréscimos por parcelamento e cálculo de lucro.
"""
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.payment_method_config import PaymentMethodConfig
from app.models.payment_installment_config import PaymentInstallmentConfig
from app.models.service import Service


class FinancialService:
    """
    Serviço responsável por cálculos financeiros relacionados a pagamentos.
    """
    
    @staticmethod
    async def calculate_payment_fee(
        db_session: AsyncSession,
        tenant_id: UUID,
        payment_method_id: UUID,
        service_price: Decimal,
        installments: int = 1
    ) -> Tuple[Decimal, Decimal]:
        """
        Calcula a taxa de pagamento baseada na forma de pagamento e número de parcelas.
        
        Args:
            db_session: Sessão do banco de dados
            tenant_id: UUID do tenant
            payment_method_id: UUID da forma de pagamento
            service_price: Preço do serviço
            installments: Número de parcelas (padrão: 1)
            
        Returns:
            Tuple[Decimal, Decimal]: (taxa_calculada, valor_total)
            - taxa_calculada: Valor da taxa em R$
            - valor_total: Preço do serviço + taxa
            
        Raises:
            ValueError: Se a forma de pagamento não for encontrada ou dados inválidos
        """
        # Converter IDs para strings
        tenant_id_str = str(tenant_id) if tenant_id else None
        payment_method_id_str = str(payment_method_id) if payment_method_id else None
        
        if not tenant_id_str or not payment_method_id_str:
            raise ValueError("tenant_id e payment_method_id são obrigatórios")
        
        # Buscar configuração da forma de pagamento
        payment_method_query = select(PaymentMethodConfig).where(
            and_(
                PaymentMethodConfig.id == payment_method_id_str,
                PaymentMethodConfig.tenant_id == tenant_id_str
            )
        )
        payment_method_result = await db_session.execute(payment_method_query)
        payment_method = payment_method_result.scalar_one_or_none()
        
        if not payment_method:
            raise ValueError(f"Forma de pagamento não encontrada")
        
        # Se for débito e tiver taxa configurada
        if payment_method.method_name.lower() in ['debit card', 'cartão de débito', 'débito']:
            if payment_method.debit_tax_type and payment_method.debit_tax_value:
                if payment_method.debit_tax_type == '%':
                    # Taxa percentual
                    fee = service_price * (payment_method.debit_tax_value / Decimal('100'))
                else:
                    # Taxa fixa em R$
                    fee = payment_method.debit_tax_value
                
                total = service_price + fee
                return fee, total
        
        # Se for crédito e tiver parcelas
        if payment_method.method_name.lower() in ['credit card', 'cartão de crédito', 'crédito']:
            if installments > 1:
                # Buscar configuração de parcelamento
                installment_query = select(PaymentInstallmentConfig).where(
                    and_(
                        PaymentInstallmentConfig.payment_method_id == payment_method_id_str,
                        PaymentInstallmentConfig.installments_count == installments
                    )
                )
                installment_result = await db_session.execute(installment_query)
                installment_config = installment_result.scalar_one_or_none()
                
                if installment_config:
                    if installment_config.tax_type.value == '%':
                        # Taxa percentual sobre o valor total
                        fee = service_price * (installment_config.tax_value / Decimal('100'))
                    else:
                        # Taxa fixa em R$
                        fee = installment_config.tax_value
                    
                    total = service_price + fee
                    return fee, total
        
        # Dinheiro, Pix ou sem taxa: sem acréscimo
        return Decimal('0.00'), service_price
    
    @staticmethod
    async def calculate_profit(
        db_session: AsyncSession,
        service_id: UUID,
        final_price: Decimal
    ) -> Optional[Decimal]:
        """
        Calcula o lucro de um serviço baseado no preço final e custo fixo.
        
        Args:
            db_session: Sessão do banco de dados
            service_id: UUID do serviço
            final_price: Preço final pago pelo cliente (incluindo taxas)
            
        Returns:
            Optional[Decimal]: Lucro calculado (preço final - custo fixo) ou None se não houver custo configurado
        """
        service_id_str = str(service_id) if service_id else None
        if not service_id_str:
            raise ValueError("service_id é obrigatório")
        
        # Buscar serviço
        service_query = select(Service).where(Service.id == service_id_str)
        service_result = await db_session.execute(service_query)
        service = service_result.scalar_one_or_none()
        
        if not service:
            raise ValueError("Serviço não encontrado")
        
        # Se não tiver custo fixo configurado, retornar None
        if service.fixed_cost_value is None:
            return None
        
        # Calcular lucro: preço final - custo fixo
        profit = final_price - service.fixed_cost_value
        return profit

