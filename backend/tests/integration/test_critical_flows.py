"""
Testes de integração para fluxos críticos do sistema.

Estes testes validam funcionalidades complexas e sensíveis:
- Isolamento multi-tenant (segurança)
- Finalização de transações (lógica financeira)
- Relatórios do caixa (agregação de dados)
- Ordenação da agenda (UX)
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from app.models.transaction import Transaction
from app.models.payment_entry import PaymentEntry
from app.models.expense import Expense


@pytest.mark.asyncio
async def test_multi_tenant_isolation(
    authenticated_client_a: TestClient,
    authenticated_client_b: TestClient,
    tenant_a,
    tenant_b,
    admin_user_a,
    admin_user_b,
    db_session: AsyncSession
):
    """
    Teste de Segurança: Isolamento Multi-tenant
    
    Objetivo: Garantir que um usuário de um Tenant A nunca consiga 
    acessar ou modificar dados pertencentes a um Tenant B.
    
    Cenário:
    1. Criar dois tenants (A e B)
    2. Criar dois usuários admin (Admin A e Admin B)
    3. Criar um serviço no Tenant B
    4. Tentar acessar o serviço do Tenant B usando o cliente do Admin A
    5. Esperar status HTTP 403 ou 404
    """
    # Criar um serviço no Tenant B
    service_b_id = str(uuid4())
    service_b = Service(
        id=service_b_id,
        tenant_id=str(tenant_b.id),
        name="Serviço do Tenant B",
        duration_minutes=30,
        price=Decimal("50.00")
    )
    db_session.add(service_b)
    await db_session.commit()
    
    # Tentar acessar o serviço do Tenant B usando o cliente do Admin A
    response = authenticated_client_a.get(
        f"/api/v1/admin/services/{service_b_id}"
    )
    
    # Deve retornar 403 (Forbidden) ou 404 (Not Found)
    # O sistema deve garantir que o Admin A não veja dados do Tenant B
    assert response.status_code in [403, 404], \
        f"Esperado 403 ou 404, mas recebeu {response.status_code}. " \
        f"Resposta: {response.text}"
    
    # Verificar que o Admin B consegue acessar seu próprio serviço
    response_b = authenticated_client_b.get(
        f"/api/v1/admin/services/{service_b_id}"
    )
    assert response_b.status_code == 200, \
        f"Admin B deveria conseguir acessar seu próprio serviço. " \
        f"Status: {response_b.status_code}"


@pytest.mark.asyncio
async def test_transaction_finalization_with_promotion_and_fee(
    authenticated_client_a: TestClient,
    tenant_a,
    admin_user_a,
    service_with_promotion,
    payment_method_credit_card,
    db_session: AsyncSession
):
    """
    Teste de Finalização de Transação (POST /finalize)
    
    Objetivo: Garantir que a lógica financeira esteja correta 
    (promoção, custo, lucro).
    
    Cenário:
    1. Criar um agendamento com um serviço que tenha custo fixo e esteja sob promoção ativa
    2. Finalizar a venda usando uma forma de pagamento com taxa (Cartão de Débito com 5% de taxa)
    
    Verificações:
    - net_value (Valor Líquido) está correto (Valor Promocional + Taxa de Pagamento)
    - total_cost está correto (Custo Fixo do Serviço)
    - total_profit está correto (net_value - total_cost)
    """
    # Criar um agendamento
    appointment_id = str(uuid4())
    now = datetime.now(timezone.utc)
    start_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(minutes=service_with_promotion.duration_minutes)
    
    appointment = Appointment(
        id=appointment_id,
        tenant_id=str(tenant_a.id),
        service_id=str(service_with_promotion.id),
        customer_name="Cliente Teste",
        customer_phone="11999999999",
        start_datetime=start_time,
        end_datetime=end_time,
        status=AppointmentStatus.CONFIRMED,
        is_manual_block=False
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    
    # Valores esperados:
    # - Valor promocional: R$ 80.00
    # - Taxa de 5% sobre R$ 80.00: R$ 4.00
    # - Valor líquido (net_value): R$ 80.00 + R$ 4.00 = R$ 84.00
    # - Custo fixo: R$ 30.00
    # - Lucro: R$ 84.00 - R$ 30.00 = R$ 54.00
    
    expected_promotional_value = Decimal("80.00")
    expected_fee = expected_promotional_value * Decimal("0.05")  # 5%
    expected_net_value = expected_promotional_value + expected_fee  # R$ 84.00
    expected_cost = Decimal("30.00")
    expected_profit = expected_net_value - expected_cost  # R$ 54.00
    
    # Finalizar o agendamento
    response = authenticated_client_a.post(
        f"/api/v1/admin/appointments/{appointment_id}/finalize",
        json={
            "payment_entries": [
                {
                    "payment_method_id": str(payment_method_credit_card.id),
                    "value_paid": float(expected_net_value),
                    "installments": 1
                }
            ],
            "additional_cost": None,
            "is_paid": True
        }
    )
    
    assert response.status_code == 200, \
        f"Erro ao finalizar agendamento: {response.status_code}. " \
        f"Resposta: {response.text}"
    
    # Buscar a transação criada
    transaction_query = select(Transaction).where(
        Transaction.appointment_id == appointment_id
    )
    result = await db_session.execute(transaction_query)
    transaction = result.scalar_one_or_none()
    
    assert transaction is not None, "Transação não foi criada"
    
    # Verificar valores
    assert abs(Decimal(str(transaction.net_value)) - expected_net_value) < Decimal("0.01"), \
        f"net_value incorreto. Esperado: {expected_net_value}, " \
        f"Recebido: {transaction.net_value}"
    
    assert abs(Decimal(str(transaction.total_cost)) - expected_cost) < Decimal("0.01"), \
        f"total_cost incorreto. Esperado: {expected_cost}, " \
        f"Recebido: {transaction.total_cost}"
    
    assert abs(Decimal(str(transaction.total_profit)) - expected_profit) < Decimal("0.01"), \
        f"total_profit incorreto. Esperado: {expected_profit}, " \
        f"Recebido: {transaction.total_profit}"
    
    # Verificar que o agendamento foi marcado como COMPLETED
    await db_session.refresh(appointment)
    assert appointment.status == AppointmentStatus.COMPLETED, \
        "Agendamento deveria estar marcado como COMPLETED"


@pytest.mark.asyncio
async def test_cash_summary_aggregation(
    authenticated_client_a: TestClient,
    tenant_a,
    admin_user_a,
    service_with_promotion,
    payment_method_cash,
    db_session: AsyncSession
):
    """
    Teste de Relatórios do Caixa (GET /cash-summary)
    
    Objetivo: Garantir que o resumo financeiro agregue corretamente 
    as transações e as despesas no período.
    
    Cenário:
    1. Registrar 2 Transações no dia de hoje
    2. Registrar 1 Despesa no dia de hoje
    
    Verificações:
    - Testar a rota GET /cash-summary para o dia de hoje
    - Verificar se o total do faturamento e despesas correspondem 
      exatamente aos registros
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Criar 2 agendamentos
    appointments = []
    transactions = []
    total_net_revenue = Decimal("0.00")
    
    for i in range(2):
        appointment_id = str(uuid4())
        start_time = today_start.replace(hour=10 + i, minute=0)
        end_time = start_time + timedelta(minutes=service_with_promotion.duration_minutes)
        
        appointment = Appointment(
            id=appointment_id,
            tenant_id=str(tenant_a.id),
            service_id=str(service_with_promotion.id),
            customer_name=f"Cliente {i+1}",
            customer_phone=f"1199999999{i}",
            start_datetime=start_time,
            end_datetime=end_time,
            status=AppointmentStatus.CONFIRMED,
            is_manual_block=False
        )
        db_session.add(appointment)
        appointments.append(appointment)
        
        # Criar transação diretamente (simulando finalização)
        transaction_id = str(uuid4())
        net_value = Decimal("80.00")  # Valor promocional
        total_net_revenue += net_value
        
        transaction = Transaction(
            id=transaction_id,
            tenant_id=str(tenant_a.id),
            appointment_id=appointment_id,
            date_time=start_time,
            gross_value=net_value,
            net_value=net_value,
            total_cost=Decimal("30.00"),
            total_profit=net_value - Decimal("30.00"),
            is_paid=True
        )
        db_session.add(transaction)
        transactions.append(transaction)
        
        # Criar payment entry
        payment_entry = PaymentEntry(
            id=str(uuid4()),
            transaction_id=transaction_id,
            payment_method_id=str(payment_method_cash.id),
            value_paid=net_value,
            installments=1,
            is_bank_account=False
        )
        db_session.add(payment_entry)
        
        # Atualizar appointment para COMPLETED
        appointment.status = AppointmentStatus.COMPLETED
        appointment.service_cost = Decimal("30.00")
        appointment.final_sale_value = net_value
    
    # Criar 1 despesa
    expense_id = str(uuid4())
    expense_value = Decimal("50.00")
    expense = Expense(
        id=expense_id,
        tenant_id=str(tenant_a.id),
        description="Despesa de teste",
        value=expense_value,
        date_time=today_start.replace(hour=12, minute=0),
        category="Outros"
    )
    db_session.add(expense)
    
    await db_session.commit()
    
    # Buscar resumo do caixa para hoje
    today_str = now.strftime("%Y-%m-%d")
    response = authenticated_client_a.get(
        f"/api/v1/admin/reports/cash-summary?start_date={today_str}&end_date={today_str}"
    )
    
    assert response.status_code == 200, \
        f"Erro ao buscar resumo do caixa: {response.status_code}. " \
        f"Resposta: {response.text}"
    
    data = response.json()
    summary = data.get("summary", {})
    
    # Verificar faturamento líquido
    net_revenue = Decimal(str(summary.get("net_revenue", 0)))
    assert abs(net_revenue - total_net_revenue) < Decimal("0.01"), \
        f"Faturamento líquido incorreto. Esperado: {total_net_revenue}, " \
        f"Recebido: {net_revenue}"
    
    # Verificar despesas
    total_expenses = Decimal(str(summary.get("total_expenses", 0)))
    assert abs(total_expenses - expense_value) < Decimal("0.01"), \
        f"Total de despesas incorreto. Esperado: {expense_value}, " \
        f"Recebido: {total_expenses}"
    
    # Verificar número de transações
    total_transactions = summary.get("total_transactions", 0)
    assert total_transactions == 2, \
        f"Número de transações incorreto. Esperado: 2, " \
        f"Recebido: {total_transactions}"


