"""
Serviço de Finalização de Agendamentos.

Este serviço implementa a lógica de finalização de agendamentos,
cálculo de transações financeiras e registro no caixa.
"""
from decimal import Decimal
from typing import List, Optional, Tuple, Union
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from app.models.transaction import Transaction
from app.models.payment_entry import PaymentEntry
from app.models.payment_method_config import PaymentMethodConfig
from app.models.debtor import Debtor, DebtorStatus
from app.services.promotion_service import PromotionService
from app.services.financial_service import FinancialService


class FinalizationService:
    """
    Serviço responsável por finalizar agendamentos e gerar transações no caixa.
    """
    
    @staticmethod
    async def finalize_appointment(
        db_session: AsyncSession,
        tenant_id: UUID,
        appointment_id: UUID,
        payment_entries: List[dict],
        additional_cost: Optional[Decimal] = None,
        is_paid: bool = True,
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        due_date: Optional[datetime] = None,
        value_due: Optional[Decimal] = None
    ) -> Tuple[Transaction, Appointment, Optional[Debtor]]:
        """
        Finaliza um agendamento e cria a transação no caixa.
        
        Fluxo:
        1. Buscar agendamento e validar
        2. Buscar serviço e calcular custos
        3. Aplicar promoção (se ativa) para obter valor bruto
        4. Calcular taxas de pagamento para cada forma de pagamento
        5. Calcular valor líquido total
        6. Criar Transaction
        7. Criar PaymentEntry para cada forma de pagamento
        8. Atualizar Appointment para COMPLETED
        
        Args:
            db_session: Sessão do banco de dados
            tenant_id: UUID do tenant
            appointment_id: UUID do agendamento
            payment_entries: Lista de dicts com payment_method_id, value_paid, installments
            additional_cost: Custo adicional opcional
            
        Returns:
            Tuple[Transaction, Appointment]: Transação criada e agendamento atualizado
            
        Raises:
            ValueError: Se o agendamento não for encontrado, já estiver finalizado, ou dados inválidos
        """
        # Converter IDs para strings
        tenant_id_str = str(tenant_id) if tenant_id else None
        appointment_id_str = str(appointment_id) if appointment_id else None
        
        if not tenant_id_str or not appointment_id_str:
            raise ValueError("tenant_id e appointment_id são obrigatórios")
        
        # 1. Buscar agendamento
        appointment_query = select(Appointment).where(
            and_(
                Appointment.id == appointment_id_str,
                Appointment.tenant_id == tenant_id_str
            )
        )
        appointment_result = await db_session.execute(appointment_query)
        appointment = appointment_result.scalar_one_or_none()
        
        if not appointment:
            raise ValueError("Agendamento não encontrado")
        
        if appointment.status == AppointmentStatus.COMPLETED:
            raise ValueError("Agendamento já foi finalizado")
        
        if appointment.status == AppointmentStatus.CANCELED:
            raise ValueError("Não é possível finalizar um agendamento cancelado")
        
        if appointment.is_manual_block:
            raise ValueError("Não é possível finalizar um bloqueio manual")
        
        # 2. Buscar serviço
        if not appointment.service_id:
            raise ValueError("Agendamento não possui serviço associado")
        
        service_id_str = str(appointment.service_id)
        service_query = select(Service).where(Service.id == service_id_str)
        service_result = await db_session.execute(service_query)
        service = service_result.scalar_one_or_none()
        
        if not service:
            raise ValueError("Serviço não encontrado")
        
        # 3. Calcular valor bruto (aplicando promoção se ativa)
        gross_value = Decimal(str(PromotionService.get_effective_price(service)))
        
        # 4. Calcular custo total
        total_cost = Decimal('0.00')
        if service.fixed_cost_value:
            total_cost = Decimal(str(service.fixed_cost_value))
        
        if additional_cost:
            total_cost += additional_cost
        
        # 5. Calcular taxas de pagamento e valor líquido total
        net_value = Decimal('0.00')
        payment_entries_to_create = []
        
        for payment_entry_data in payment_entries:
            payment_method_id = payment_entry_data.get('payment_method_id')
            value_paid = Decimal(str(payment_entry_data.get('value_paid', 0)))
            installments = payment_entry_data.get('installments', 1)
            
            if not payment_method_id or value_paid <= 0:
                raise ValueError("payment_method_id e value_paid são obrigatórios e value_paid deve ser > 0")
            
            # Buscar forma de pagamento
            payment_method_id_str = str(payment_method_id)
            payment_method_query = select(PaymentMethodConfig).where(
                and_(
                    PaymentMethodConfig.id == payment_method_id_str,
                    PaymentMethodConfig.tenant_id == tenant_id_str
                )
            )
            payment_method_result = await db_session.execute(payment_method_query)
            payment_method = payment_method_result.scalar_one_or_none()
            
            if not payment_method:
                raise ValueError(f"Forma de pagamento não encontrada: {payment_method_id}")
            
            # Calcular taxa de pagamento para este valor parcial
            # A taxa é calculada proporcionalmente ao valor pago
            fee, value_with_fee = await FinancialService.calculate_payment_fee(
                db_session=db_session,
                tenant_id=tenant_id,
                payment_method_id=payment_method_id,
                service_price=value_paid,  # Usar o valor parcial como base
                installments=installments
            )
            
            # O valor líquido é o valor pago menos a taxa
            # fee é a taxa calculada, então o valor que entra no caixa é value_paid - fee
            net_value += value_paid - fee
            
            # Determinar se é conta bancária (PIX ou Cartão)
            # Dinheiro = False (físico), PIX/Cartões = True (bancário)
            method_name_lower = payment_method.method_name.lower()
            is_bank_account = (
                'pix' in method_name_lower or
                'cartão' in method_name_lower or
                'card' in method_name_lower or
                'débito' in method_name_lower or
                'debit' in method_name_lower or
                'crédito' in method_name_lower or
                'credit' in method_name_lower
            ) and 'dinheiro' not in method_name_lower and 'cash' not in method_name_lower
            
            payment_entries_to_create.append({
                'payment_method_id': payment_method_id_str,
                'value_paid': value_paid,
                'installments': installments if installments > 1 else None,
                'is_bank_account': is_bank_account
            })
        
        # Validar que a soma dos pagamentos é igual ao valor bruto
        total_paid = sum(Decimal(str(pe['value_paid'])) for pe in payment_entries_to_create)
        if abs(total_paid - gross_value) > Decimal('0.01'):  # Tolerância de 1 centavo
            raise ValueError(
                f"A soma dos pagamentos ({total_paid}) deve ser igual ao valor bruto ({gross_value})"
            )
        
        # 6. Calcular lucro
        total_profit = net_value - total_cost
        
        # 7. Criar Transaction
        new_transaction = Transaction(
            tenant_id=tenant_id_str,
            appointment_id=appointment_id_str,
            date_time=datetime.now(timezone.utc),
            gross_value=gross_value,
            net_value=net_value,
            total_cost=total_cost,
            total_profit=total_profit,
            additional_cost=additional_cost,
            is_paid=is_paid
        )
        
        db_session.add(new_transaction)
        await db_session.flush()  # Para obter o ID da transação
        
        # 8. Criar PaymentEntry para cada forma de pagamento (apenas se is_paid=True)
        # Se is_paid=False, não cria PaymentEntry agora (será criado na baixa)
        new_debtor = None
        if is_paid:
            for pe_data in payment_entries_to_create:
                # Recalcular taxa para este pagamento específico
                payment_method_id_str = pe_data['payment_method_id']
                value_paid = pe_data['value_paid']
                installments = pe_data.get('installments', 1)
                
                fee, _ = await FinancialService.calculate_payment_fee(
                    db_session=db_session,
                    tenant_id=tenant_id,
                    payment_method_id=UUID(payment_method_id_str),
                    service_price=value_paid,
                    installments=installments if installments else 1
                )
                
                payment_entry = PaymentEntry(
                    transaction_id=str(new_transaction.id),
                    payment_method_id=payment_method_id_str,
                    value_paid=value_paid,
                    installments=pe_data.get('installments'),
                    is_bank_account=pe_data['is_bank_account']
                )
                
                db_session.add(payment_entry)
        else:
            # Pagamento futuro: criar Debtor
            if not client_name or not due_date:
                raise ValueError("client_name e due_date são obrigatórios quando is_paid=False")
            
            # Garantir que due_date está em UTC
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            
            # Usar value_due se fornecido, senão usar net_value (valor total)
            debtor_value = value_due if value_due is not None else net_value
            
            new_debtor = Debtor(
                transaction_id=str(new_transaction.id),
                client_name=client_name,
                client_phone=client_phone,
                due_date=due_date,
                value_due=debtor_value,  # Valor devido (pode ser parcial)
                status=DebtorStatus.PENDING
            )
            
            db_session.add(new_debtor)
        
        # 9. Atualizar Appointment
        appointment.status = AppointmentStatus.COMPLETED
        appointment.final_sale_value = net_value  # Valor líquido que entrou no caixa (ou que será recebido)
        appointment.service_cost = total_cost
        
        await db_session.commit()
        await db_session.refresh(new_transaction)
        await db_session.refresh(appointment)
        if new_debtor:
            await db_session.refresh(new_debtor)
        
        return new_transaction, appointment, new_debtor

