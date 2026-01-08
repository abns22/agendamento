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
        discount: Optional[Decimal] = None,
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
        4. Aplicar desconto (se fornecido) e validar
        5. Calcular taxas de pagamento para cada forma de pagamento
        6. Calcular valor líquido total
        7. Criar Transaction
        8. Criar PaymentEntry para cada forma de pagamento
        9. Atualizar Appointment para COMPLETED
        
        Args:
            db_session: Sessão do banco de dados
            tenant_id: UUID do tenant
            appointment_id: UUID do agendamento
            payment_entries: Lista de dicts com payment_method_id, value_paid, installments
            additional_cost: Custo adicional opcional
            discount: Valor do desconto aplicado (opcional, padrão: 0.00)
            
        Returns:
            Tuple[Transaction, Appointment, Optional[Debtor]]: Transação criada, agendamento atualizado e devedor (se houver)
            
        Raises:
            ValueError: Se o agendamento não for encontrado, já estiver finalizado, dados inválidos ou desconto maior que valor bruto
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
        
        # 2. Calcular valor bruto (usando total_value do appointment ou calculando dos serviços)
        # O appointment já tem total_value salvo no momento do agendamento (com promoções aplicadas)
        await db_session.refresh(appointment, ['services'])
        
        if appointment.total_value:
            gross_value = Decimal(str(appointment.total_value))
        elif appointment.services:
            # Calcular valor total somando os serviços (com promoções)
            gross_value = Decimal('0.00')
            for service in appointment.services:
                effective_price = Decimal(str(PromotionService.get_effective_price(service)))
                gross_value += effective_price
        elif appointment.service_id:
            # Fallback: dados antigos com serviço único
            service_id_str = str(appointment.service_id)
            service_query = select(Service).where(Service.id == service_id_str)
            service_result = await db_session.execute(service_query)
            service = service_result.scalar_one_or_none()
            if not service:
                raise ValueError("Serviço não encontrado")
            gross_value = Decimal(str(PromotionService.get_effective_price(service)))
        else:
            raise ValueError("Agendamento não possui serviços associados")
        
        # 4. Aplicar desconto e validar
        discount_value = Decimal('0.00')
        if discount is not None:
            discount_value = Decimal(str(discount))
            if discount_value < 0:
                raise ValueError("Desconto não pode ser negativo")
            if discount_value > gross_value:
                raise ValueError(f"Desconto ({discount_value}) não pode ser maior que o valor bruto total ({gross_value})")
        
        # Calcular valor final após desconto (usado para cálculos de taxas e validações)
        final_value_after_discount = gross_value - discount_value
        
        # 5. Calcular custo total (soma dos custos fixos de todos os serviços)
        total_cost = Decimal('0.00')
        await db_session.refresh(appointment, ['services'])
        if appointment.services:
            for service in appointment.services:
                if service.fixed_cost_value:
                    total_cost += Decimal(str(service.fixed_cost_value))
        elif appointment.service_id:
            # Fallback: dados antigos com serviço único
            service_id_str = str(appointment.service_id)
            service_query = select(Service).where(Service.id == service_id_str)
            service_result = await db_session.execute(service_query)
            service = service_result.scalar_one_or_none()
            if service and service.fixed_cost_value:
                total_cost = Decimal(str(service.fixed_cost_value))
        
        if additional_cost:
            total_cost += additional_cost
        
        # 6. Calcular taxas de pagamento e valor líquido total
        net_value = Decimal('0.00')
        payment_entries_to_create = []
        
        # Processar apenas entradas de pagamento válidas (com método e valor > 0)
        valid_payment_entries = [
            pe for pe in payment_entries 
            if pe.get('payment_method_id') and Decimal(str(pe.get('value_paid', 0))) > 0
        ]
        
        for payment_entry_data in valid_payment_entries:
            payment_method_id = payment_entry_data.get('payment_method_id')
            value_paid = Decimal(str(payment_entry_data.get('value_paid', 0)))
            # Garantir que installments seja um int, não None
            installments_raw = payment_entry_data.get('installments')
            installments = int(installments_raw) if installments_raw is not None else 1
            
            if not payment_method_id or value_paid <= 0:
                continue  # Pular entradas inválidas (já filtradas, mas garantir)
            
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
            # O valor base para cálculo de taxa é o valor pago (já considerando desconto proporcional)
            fee, value_with_fee = await FinancialService.calculate_payment_fee(
                db_session=db_session,
                tenant_id=tenant_id,
                payment_method_id=payment_method_id,
                service_price=value_paid,  # Usar o valor parcial como base (já com desconto proporcional)
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
                'installments': installments if installments and installments > 1 else None,
                'is_bank_account': is_bank_account
            })
        
        # Validar que a soma dos pagamentos + valor a receber é igual ao valor final após desconto
        total_paid = sum(Decimal(str(pe['value_paid'])) for pe in payment_entries_to_create)
        
        # Se há valor a receber (value_due), considerar na validação
        value_due_decimal = Decimal('0.00')
        if value_due is not None:
            value_due_decimal = Decimal(str(value_due))
            if value_due_decimal < 0:
                raise ValueError("Valor a receber não pode ser negativo")
            if value_due_decimal > final_value_after_discount:
                raise ValueError(
                    f"Valor a receber ({value_due_decimal}) não pode ser maior que o valor final após desconto ({final_value_after_discount})"
                )
        
        total_covered = total_paid + value_due_decimal
        
        # Permitir pagamento totalmente a prazo (sem payment_entries) se value_due = total
        # Permitir pagamento parcial (com payment_entries + value_due) se soma = total
        # Permitir pagamento à vista (apenas payment_entries) se total_paid = total
        
        # Validar contra o valor final após desconto (não o valor bruto)
        if abs(total_covered - final_value_after_discount) > Decimal('0.01'):  # Tolerância de 1 centavo
            if value_due_decimal > 0 and total_paid == 0:
                # Pagamento totalmente a prazo
                raise ValueError(
                    f"O valor a receber ({value_due_decimal}) deve ser igual ao valor final após desconto ({final_value_after_discount})"
                )
            elif value_due_decimal > 0 and total_paid > 0:
                # Pagamento parcial
                raise ValueError(
                    f"A soma dos pagamentos ({total_paid}) + valor a receber ({value_due_decimal}) deve ser igual ao valor final após desconto ({final_value_after_discount})"
                )
            else:
                # Pagamento à vista
                raise ValueError(
                    f"A soma dos pagamentos ({total_paid}) deve ser igual ao valor final após desconto ({final_value_after_discount})"
                )
        
        # 7. Ajustar net_value baseado em is_paid e pagamentos
        # IMPORTANTE: 
        # - Se is_paid=False e não há pagamentos (conta a receber total): net_value = 0
        # - Se há pagamentos parciais: net_value = valor dos pagamentos (já calculado acima)
        # - Se is_paid=True: net_value = valor total (já calculado acima)
        # O net_value já foi calculado considerando apenas os pagamentos imediatos (payment_entries_to_create)
        # Se não há pagamentos imediatos e is_paid=False, então net_value deve ser 0
        if not payment_entries_to_create and not is_paid:
            # Pagamento totalmente a prazo: não registrar no caixa ainda
            # O net_value será 0 e será atualizado quando receber a conta
            net_value_for_cash = Decimal('0.00')
            total_profit_for_cash = Decimal('0.00') - total_cost  # Lucro negativo (custo já foi)
        else:
            # Pagamento à vista ou parcial: usar o net_value calculado dos pagamentos feitos agora
            # O net_value já foi calculado considerando apenas os pagamentos imediatos
            net_value_for_cash = net_value
            total_profit_for_cash = net_value - total_cost
        
        # 8. Calcular lucro
        total_profit = total_profit_for_cash
        
        # 9. Criar Transaction
        # IMPORTANTE: Se is_paid=False, o net_value será 0 (não entra no caixa ainda)
        # O net_value será atualizado quando receber a conta a receber
        # Usar datetime.now() (timezone-naive, horário local) para que a data do pagamento
        # seja registrada no dia correto conforme o timezone local do servidor
        # Isso garante que pagamentos feitos no dia 25 apareçam no caixa do dia 25
        new_transaction = Transaction(
            tenant_id=tenant_id_str,
            appointment_id=appointment_id_str,
            date_time=datetime.now(),
            gross_value=gross_value,  # Valor bruto original (para histórico)
            discount=discount_value,  # Valor do desconto aplicado
            net_value=net_value_for_cash,  # Valor líquido (0 se conta a receber, senão valor calculado)
            total_cost=total_cost,
            total_profit=total_profit_for_cash,  # Lucro (negativo se conta a receber, senão calculado)
            additional_cost=additional_cost,
            is_paid=is_paid
        )
        
        db_session.add(new_transaction)
        await db_session.flush()  # Para obter o ID da transação
        
        # 10. Criar PaymentEntry para cada forma de pagamento (se houver pagamentos agora)
        # E criar Debtor se houver valor a receber (pagamento parcial ou total a prazo)
        new_debtor = None
        
        # Criar PaymentEntry para pagamentos feitos agora
        if payment_entries_to_create:
            for pe_data in payment_entries_to_create:
                # Recalcular taxa para este pagamento específico
                payment_method_id_str = pe_data['payment_method_id']
                value_paid = pe_data['value_paid']
                # Garantir que installments seja um int, não None
                installments_raw = pe_data.get('installments')
                installments = int(installments_raw) if installments_raw is not None else 1
                
                fee, _ = await FinancialService.calculate_payment_fee(
                    db_session=db_session,
                    tenant_id=tenant_id,
                    payment_method_id=UUID(payment_method_id_str),
                    service_price=value_paid,
                    installments=installments
                )
                
                payment_entry = PaymentEntry(
                    transaction_id=str(new_transaction.id),
                    payment_method_id=payment_method_id_str,
                    value_paid=value_paid,
                    installments=pe_data.get('installments'),
                    is_bank_account=pe_data['is_bank_account']
                )
                
                db_session.add(payment_entry)
        
        # Criar Debtor se houver valor a receber (pagamento parcial ou total a prazo)
        if value_due is not None and value_due > Decimal('0.00'):
            if not client_name or not due_date:
                raise ValueError("client_name e due_date são obrigatórios quando há valor a receber (value_due > 0)")
            
            # Remover timezone se presente (timezone-naive para compatibilidade com PostgreSQL)
            if due_date.tzinfo is not None:
                due_date = due_date.replace(tzinfo=None)
            
            # O value_due informado pelo usuário é o valor bruto a receber
            # Precisamos calcular o valor líquido proporcional, mas considerando que
            # o valor a receber não tem taxa de pagamento (será pago depois)
            # Portanto, o valor líquido a receber é igual ao valor bruto a receber
            # (sem descontar taxas, pois as taxas já foram descontadas dos pagamentos imediatos)
            debtor_net_value = value_due
            
            new_debtor = Debtor(
                transaction_id=str(new_transaction.id),
                client_name=client_name,
                client_phone=client_phone,
                due_date=due_date,
                value_due=debtor_net_value,  # Valor líquido devido (proporcional)
                status=DebtorStatus.PENDING
            )
            
            db_session.add(new_debtor)
        elif not is_paid and not payment_entries_to_create:
            # Caso especial: pagamento totalmente a prazo (sem pagamentos agora)
            if not client_name or not due_date:
                raise ValueError("client_name e due_date são obrigatórios quando is_paid=False")
            
            # Remover timezone se presente (timezone-naive para compatibilidade com PostgreSQL)
            if due_date.tzinfo is not None:
                due_date = due_date.replace(tzinfo=None)
            
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
        
        # 11. Atualizar Appointment
        appointment.status = AppointmentStatus.COMPLETED
        appointment.final_sale_value = net_value  # Valor líquido que entrou no caixa (ou que será recebido)
        appointment.service_cost = total_cost
        
        await db_session.commit()
        await db_session.refresh(new_transaction)
        await db_session.refresh(appointment)
        if new_debtor:
            await db_session.refresh(new_debtor)
        
        return new_transaction, appointment, new_debtor

