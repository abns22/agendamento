import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card } from '../../components/ui'
import { api, formatCurrency } from '../../utils/api'

/**
 * Widget de Próximos Agendamentos para o Dashboard.
 * 
 * Exibe uma lista de agendamentos futuros agrupados por dia,
 * com scroll interno e navegação para detalhes.
 */
const UpcomingAppointmentsWidget = () => {
  const navigate = useNavigate()
  const [upcomingData, setUpcomingData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [notificationDays, setNotificationDays] = useState(3)

  // Buscar próximos agendamentos
  useEffect(() => {
    const fetchUpcomingAppointments = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const response = await api.get('/api/v1/admin/dashboard/upcoming')
        setUpcomingData(response.data)
        
        // Calcular notification_days baseado no último dia retornado
        if (response.data.days && response.data.days.length > 0) {
          const lastDay = response.data.days[response.data.days.length - 1]
          if (lastDay?.date) {
            const today = new Date()
            today.setHours(0, 0, 0, 0) // Zerar horas para comparação correta
            const lastDate = new Date(lastDay.date)
            lastDate.setHours(0, 0, 0, 0)
            const diffTime = lastDate - today
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
            // Se diffDays for 0 ou negativo, usar 3 como padrão
            setNotificationDays(diffDays > 0 ? diffDays : 3)
          }
        }
      } catch (err) {
        console.error('Erro ao carregar próximos agendamentos:', err)
        setError('Erro ao carregar próximos agendamentos')
      } finally {
        setIsLoading(false)
      }
    }

    fetchUpcomingAppointments()
  }, [])

  // Formatar data/hora para exibição
  const formatDateTime = (dateLabel, startTime) => {
    // dateLabel já vem formatado do backend (ex: "Hoje", "Amanhã", "15 de Janeiro")
    // startTime vem no formato "HH:MM"
    
    // Se for "Hoje" ou "Amanhã", usar formato: "Hoje às 14h" ou "Amanhã às 10h"
    if (dateLabel === 'Hoje' || dateLabel === 'Amanhã') {
      const hour = parseInt(startTime.split(':')[0])
      const minute = parseInt(startTime.split(':')[1])
      const timeStr = minute > 0 ? `${hour}h${minute.toString().padStart(2, '0')}` : `${hour}h`
      return `${dateLabel} às ${timeStr}`
    }
    
    // Para outras datas, usar formato: "07/01 às 10h"
    // Extrair dia e mês do dateLabel (ex: "15 de Janeiro" -> "15/01")
    const dateMatch = dateLabel.match(/(\d+)\s+de\s+(\w+)/)
    if (dateMatch) {
      const day = dateMatch[1]
      const monthName = dateMatch[2]
      const months = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
      }
      const month = months[monthName.toLowerCase()] || '01'
      const hour = parseInt(startTime.split(':')[0])
      const minute = parseInt(startTime.split(':')[1])
      const timeStr = minute > 0 ? `${hour}h${minute.toString().padStart(2, '0')}` : `${hour}h`
      return `${day}/${month} às ${timeStr}`
    }
    
    // Fallback: usar dateLabel + horário
    return `${dateLabel} às ${startTime}`
  }

  // Navegar para detalhes do agendamento
  const handleAppointmentClick = (appointmentId) => {
    // Redirecionar para a agenda com o appointment_id na URL
    // A AgendaPage pode usar isso para abrir o modal de detalhes
    navigate(`/admin/agenda?appointment_id=${appointmentId}`)
  }

  // Calcular total de agendamentos
  const totalAppointments = upcomingData?.days?.reduce(
    (total, day) => total + (day.appointments?.length || 0),
    0
  ) || 0

  return (
    <Card className="bg-white border-gray-200">
      <div className="p-4">
        {/* Título */}
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          Próximos Agendamentos (Próximos {notificationDays} {notificationDays === 1 ? 'dia' : 'dias'})
        </h3>

        {/* Conteúdo */}
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-3 text-gray-600">Carregando...</span>
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-600">
            {error}
          </div>
        ) : totalAppointments === 0 ? (
          <div className="text-center py-8 text-gray-500">
            Nenhum agendamento para os próximos dias.
          </div>
        ) : (
          <div 
            className="space-y-4 overflow-y-auto"
            style={{ maxHeight: '300px' }}
          >
            {upcomingData.days.map((day, dayIndex) => (
              <div key={day.date || dayIndex} className="space-y-2">
                {/* Label do Dia */}
                <div className="flex items-center gap-2 mb-2">
                  <div className="h-px flex-1 bg-gray-200"></div>
                  <span className="text-sm font-semibold text-gray-600 px-2">
                    {day.date_label}
                  </span>
                  <div className="h-px flex-1 bg-gray-200"></div>
                </div>

                {/* Lista de Agendamentos do Dia */}
                <div className="space-y-2">
                  {day.appointments.map((appointment, aptIndex) => (
                    <button
                      key={appointment.id || aptIndex}
                      onClick={() => handleAppointmentClick(appointment.id)}
                      className="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-primary hover:bg-primary/5 transition-all duration-200 hover:shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          {/* Nome do Cliente (negrito) */}
                          <p className="font-semibold text-gray-900 mb-1 truncate">
                            {appointment.client_name || 'Cliente não informado'}
                          </p>
                          
                          {/* Data/Hora formatada */}
                          <p className="text-sm text-gray-600 mb-1">
                            {formatDateTime(day.date_label, appointment.start_time)}
                          </p>
                          
                          {/* Serviço */}
                          <p className="text-sm text-gray-500">
                            {appointment.services || 'Sem serviço'}
                          </p>
                        </div>
                        
                        {/* Valor (se disponível) */}
                        {appointment.total_price && (
                          <div className="flex-shrink-0">
                            <p className="text-sm font-semibold text-primary whitespace-nowrap">
                              {formatCurrency(parseFloat(appointment.total_price))}
                            </p>
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

export default UpcomingAppointmentsWidget

