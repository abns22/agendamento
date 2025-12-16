import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { api } from '../../utils/api'
import { Modal, Button, Card } from '../../components/ui'

/**
 * Modal de Agendamento Manual
 * 
 * Permite que o administrador crie agendamentos manualmente,
 * selecionando data e horário disponível.
 */
const ManualAppointmentModal = ({ isOpen, onClose, services, onSuccess }) => {
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [selectedTime, setSelectedTime] = useState(null)
  const [availableSlots, setAvailableSlots] = useState([])
  const [isLoadingSlots, setIsLoadingSlots] = useState(false)
  const [selectedService, setSelectedService] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [customerContact, setCustomerContact] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Resetar estado ao abrir/fechar modal
  useEffect(() => {
    if (isOpen) {
      setSelectedDate(new Date())
      setSelectedTime(null)
      setSelectedService(services.length > 0 ? services[0].id : '')
      setCustomerName('')
      setCustomerContact('')
      setError(null)
    }
  }, [isOpen, services])

  // Buscar slots disponíveis quando data mudar
  useEffect(() => {
    if (isOpen && selectedDate) {
      fetchAvailableSlots()
    }
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
      console.error('Erro ao buscar disponibilidade:', err)
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

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!selectedService) {
      setError('Selecione um serviço')
      return
    }
    
    if (!customerName.trim()) {
      setError('Nome do cliente é obrigatório')
      return
    }
    
    if (!customerContact.trim()) {
      setError('Contato do cliente é obrigatório')
      return
    }
    
    if (!selectedTime) {
      setError('Selecione um horário')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      // Combinar data e hora selecionados
      const [hours, minutes] = selectedTime.split(':')
      const dateTime = new Date(selectedDate)
      dateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0)
      
      // Converter para UTC (o backend espera UTC)
      const utcDateTime = new Date(dateTime.getTime() - (dateTime.getTimezoneOffset() * 60000))
      
      const payload = {
        service_id: selectedService,
        data_agendamento: utcDateTime.toISOString(),
        cliente_nome: customerName.trim(),
        cliente_contato: customerContact.trim()
      }

      await api.post('/api/v1/admin/appointments/manual', payload)
      
      if (onSuccess) {
        onSuccess()
      }
      
      onClose()
    } catch (err) {
      console.error('Erro ao criar agendamento:', err)
      setError(
        err.response?.data?.detail || 
        'Erro ao criar agendamento. Tente novamente.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // Gerar dias do mês para o calendário
  const getCalendarDays = () => {
    const year = selectedDate.getFullYear()
    const month = selectedDate.getMonth()
    
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDayOfWeek = firstDay.getDay()
    
    const days = []
    
    // Dias do mês anterior (para preencher início)
    const prevMonth = new Date(year, month - 1, 0)
    const daysInPrevMonth = prevMonth.getDate()
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, daysInPrevMonth - i),
        isCurrentMonth: false
      })
    }
    
    // Dias do mês atual
    for (let day = 1; day <= daysInMonth; day++) {
      days.push({
        date: new Date(year, month, day),
        isCurrentMonth: true
      })
    }
    
    // Dias do próximo mês (para preencher fim)
    const remainingDays = 42 - days.length // 6 semanas * 7 dias
    for (let day = 1; day <= remainingDays; day++) {
      days.push({
        date: new Date(year, month + 1, day),
        isCurrentMonth: false
      })
    }
    
    return days
  }

  const navigateMonth = (direction) => {
    const newDate = new Date(selectedDate)
    newDate.setMonth(selectedDate.getMonth() + direction)
    setSelectedDate(newDate)
  }

  const navigateYear = (direction) => {
    const newDate = new Date(selectedDate)
    newDate.setFullYear(selectedDate.getFullYear() + direction)
    setSelectedDate(newDate)
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
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ]
  const weekDays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Agendamento Manual" size="lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Seleção de Serviço */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Serviço *
          </label>
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            required
          >
            <option value="">Selecione um serviço</option>
            {services.map(service => (
              <option key={service.id} value={service.id}>
                {service.name}
              </option>
            ))}
          </select>
        </div>

        {/* Calendário Interativo */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Data *
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
                {monthNames[selectedDate.getMonth()]} {selectedDate.getFullYear()}
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
              {weekDays.map(day => (
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
                      ${disabled ? 'cursor-not-allowed opacity-50' : 'hover:bg-gray-100 cursor-pointer'}
                      ${selected ? 'bg-primary text-white font-bold' : ''}
                      ${today && !selected ? 'bg-primary/10 font-semibold' : ''}
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
              Horário Disponível *
            </label>
            
            {isLoadingSlots ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
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
                      ${selectedTime === slot
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

        {/* Dados do Cliente */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Nome do Cliente *
            </label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Ex: João Silva"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Contato (Telefone ou E-mail) *
            </label>
            <input
              type="text"
              value={customerContact}
              onChange={(e) => setCustomerContact(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Ex: 11987654321 ou email@exemplo.com"
              required
            />
          </div>
        </div>

        {/* Erro */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Preview da Seleção */}
        {selectedDate && selectedTime && (
          <div className="bg-primary/5 border border-primary rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Agendamento para:</p>
            <p className="font-semibold text-text">
              {format(selectedDate, "EEEE, dd 'de' MMMM 'de' yyyy", { locale: ptBR })} às {selectedTime}
            </p>
          </div>
        )}

        {/* Botões */}
        <div className="flex gap-3 justify-end">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting || !selectedTime || !selectedService}
          >
            {isSubmitting ? 'Criando...' : 'Criar Agendamento'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default ManualAppointmentModal

