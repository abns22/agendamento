"""
Serviço de Utilitários para Agendamentos.

Este serviço fornece funções auxiliares para cálculos relacionados a agendamentos,
como duração total e preço total de múltiplos serviços.
"""
from typing import List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.service import Service
from app.services.promotion_service import PromotionService


class AppointmentService:
    """
    Serviço com funções auxiliares para agendamentos.
    """
    
    @staticmethod
    async def calculate_total_duration(
        db_session: AsyncSession,
        tenant_id: UUID,
        service_ids: List[UUID]
    ) -> int:
        """
        Calcula a duração total (em minutos) somando as durações de todos os serviços.
        
        Args:
            db_session: Sessão assíncrona do banco de dados
            tenant_id: UUID do tenant
            service_ids: Lista de UUIDs dos serviços
            
        Returns:
            int: Duração total em minutos
            
        Raises:
            ValueError: Se algum serviço não for encontrado ou não pertencer ao tenant
        """
        if not service_ids:
            raise ValueError("Lista de service_ids não pode estar vazia")
        
        tenant_id_str = str(tenant_id)
        total_duration = 0
        
        for service_id in service_ids:
            service_id_str = str(service_id)
            
            service_query = select(Service).where(
                and_(
                    Service.id == service_id_str,
                    Service.tenant_id == tenant_id_str
                )
            )
            service_result = await db_session.execute(service_query)
            service = service_result.scalar_one_or_none()
            
            if not service:
                raise ValueError(f"Serviço {service_id} não encontrado ou não pertence ao tenant")
            
            total_duration += service.duration_minutes
        
        return total_duration
    
    @staticmethod
    async def calculate_total_value(
        db_session: AsyncSession,
        tenant_id: UUID,
        service_ids: List[UUID],
        appointment_datetime: datetime = None
    ) -> Decimal:
        """
        Calcula o valor total do agendamento somando os preços efetivos (com promoções) de todos os serviços.
        
        Args:
            db_session: Sessão assíncrona do banco de dados
            tenant_id: UUID do tenant
            service_ids: Lista de UUIDs dos serviços
            appointment_datetime: Data/hora do agendamento (opcional, usa datetime.now() se não fornecido)
            
        Returns:
            Decimal: Valor total (soma dos preços efetivos dos serviços)
            
        Raises:
            ValueError: Se algum serviço não for encontrado ou não pertencer ao tenant
        """
        if not service_ids:
            raise ValueError("Lista de service_ids não pode estar vazia")
        
        if appointment_datetime is None:
            appointment_datetime = datetime.now()
        
        tenant_id_str = str(tenant_id)
        total_value = Decimal('0.00')
        
        for service_id in service_ids:
            service_id_str = str(service_id)
            
            service_query = select(Service).where(
                and_(
                    Service.id == service_id_str,
                    Service.tenant_id == tenant_id_str
                )
            )
            service_result = await db_session.execute(service_query)
            service = service_result.scalar_one_or_none()
            
            if not service:
                raise ValueError(f"Serviço {service_id} não encontrado ou não pertence ao tenant")
            
            # Obter preço efetivo (com promoção se ativa)
            effective_price = PromotionService.get_effective_price(service)
            total_value += Decimal(str(effective_price))
        
        return total_value
    
    @staticmethod
    async def get_services_by_ids(
        db_session: AsyncSession,
        tenant_id: UUID,
        service_ids: List[UUID]
    ) -> List[Service]:
        """
        Busca todos os serviços por seus IDs.
        
        Args:
            db_session: Sessão assíncrona do banco de dados
            tenant_id: UUID do tenant
            service_ids: Lista de UUIDs dos serviços
            
        Returns:
            List[Service]: Lista de serviços encontrados
            
        Raises:
            ValueError: Se algum serviço não for encontrado ou não pertencer ao tenant
        """
        if not service_ids:
            return []
        
        tenant_id_str = str(tenant_id)
        services = []
        
        for service_id in service_ids:
            service_id_str = str(service_id)
            
            service_query = select(Service).where(
                and_(
                    Service.id == service_id_str,
                    Service.tenant_id == tenant_id_str
                )
            )
            service_result = await db_session.execute(service_query)
            service = service_result.scalar_one_or_none()
            
            if not service:
                raise ValueError(f"Serviço {service_id} não encontrado ou não pertence ao tenant")
            
            services.append(service)
        
        return services
    
    @staticmethod
    def calculate_end_datetime(start_datetime: datetime, total_duration_minutes: int) -> datetime:
        """
        Calcula o horário de término baseado no horário de início e duração total.
        
        Args:
            start_datetime: Data/hora de início
            total_duration_minutes: Duração total em minutos
            
        Returns:
            datetime: Data/hora de término
        """
        return start_datetime + timedelta(minutes=total_duration_minutes)