@pytest.mark.asyncio
async def test_appointment_ordering_by_start_datetime(
    authenticated_client_a: TestClient,
    tenant_a,
    admin_user_a,
    service_with_promotion,
    db_session: AsyncSession
):
    """
    Teste de Ordenação da Agenda
    
    Objetivo: Garantir que a ordenação do GET /admin/appointments 
    pela start_datetime (ASC) seja obrigatória, conforme a última 
    implementação de UX.
    
    Cenário:
    1. Criar 3 agendamentos no mesmo dia em horários aleatórios (ex: 15h, 9h, 17h)
    
    Verificações:
    1. Chamar a rota e garantir que o primeiro agendamento na lista 
       retornada seja o das 9h
    2. Verificar que a ordem está correta: 9h, 15h, 17h
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    
    # Criar 3 agendamentos em horários aleatórios: 15h, 9h, 17h
    appointment_times = [
        (15, 0),  # 15:00
        (9, 0),   # 09:00
        (17, 0)   # 17:00
    ]
    
    appointments_created = []
    for hour, minute in appointment_times:
        appointment_id = str(uuid4())
        start_time = datetime.combine(today, datetime.min.time()).replace(
            hour=hour, minute=minute, tzinfo=timezone.utc
        )
        end_time = start_time + timedelta(minutes=service_with_promotion.duration_minutes)
        
        appointment = Appointment(
            id=appointment_id,
            tenant_id=str(tenant_a.id),
            service_id=str(service_with_promotion.id),
            customer_name=f"Cliente {hour}h",
            customer_phone=f"1199999999{hour}",
            start_datetime=start_time,
            end_datetime=end_time,
            status=AppointmentStatus.SCHEDULED,
            is_manual_block=False
        )
        db_session.add(appointment)
        appointments_created.append((appointment_id, start_time))
    
    await db_session.commit()
    
    # Buscar agendamentos do dia
    today_str = today.strftime("%Y-%m-%d")
    response = authenticated_client_a.get(
        f"/api/v1/admin/appointments?date={today_str}"
    )
    
    assert response.status_code == 200, \
        f"Erro ao buscar agendamentos: {response.status_code}. " \
        f"Resposta: {response.text}"
    
    appointments = response.json()
    
    # Filtrar apenas os agendamentos que criamos (pode haver outros)
    our_appointments = [
        apt for apt in appointments
        if apt["id"] in [apt_id for apt_id, _ in appointments_created]
    ]
    
    assert len(our_appointments) == 3, \
        f"Esperado 3 agendamentos, mas recebido {len(our_appointments)}"
    
    # Verificar que o primeiro agendamento é o das 9h
    first_appointment = our_appointments[0]
    first_start_time = datetime.fromisoformat(first_appointment["start_datetime"].replace("Z", "+00:00"))
    
    assert first_start_time.hour == 9, \
        f"Primeiro agendamento deveria ser às 9h, mas é às {first_start_time.hour}h"
    
    # Verificar ordem completa: 9h, 15h, 17h
    expected_hours = [9, 15, 17]
    actual_hours = [
        datetime.fromisoformat(apt["start_datetime"].replace("Z", "+00:00")).hour
        for apt in our_appointments
    ]
    
    assert actual_hours == expected_hours, \
        f"Ordem incorreta. Esperado: {expected_hours}, " \
        f"Recebido: {actual_hours}"

