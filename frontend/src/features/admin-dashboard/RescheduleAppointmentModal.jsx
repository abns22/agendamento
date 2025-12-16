import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { api, formatDuration } from '../../utils/api'
import { Modal, Button, Card } from '../../components/ui'

/**
 * Modal de Reagendamento de Agendamento
 *
 * Permite que o administrador reagende um agendamento existente,
 * selecionando nova data, horário e (opcionalmente) outro serviço.
 */
const RescheduleAppointmentModal = ({ isOpen, onClose, services, appointment, onSuccess }) => {
  const [selectedDate, setSelectedDate] = useState(null)
  const [selectedTime, setSelectedTime] = useState(null)
  const [availableSlots, setAvailableSlots] = useState([])
  const [isLoadingSlots, setIsLoadingSlots] = useState(false)
  const [selectedService, setSelectedService] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Inicializar estado com dados do agendamento atual
  useEffect(() => {
    if (isOpen && appointment) {
      const startDate = new Date(appointment.start_datetime)
      setSelectedDate(startDate)
      setSelectedTime(format(startDate, 'HH:mm'))
      setSelectedService(appointment.service_id || '')
      setError(null)
      setAvailableSlots([])
    }
  }, [isOpen, appointment])

  // Buscar slots disponíveis quando data mudar
  useEffect(() => {
    if (isOpen && selectedDate) {
      fetchAvailableSlots()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, selectedDate])

  const fetchAvailableSlots = async () => {
    if (!selectedDate) return

    setIsLoadingSlots(true)
    setError(null)

    try {
      const dateStr = format(selectedDate, 'yyyy-MM-dd')
      const response = await api.get(`/api/v1/admin/appointments/availability?date=${dateStr}`)
      setAvailableSlots(response.data?.available_slots || [])
    } catch (err) {
      console.error('Erro ao buscar disponibilidade (reagendamento):', err)
      setError('Erro ao buscar horários disponíveis. Tente novamente.')
      setAvailableSlots([])
    } finally {
      setIsLoadingSlots(false)
    }
  }

  const handleDateChange = (date) => {
    setSelectedDate(date)
    setSelectedTime(null) // Limpar horário ao mudar data
  }

  const handleTimeSelect = (time) => {
    setSelectedTime(time)
  }

  const validateForm = () => {
    if (!appointment) {
      setError('Agendamento não encontrado')
      return false
    }

    if (!selectedService || selectedService === '') {
      setError('Selecione um serviço')
      return false
    }

    if (!selectedDate) {
      setError('Selecione uma data')
      return false
    }

    if (!selectedTime) {
      setError('Selecione um horário disponível')
      return false
    }

    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    setError(null)

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)

    try {
      // Combinar data e hora selecionados (timezone local)
      const [hours, minutes] = selectedTime.split(':')
      const dateTime = new Date(selectedDate)
      dateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0)

      // Converter para UTC antes de enviar
      const utcDateTime = new Date(dateTime.getTime() - dateTime.getTimezoneOffset() * 60000)

      const payload = {
        data_agendamento: utcDateTime.toISOString(),
        service_id: selectedService || null
      }

      await api.put(`/api/v1/admin/appointments/${appointment.id}/reschedule`, payload)

      try {
        if (typeof window !== 'undefined' && typeof window.alert === 'function') {
          window.alert('Agendamento reagendado com sucesso!')
        }
      } catch {
        // Ignorar falhas em alert
      }

      if (onSuccess) {
        await onSuccess()
      }

      onClose()
    } catch (err) {
      console.error('Erro ao reagendar agendamento:', err)
      setError(
        err.response?.data?.detail ||
          'Erro ao reagendar agendamento. Tente novamente.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // Utilitários de calendário (mesmo padrão do agendamento manual)
  const getCalendarDays = () => {
    const baseDate = selectedDate || new Date()
    const year = baseDate.getFullYear()
    const month = baseDate.getMonth()

    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDayOfWeek = firstDay.getDay()

    const days = []

    const prevMonth = new Date(year, month - 1, 0)
    const daysInPrevMonth = prevMonth.getDate()
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, daysInPrevMonth - i),
        isCurrentMonth: false
      })
    }

    for (let day = 1; day <= daysInMonth; day++) {
      days.push({
        date: new Date(year, month, day),
        isCurrentMonth: true
      })
    }

    const remainingDays = 42 - days.length
    for (let day = 1; day <= remainingDays; day++) {
      days.push({
        date: new Date(year, month + 1, day),
        isCurrentMonth: false
      })
    }

    return days
  }

  const navigateMonth = (direction) => {
    const baseDate = selectedDate || new Date()
    const newDate = new Date(baseDate)
    newDate.setMonth(baseDate.getMonth() + direction)
    setSelectedDate(newDate)
    setSelectedTime(null)
  }

  const navigateYear = (direction) => {
    const baseDate = selectedDate || new Date()
    const newDate = new Date(baseDate)
    newDate.setFullYear(baseDate.getFullYear() + direction)
    setSelectedDate(newDate)
    setSelectedTime(null)
  }

  const isToday = (date) => {
    const today = new Date()
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    )
  }

  const isSelected = (date) => {
    if (!selectedDate) return false
    return (
      date.getDate() === selectedDate.getDate() &&
      date.getMonth() === selectedDate.getMonth() &&
      date.getFullYear() === selectedDate.getFullYear()
    )
  }

  const isPast = (date) => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const compareDate = new Date(date)
    compareDate.setHours(0, 0, 0, 0)
    return compareDate < today
  }

  const calendarDays = getCalendarDays()
  const monthNames = [
    'Janeiro',
    'Fevereiro',
    'Março',
    'Abril',
    'Maio',
    'Junho',
    'Julho',
    'Agosto',
    'Setembro',
    'Outubro',
    'Novembro',
    'Dezembro'
  ]
  const weekDays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Reagendar Agendamento"
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Seleção de Serviço */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Serviço
          </label>
          {services.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800 text-sm">
                Nenhum serviço cadastrado. Por favor, cadastre um serviço antes
                de reagendar.
              </p>
            </div>
          ) : (
            <select
              value={selectedService}
              onChange={(e) => {
                setSelectedService(e.target.value)
                setError(null)
              }}
              className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-base"
              required
            >
              <option value="">Selecione um serviço</option>
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}{' '}
                  {service.duration_minutes
                    ? `(${formatDuration(service.duration_minutes)})`
                    : ''}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Calendário Interativo */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Nova Data
          </label>
          <Card className="p-4">
            {/* Navegação do Calendário */}
            <div className="flex items-center justify-between mb-4">
              <button
                type="button"
                onClick={() => navigateYear(-1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Ano anterior"
              >
                <span className="text-xl">⏮</span>
              </button>
              <button
                type="button"
                onClick={() => navigateMonth(-1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Mês anterior"
              >
                <span className="text-xl">◀</span>
              </button>
              <h3 className="text-lg font-bold text-text">
                {monthNames[(selectedDate || new Date()).getMonth()]}{' '}
                {(selectedDate || new Date()).getFullYear()}
              </h3>
              <button
                type="button"
                onClick={() => navigateMonth(1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Próximo mês"
              >
                <span className="text-xl">▶</span>
              </button>
              <button
                type="button"
                onClick={() => navigateYear(1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Próximo ano"
              >
                <span className="text-xl">⏭</span>
              </button>
            </div>

            {/* Dias da Semana */}
            <div className="grid grid-cols-7 gap-1 mb-2">
              {weekDays.map((day) => (
                <div
                  key={day}
                  className="text-center text-xs font-semibold text-gray-600 py-2"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Dias do Calendário */}
            <div className="grid grid-cols-7 gap-1">
              {calendarDays.map((dayObj, index) => {
                const { date, isCurrentMonth } = dayObj
                const disabled = isPast(date)
                const selected = isSelected(date)
                const today = isToday(date)

                return (
                  <button
                    key={index}
                    type="button"
                    onClick={() => !disabled && handleDateChange(date)}
                    disabled={disabled}
                    className={`
                      aspect-square p-2 text-sm rounded-lg transition-all
                      ${!isCurrentMonth ? 'text-gray-300' : ''}
                      ${
                        disabled
                          ? 'cursor-not-allowed opacity-50'
                          : 'hover:bg-gray-100 cursor-pointer'
                      }
                      ${selected ? 'bg-primary text-white font-bold' : ''}
                      ${
                        today && !selected
                          ? 'bg-primary/10 font-semibold'
                          : ''
                      }
                    `}
                  >
                    {date.getDate()}
                  </button>
                )
              })}
            </div>
          </Card>
        </div>

        {/* Slots de Horário */}
        {selectedDate && (
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Novo Horário Disponível
            </label>

            {isLoadingSlots ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : availableSlots.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-yellow-800 text-sm">
                  Não há horários disponíveis para esta data.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                {availableSlots.map((slot) => (
                  <button
                    key={slot}
                    type="button"
                    onClick={() => handleTimeSelect(slot)}
                    className={`
                      px-4 py-2 rounded-lg border-2 transition-all
                      ${
                        selectedTime === slot
                          ? 'bg-primary text-white border-primary font-semibold'
                          : 'bg-white text-gray-700 border-gray-300 hover:border-primary hover:bg-primary/5'
                      }
                    `}
                  >
                    {slot}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Erro */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Preview */}
        {selectedDate && selectedTime && appointment && (
          <div className="bg-primary/5 border border-primary rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Novo horário:</p>
            <p className="font-semibold text-text">
              {format(selectedDate, "EEEE, dd 'de' MMMM 'de' yyyy", {
                locale: ptBR
              })}{' '}
              às {selectedTime}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Cliente: {appointment.customer_name || 'Não informado'}
            </p>
          </div>
        )}

        {/* Botões */}
        <div className="flex flex-col sm:flex-row gap-3 justify-end pt-4 border-t border-gray-200">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isSubmitting}
            className="w-full sm:w-auto"
          >
            Voltar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={
              isSubmitting ||
              !selectedTime ||
              !selectedService ||
              !selectedDate ||
              !appointment
            }
            className="w-full sm:w-auto"
          >
            {isSubmitting ? 'Reagendando...' : 'Confirmar Reagendamento'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default RescheduleAppointmentModal


