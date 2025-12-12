"""
Endpoints administrativos para estatísticas do Dashboard.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone, date
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from pydantic import BaseModel

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


class DashboardStatsResponse(BaseModel):
    """Estatísticas do dashboard."""
    appointments_today: int
    active_services: int
    pending_appointments: int


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Obter estatísticas do dashboard",
    description="Retorna estatísticas resumidas para o dashboard do tenant autenticado."
)
async def get_dashboard_stats(
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna estatísticas do dashboard:
    - Agendamentos de hoje
    - Serviços ativos
    - Agendamentos pendentes
    
    Args:
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        DashboardStatsResponse: Estatísticas do dashboard
    """
    # IMPORTANTE: Converter tenant_id para string (MySQL armazena UUIDs como String(36))
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        return DashboardStatsResponse(
            appointments_today=0,
            active_services=0,
            pending_appointments=0
        )
    
    # 1. Agendamentos de hoje
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    appointments_today_query = select(func.count(Appointment.id)).where(
        and_(
            Appointment.tenant_id == tenant_id_str,
            Appointment.start_datetime >= start_of_day,
            Appointment.start_datetime <= end_of_day,
            Appointment.status != AppointmentStatus.CANCELED
        )
    )
    appointments_today_result = await db.execute(appointments_today_query)
    appointments_today = appointments_today_result.scalar() or 0
    
    # 2. Serviços ativos (todos os serviços do tenant)
    active_services_query = select(func.count(Service.id)).where(
        Service.tenant_id == tenant_id_str
    )
    active_services_result = await db.execute(active_services_query)
    active_services = active_services_result.scalar() or 0
    
    # 3. Agendamentos pendentes (status PENDING)
    pending_appointments_query = select(func.count(Appointment.id)).where(
        and_(
            Appointment.tenant_id == tenant_id_str,
            Appointment.status == AppointmentStatus.PENDING
        )
    )
    pending_appointments_result = await db.execute(pending_appointments_query)
    pending_appointments = pending_appointments_result.scalar() or 0
    
    return DashboardStatsResponse(
        appointments_today=appointments_today,
        active_services=active_services,
        pending_appointments=pending_appointments
    )

