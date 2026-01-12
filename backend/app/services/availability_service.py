"""
Serviço de Disponibilidade de Horários (Availability Service).

Este serviço implementa a lógica crítica de cálculo de slots disponíveis
para agendamento, garantindo que não haja sobreposição de horários
e respeitando os horários de funcionamento do estúdio.

Algoritmo Principal:
1. Busca configuração de horário de funcionamento
2. Busca duração do serviço
3. Busca agendamentos existentes (colisões)
4. Gera slots candidatos em intervalos regulares
5. Testa colisão de cada slot com agendamentos existentes
6. Retorna apenas os slots livres
"""
from typing import List
from uuid import UUID
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.schedule_config import ScheduleConfig
from app.models.stop_time import StopTime
from app.models.service import Service
from app.models.appointment import Appointment, AppointmentStatus


class AvailabilityService:
    """
    Serviço responsável por calcular horários disponíveis para agendamento.
    
    Implementa o algoritmo de geração de slots com detecção de colisões
    usando a fórmula de intersecção de intervalos.
    """
    
    # Intervalo padrão para geração de slots (em minutos)
    # Slots serão gerados a cada 15 minutos por padrão
    DEFAULT_SLOT_INTERVAL_MINUTES = 15
    
    @staticmethod
    async def get_available_slots(
        db_session: AsyncSession,
        tenant_id: UUID,
        service_id: UUID,
        date_str: str  # Formato: 'YYYY-MM-DD'
    ) -> List[str]:
        """
        Calcula e retorna uma lista de horários disponíveis para agendamento.
        
        Args:
            db_session: Sessão assíncrona do banco de dados
            tenant_id: UUID do tenant (empresa)
            service_id: UUID do serviço a ser agendado
            date_str: Data no formato 'YYYY-MM-DD'
            
        Returns:
            List[str]: Lista de horários disponíveis no formato 'HH:MM'
                      Ex: ['09:00', '09:15', '09:30', ...]
        
        Raises:
            ValueError: Se a data for inválida ou não houver configuração de horário
        """
        
        # ============================================================
        # PASSO 1: VALIDAÇÃO DE ENTRADA
        # ============================================================
        # Converta date_str para um objeto datetime.date
        # Trate exceções de formato inválido e retorne erro apropriado
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f"Data inválida: {date_str}. Use o formato 'YYYY-MM-DD'")
        
        # Obter o dia da semana (0=Segunda, 6=Domingo)
        day_of_week = target_date.weekday()
        
        # IMPORTANTE: Converter tenant_id para string (MySQL armazena UUIDs como String(36))
        tenant_id_str = str(tenant_id) if tenant_id else None
        if not tenant_id_str:
            raise ValueError("tenant_id é obrigatório")
        
        # ============================================================
        # PASSO 2: CONSULTA DE CONFIGURAÇÃO DE HORÁRIO
        # ============================================================
        # Busque no DB (ScheduleConfig) o horário de abertura e fechamento
        # para o tenant_id e o dia da semana correspondente à date_str
        # 
        # IMPORTANTE: Verifique se is_closed == True (estúdio fechado neste dia)
        # Se fechado, retorne lista vazia []
        schedule_query = select(ScheduleConfig).where(
            and_(
                ScheduleConfig.tenant_id == tenant_id_str,
                ScheduleConfig.day_of_week == day_of_week
            )
        )
        schedule_result = await db_session.execute(schedule_query)
        schedule_config = schedule_result.scalar_one_or_none()
        
        if not schedule_config:
            raise ValueError(f"Configuração de horário não encontrada para o dia {day_of_week}")
        
        if schedule_config.is_closed:
            return []  # Estúdio fechado neste dia
        
        # Extrair horários de abertura e fechamento
        opening_time = schedule_config.start_time
        closing_time = schedule_config.end_time
        
        # ============================================================
        # PASSO 3: CONSULTA DE DURAÇÃO DO SERVIÇO
        # ============================================================
        # Busque a duration_minutes do Service usando o service_id
        # Valide se o serviço existe e pertence ao tenant_id
        # IMPORTANTE: Converter service_id para string se necessário (MySQL armazena UUIDs como String(36))
        service_id_str = str(service_id) if service_id else None
        tenant_id_str = str(tenant_id) if tenant_id else None
        
        if not service_id_str or not tenant_id_str:
            raise ValueError(f"service_id e tenant_id são obrigatórios")
        
        service_query = select(Service).where(
            and_(
                Service.id == service_id_str,
                Service.tenant_id == tenant_id_str
            )
        )
        service_result = await db_session.execute(service_query)
        service = service_result.scalar_one_or_none()
        
        if not service:
            raise ValueError(f"Serviço não encontrado ou não pertence ao tenant")
        
        service_duration_minutes = service.duration_minutes
        
        # ============================================================
        # PASSO 4: CONSULTA DE COLISÕES (AGENDAMENTOS EXISTENTES)
        # ============================================================
        # Busque todos os Appointments já Confirmados ou Pendentes
        # (status != 'CANCELED') para o tenant_id na date_str
        # 
        # IMPORTANTE: Use filtro de data com timezone-naive (PostgreSQL usa TIMESTAMP WITHOUT TIME ZONE)
        # Crie datetime objects para início e fim do dia sem timezone
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)
        
        appointments_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.start_datetime >= start_of_day,
                Appointment.start_datetime < end_of_day + timedelta(days=1),
                Appointment.status != AppointmentStatus.CANCELED
            )
        )
        appointments_result = await db_session.execute(appointments_query)
        existing_appointments = appointments_result.scalars().all()
        
        # ============================================================
        # PASSO 4.5: CONSULTA DE STOP TIMES (INTERVALOS DE PARADA/ALMOÇO)
        # ============================================================
        # Busque todos os StopTimes configurados para o tenant no dia da semana
        stop_times_query = select(StopTime).where(
            and_(
                StopTime.tenant_id == tenant_id_str,
                StopTime.day_of_week == day_of_week
            )
        )
        stop_times_result = await db_session.execute(stop_times_query)
        stop_times = stop_times_result.scalars().all()
        
        # ============================================================
        # PASSO 5: GERAÇÃO DE SLOTS CANDIDATOS
        # ============================================================
        # Crie um loop que percorre desde o horário de abertura até
        # o horário de fechamento, gerando slots candidatos em intervalos
        # lógicos (ex: a cada 15 minutos, 30 minutos ou o menor intervalo
        # entre os serviços)
        # 
        # Para cada horário de início (candidate_start), calcule o horário
        # de fim do agendamento (candidate_end) usando a duration_minutes
        # do serviço
        # 
        # LÓGICA DO LOOP:
        # 1. Inicie com candidate_start = opening_time
        # 2. Calcule candidate_end = candidate_start + service_duration_minutes
        # 3. Se candidate_end > closing_time, pare o loop (não cabe mais)
        # 4. Avance candidate_start pelo intervalo (ex: +15 minutos)
        # 5. Repita até não caber mais
        
        available_slots = []
        slot_interval = timedelta(minutes=AvailabilityService.DEFAULT_SLOT_INTERVAL_MINUTES)
        
        # Converter opening_time e closing_time para datetime no dia alvo
        # IMPORTANTE: Criar datetimes sem timezone (timezone-naive) para compatibilidade com PostgreSQL
        candidate_start_datetime = datetime.combine(target_date, opening_time)
        closing_datetime = datetime.combine(target_date, closing_time)
        
        # Loop principal de geração de slots candidatos
        while True:
            # Calcular horário de fim do agendamento
            candidate_end_datetime = candidate_start_datetime + timedelta(minutes=service_duration_minutes)
            
            # Verificar se o agendamento cabe no horário de funcionamento
            if candidate_end_datetime > closing_datetime:
                break  # Não cabe mais nenhum slot
            
            # ============================================================
            # PASSO 6: TESTE DE COLISÃO
            # ============================================================
            # Para cada slot candidato gerado, itere sobre a lista de
            # agendamentos existentes (as colisões). Use a Fórmula de
            # Intersecção de Intervalos para verificar se:
            # 
            # (candidate_start < existing_appointment_end) AND 
            # (candidate_end > existing_appointment_start)
            # 
            # Se essa condição for verdadeira, há colisão (sobreposição)
            # e o slot NÃO está disponível.
            # 
            # FÓRMULA DE COLISÃO EXPLICADA:
            # Dois intervalos [A_start, A_end] e [B_start, B_end] se sobrepõem se:
            # A_start < B_end AND A_end > B_start
            # 
            # Aplicado ao nosso caso:
            # candidate_start < existing_end AND candidate_end > existing_start
            
            has_collision = False
            
            for appointment in existing_appointments:
                # Extrair horários de início e fim do agendamento existente
                # Os appointments estão em UTC
                existing_start = appointment.start_datetime
                existing_end = appointment.end_datetime
                
                # Remover timezone se presente (timezone-naive para compatibilidade com PostgreSQL)
                if existing_start.tzinfo is not None:
                    existing_start = existing_start.replace(tzinfo=None)
                if existing_end.tzinfo is not None:
                    existing_end = existing_end.replace(tzinfo=None)
                
                # Aplicar fórmula de intersecção de intervalos
                # Se houver sobreposição, marcar como colisão
                if (candidate_start_datetime < existing_end and 
                    candidate_end_datetime > existing_start):
                    has_collision = True
                    break  # Já encontrou colisão, não precisa verificar os demais
            
            # ============================================================
            # PASSO 6.5: TESTE DE COLISÃO COM STOP TIMES
            # ============================================================
            # Verificar se o slot candidato colide com algum intervalo de parada/almoço
            if not has_collision:
                for stop_time in stop_times:
                    # Converter horários de parada para datetime no dia alvo
                    stop_start_datetime = datetime.combine(target_date, stop_time.start_time)
                    stop_end_datetime = datetime.combine(target_date, stop_time.end_time)
                    
                    # Aplicar fórmula de intersecção de intervalos
                    # Se houver sobreposição com qualquer StopTime, marcar como colisão
                    if (candidate_start_datetime < stop_end_datetime and 
                        candidate_end_datetime > stop_start_datetime):
                        has_collision = True
                        break  # Já encontrou colisão, não precisa verificar os demais
            
            # ============================================================
            # PASSO 7: COMPILAÇÃO DO RESULTADO
            # ============================================================
            # Se o slot candidato não colidir com nenhum agendamento
            # existente e estiver dentro do horário de funcionamento do
            # estúdio, adicione o candidate_start (formatado como string
            # 'HH:MM') à lista final de horários disponíveis
            
            if not has_collision:
                # Formatar horário como string 'HH:MM'
                time_str = candidate_start_datetime.strftime('%H:%M')
                available_slots.append(time_str)
            
            # Avançar para o próximo slot candidato
            candidate_start_datetime += slot_interval
        
        # Retornar lista de horários disponíveis ordenada
        return sorted(available_slots)
    
    @staticmethod
    async def is_slot_available(
        db_session: AsyncSession,
        tenant_id: UUID,
        service_id: UUID,
        start_datetime: datetime
    ) -> bool:
        """
        Verifica se um horário específico está disponível para agendamento.
        
        Este método é usado para verificação de concorrência antes de criar
        um agendamento, garantindo que o slot ainda está livre.
        
        Args:
            db_session: Sessão assíncrona do banco de dados
            tenant_id: UUID do tenant
            service_id: UUID do serviço
            start_datetime: Data e hora de início do agendamento (UTC)
            
        Returns:
            bool: True se o slot estiver disponível, False caso contrário
            
        Raises:
            ValueError: Se o serviço não for encontrado ou não houver configuração
        """
        # Buscar serviço para obter a duração
        # IMPORTANTE: Converter service_id e tenant_id para string (MySQL armazena UUIDs como String(36))
        service_id_str = str(service_id) if service_id else None
        tenant_id_str = str(tenant_id) if tenant_id else None
        
        if not service_id_str or not tenant_id_str:
            raise ValueError("service_id e tenant_id são obrigatórios")
        
        service_query = select(Service).where(
            and_(
                Service.id == service_id_str,
                Service.tenant_id == tenant_id_str
            )
        )
        service_result = await db_session.execute(service_query)
        service = service_result.scalar_one_or_none()
        
        if not service:
            raise ValueError("Serviço não encontrado ou não pertence ao tenant")
        
        # Calcular horário de fim
        end_datetime = start_datetime + timedelta(minutes=service.duration_minutes)
        
        # Buscar configuração de horário para o dia da semana
        target_date = start_datetime.date()
        day_of_week = target_date.weekday()
        
        schedule_query = select(ScheduleConfig).where(
            and_(
                ScheduleConfig.tenant_id == tenant_id_str,
                ScheduleConfig.day_of_week == day_of_week
            )
        )
        schedule_result = await db_session.execute(schedule_query)
        schedule_config = schedule_result.scalar_one_or_none()
        
        if not schedule_config:
            raise ValueError(f"Configuração de horário não encontrada para o dia {day_of_week}")
        
        if schedule_config.is_closed:
            return False  # Estúdio fechado
        
        # Verificar se o horário está dentro do funcionamento
        opening_time = schedule_config.start_time
        closing_time = schedule_config.end_time
        opening_datetime = datetime.combine(target_date, opening_time)
        closing_datetime = datetime.combine(target_date, closing_time)
        
        # Remover timezone se presente (timezone-naive para compatibilidade com PostgreSQL)
        if start_datetime.tzinfo is not None:
            start_datetime = start_datetime.replace(tzinfo=None)
        if end_datetime.tzinfo is not None:
            end_datetime = end_datetime.replace(tzinfo=None)
        
        # Verificar se está dentro do horário de funcionamento
        if start_datetime < opening_datetime or end_datetime > closing_datetime:
            return False
        
        # Buscar agendamentos que possam colidir
        appointments_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.start_datetime < end_datetime,
                Appointment.end_datetime > start_datetime,
                Appointment.status != AppointmentStatus.CANCELED
            )
        )
        appointments_result = await db_session.execute(appointments_query)
        conflicting_appointments = appointments_result.scalars().all()
        
        # Se houver conflitos, o slot não está disponível
        return len(conflicting_appointments) == 0
    
    @staticmethod
    async def is_slot_available_with_duration(
        db_session: AsyncSession,
        tenant_id: UUID,
        start_datetime: datetime,
        total_duration_minutes: int
    ) -> bool:
        """
        Verifica se um horário específico está disponível para agendamento usando duração total.
        
        Este método é usado para verificação de disponibilidade com múltiplos serviços,
        onde a duração total já foi calculada.
        
        Args:
            db_session: Sessão assíncrona do banco de dados
            tenant_id: UUID do tenant
            start_datetime: Data e hora de início do agendamento (UTC)
            total_duration_minutes: Duração total em minutos (soma de todos os serviços)
            
        Returns:
            bool: True se o slot estiver disponível, False caso contrário
            
        Raises:
            ValueError: Se não houver configuração de horário
        """
        tenant_id_str = str(tenant_id) if tenant_id else None
        if not tenant_id_str:
            raise ValueError("tenant_id é obrigatório")
        
        # Calcular horário de fim
        end_datetime = start_datetime + timedelta(minutes=total_duration_minutes)
        
        # Buscar configuração de horário para o dia da semana
        target_date = start_datetime.date()
        day_of_week = target_date.weekday()
        
        schedule_query = select(ScheduleConfig).where(
            and_(
                ScheduleConfig.tenant_id == tenant_id_str,
                ScheduleConfig.day_of_week == day_of_week
            )
        )
        schedule_result = await db_session.execute(schedule_query)
        schedule_config = schedule_result.scalar_one_or_none()
        
        if not schedule_config:
            raise ValueError(f"Configuração de horário não encontrada para o dia {day_of_week}")
        
        if schedule_config.is_closed:
            return False  # Estúdio fechado
        
        # Verificar se o horário está dentro do funcionamento
        opening_time = schedule_config.start_time
        closing_time = schedule_config.end_time
        opening_datetime = datetime.combine(target_date, opening_time)
        closing_datetime = datetime.combine(target_date, closing_time)
        
        # Remover timezone se presente (timezone-naive para compatibilidade com PostgreSQL)
        if start_datetime.tzinfo is not None:
            start_datetime = start_datetime.replace(tzinfo=None)
        if end_datetime.tzinfo is not None:
            end_datetime = end_datetime.replace(tzinfo=None)
        
        # Verificar se está dentro do horário de funcionamento
        if start_datetime < opening_datetime or end_datetime > closing_datetime:
            return False
        
        # Buscar agendamentos que possam colidir
        appointments_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.start_datetime < end_datetime,
                Appointment.end_datetime > start_datetime,
                Appointment.status != AppointmentStatus.CANCELED
            )
        )
        appointments_result = await db_session.execute(appointments_query)
        conflicting_appointments = appointments_result.scalars().all()
        
        # Se houver conflitos, o slot não está disponível
        return len(conflicting_appointments) == 0
    
    @staticmethod
    async def get_available_slots_with_duration(
        db_session: AsyncSession,
        tenant_id: UUID,
        total_duration_minutes: int,
        date_str: str  # Formato: 'YYYY-MM-DD'
    ) -> List[str]:
        """
        Calcula e retorna uma lista de horários disponíveis para agendamento
        usando uma duração total fornecida (útil para múltiplos serviços).
        
        Args:
            db_session: Sessão assíncrona do banco de dados
            tenant_id: UUID do tenant (empresa)
            total_duration_minutes: Duração total em minutos (soma de todos os serviços)
            date_str: Data no formato 'YYYY-MM-DD'
            
        Returns:
            List[str]: Lista de horários disponíveis no formato 'HH:MM'
                      Ex: ['09:00', '09:15', '09:30', ...]
        
        Raises:
            ValueError: Se a data for inválida ou não houver configuração de horário
        """
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f"Data inválida: {date_str}. Use o formato 'YYYY-MM-DD'")
        
        day_of_week = target_date.weekday()
        
        tenant_id_str = str(tenant_id) if tenant_id else None
        if not tenant_id_str:
            raise ValueError("tenant_id é obrigatório")
        
        if total_duration_minutes <= 0:
            raise ValueError("Duração total deve ser maior que zero")
        
        schedule_query = select(ScheduleConfig).where(
            and_(
                ScheduleConfig.tenant_id == tenant_id_str,
                ScheduleConfig.day_of_week == day_of_week
            )
        )
        schedule_result = await db_session.execute(schedule_query)
        schedule_config = schedule_result.scalar_one_or_none()
        
        if not schedule_config:
            raise ValueError(f"Configuração de horário não encontrada para {date_str}")
        
        if schedule_config.is_closed:
            return []
        
        opening_time = schedule_config.start_time
        closing_time = schedule_config.end_time
        
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)
        
        appointments_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.start_datetime >= start_of_day,
                Appointment.start_datetime < end_of_day + timedelta(days=1),
                Appointment.status != AppointmentStatus.CANCELED
            )
        )
        appointments_result = await db_session.execute(appointments_query)
        existing_appointments = appointments_result.scalars().all()
        
        stop_times_query = select(StopTime).where(
            and_(
                StopTime.tenant_id == tenant_id_str,
                StopTime.day_of_week == day_of_week
            )
        )
        stop_times_result = await db_session.execute(stop_times_query)
        stop_times = stop_times_result.scalars().all()
        
        available_slots = []
        slot_interval = timedelta(minutes=AvailabilityService.DEFAULT_SLOT_INTERVAL_MINUTES)
        
        candidate_start_datetime = datetime.combine(target_date, opening_time)
        closing_datetime = datetime.combine(target_date, closing_time)
        
        while True:
            candidate_end_datetime = candidate_start_datetime + timedelta(minutes=total_duration_minutes)
            
            if candidate_end_datetime > closing_datetime:
                break
            
            has_collision = False
            
            for apt in existing_appointments:
                if (candidate_start_datetime < apt.end_datetime and 
                    candidate_end_datetime > apt.start_datetime):
                    has_collision = True
                    break
            
            if not has_collision:
                for stop_time in stop_times:
                    stop_start_datetime = datetime.combine(target_date, stop_time.start_time)
                    stop_end_datetime = datetime.combine(target_date, stop_time.end_time)
                    if (candidate_start_datetime < stop_end_datetime and 
                        candidate_end_datetime > stop_start_datetime):
                        has_collision = True
                        break
            
            if not has_collision:
                time_str = candidate_start_datetime.strftime('%H:%M')
                available_slots.append(time_str)
            
            candidate_start_datetime += slot_interval
        
        return sorted(available_slots)

