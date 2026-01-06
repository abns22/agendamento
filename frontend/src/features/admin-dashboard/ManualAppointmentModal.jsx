import React, { useState, useEffect, useCallback } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { api, formatDuration, formatCurrency } from '../../utils/api'
import { Modal, Button, Card } from '../../components/ui'

/**
 * Modal de Agendamento Manual
 * 
 * Permite que o administrador crie ou edite agendamentos manualmente,
 * selecionando data e horário disponível.
 * 
 * Props:
 * - isOpen: boolean - Controla se o modal está aberto
 * - onClose: function - Callback ao fechar o modal
 * - services: array - Lista de serviços disponíveis
 * - onSuccess: function - Callback após sucesso (criar ou editar)
 * - appointment: object (opcional) - Agendamento para edição (se fornecido, entra em modo edição)
 */
const ManualAppointmentModal = ({ isOpen, onClose, services, onSuccess, appointment = null }) => {
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [selectedTime, setSelectedTime] = useState(null)
  const [availableSlots, setAvailableSlots] = useState([])
  const [isLoadingSlots, setIsLoadingSlots] = useState(false)
  const [selectedServices, setSelectedServices] = useState([]) // Array de serviços selecionados
  const [customerName, setCustomerName] = useState('')
  const [customerContact, setCustomerContact] = useState('')
  const [customerBirthDate, setCustomerBirthDate] = useState('') // Data de nascimento (YYYY-MM-DD)
  const [selectedClientId, setSelectedClientId] = useState(null) // ID do cliente selecionado (se houver)
  const [clientSearchQuery, setClientSearchQuery] = useState('') // Termo de busca de clientes
  const [clientSearchResults, setClientSearchResults] = useState([]) // Resultados da busca
  const [isSearchingClients, setIsSearchingClients] = useState(false) // Loading da busca
  const [showClientSuggestions, setShowClientSuggestions] = useState(false) // Mostrar/ocultar sugestões
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Determinar se está em modo edição
  const isEditMode = !!appointment
  
  // Carregar dados do agendamento ao abrir em modo edição
  useEffect(() => {
    if (isOpen) {
      if (isEditMode && appointment) {
        // Modo edição: carregar dados do agendamento
        // Carregar data e horário
        const startDate = new Date(appointment.start_datetime)
        setSelectedDate(startDate)
        
        // Formatar horário como HH:MM
        const hours = String(startDate.getHours()).padStart(2, '0')
        const minutes = String(startDate.getMinutes()).padStart(2, '0')
        setSelectedTime(`${hours}:${minutes}`)
        
        // Carregar serviços selecionados
        if (appointment.service_ids && appointment.service_ids.length > 0) {
          const selectedServicesFromAppointment = services.filter(s => 
            appointment.service_ids.includes(s.id)
          )
          setSelectedServices(selectedServicesFromAppointment)
        } else if (appointment.service_id) {
          // Fallback para service_id único (compatibilidade)
          const service = services.find(s => s.id === appointment.service_id)
          if (service) {
            setSelectedServices([service])
          }
        }
        
        // Carregar dados do cliente
        if (appointment.customer_name) {
          setCustomerName(appointment.customer_name)
        }
        if (appointment.customer_phone) {
          setCustomerContact(appointment.customer_phone)
        }
        
        // Buscar slots disponíveis para a data (chamada assíncrona)
        const fetchSlotsForEdit = async () => {
          try {
            const dateStr = format(startDate, 'yyyy-MM-dd')
            setIsLoadingSlots(true)
            const response = await api.get(`/api/v1/admin/appointments/availability?date=${dateStr}`)
            setAvailableSlots(response.data?.available_slots || [])
          } catch (err) {
            console.error('Erro ao buscar disponibilidade:', err)
            setAvailableSlots([])
          } finally {
            setIsLoadingSlots(false)
          }
        }
        fetchSlotsForEdit()
      } else {
        // Modo criação: resetar estado
        setSelectedDate(new Date())
        setSelectedTime(null)
        setSelectedServices([])
        setCustomerName('')
        setCustomerContact('')
        setCustomerBirthDate('')
        setSelectedClientId(null)
        setClientSearchQuery('')
        setClientSearchResults([])
        setShowClientSuggestions(false)
        setError(null)
        setAvailableSlots([])
      }
    }
  }, [isOpen, services, appointment, isEditMode])

  // Buscar clientes com debounce
  useEffect(() => {
    if (!isOpen) return
    
    // Se query está vazia, limpar resultados
    if (!clientSearchQuery.trim()) {
      setClientSearchResults([])
      setShowClientSuggestions(false)
      return
    }

    // Debounce: aguardar 300ms após parar de digitar
    const timeoutId = setTimeout(async () => {
      if (clientSearchQuery.trim().length < 2) {
        setClientSearchResults([])
        setShowClientSuggestions(false)
        return
      }

      try {
        setIsSearchingClients(true)
        const response = await api.get(`/api/v1/admin/clients/search?q=${encodeURIComponent(clientSearchQuery.trim())}`)
        setClientSearchResults(response.data || [])
        setShowClientSuggestions(true)
      } catch (err) {
        console.error('Erro ao buscar clientes:', err)
        setClientSearchResults([])
        setShowClientSuggestions(false)
      } finally {
        setIsSearchingClients(false)
      }
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [clientSearchQuery, isOpen])

  // Função auxiliar para converter data ISO para YYYY-MM-DD sem problemas de timezone
  const isoDateToDateInput = useCallback((isoDateString) => {
    if (!isoDateString) return ''
    // Se a string já está no formato YYYY-MM-DD, retornar direto
    if (/^\d{4}-\d{2}-\d{2}$/.test(isoDateString)) {
      return isoDateString
    }
    // Para strings ISO (ex: "2024-01-15T00:00:00Z"), extrair apenas a parte da data
    // Isso evita problemas de conversão de timezone
    const datePart = isoDateString.split('T')[0]
    return datePart || ''
  }, [])

  // Selecionar cliente do autocomplete
  const handleSelectClient = useCallback((client) => {
    setSelectedClientId(client.id)
    setCustomerName(client.name)
    setCustomerContact(client.phone_number || '')
    // Formatar data de nascimento para YYYY-MM-DD (formato do input date)
    setCustomerBirthDate(isoDateToDateInput(client.birth_date))
    setShowClientSuggestions(false)
    setClientSearchQuery('')
  }, [isoDateToDateInput])

  // Limpar seleção de cliente (permitir cadastro manual)
  const handleClearClientSelection = useCallback(() => {
    setSelectedClientId(null)
    setCustomerName('')
    setCustomerContact('')
    setCustomerBirthDate('')
    setClientSearchQuery('')
    setShowClientSuggestions(false)
  }, [])

  // Fechar sugestões ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showClientSuggestions && !event.target.closest('.client-search-container')) {
        setShowClientSuggestions(false)
      }
    }

    if (showClientSuggestions) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showClientSuggestions])

  // Buscar slots disponíveis quando data mudar (apenas em modo criação)
  useEffect(() => {
    if (isOpen && selectedDate && !isEditMode) {
      fetchAvailableSlots()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, selectedDate, isEditMode])

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

  const handleServiceToggle = (service) => {
    const serviceId = service.id
    const isSelected = selectedServices.find(s => s.id === serviceId)
    
    if (isSelected) {
      // Remover da seleção
      setSelectedServices(selectedServices.filter(s => s.id !== serviceId))
    } else {
      // Adicionar à seleção
      setSelectedServices([...selectedServices, service])
    }
  }
  
  const isServiceSelected = (serviceId) => {
    return selectedServices.some(s => s.id === serviceId)
  }
  
  // Calcular duração total e valor total (atualização dinâmica)
  const totalDuration = selectedServices.reduce((sum, s) => sum + (s.duration_minutes || 0), 0)
  const totalValue = selectedServices.reduce((sum, s) => {
    // Verificar se há promoção ativa (usar promotion_active se disponível, senão calcular)
    let isPromoActive = false
    if (s.promotion_active !== undefined && s.promotion_active !== null) {
      isPromoActive = s.promotion_active === true
    } else if (s.is_promotional && s.promotion_start_date && s.promotion_end_date && s.promotional_value) {
      const now = new Date()
      const startDate = new Date(s.promotion_start_date)
      const endDate = new Date(s.promotion_end_date)
      isPromoActive = now >= startDate && now <= endDate
    }
    if (isPromoActive && s.promotional_value) {
      return sum + parseFloat(s.promotional_value)
    }
    return sum + parseFloat(s.price)
  }, 0)
  
  // Calcular valores originais (para comparação em modo edição)
  const originalDuration = appointment ? (appointment.service_ids?.length > 0 
    ? services.filter(s => appointment.service_ids.includes(s.id))
        .reduce((sum, s) => sum + (s.duration_minutes || 0), 0)
    : appointment.service_id 
      ? services.find(s => s.id === appointment.service_id)?.duration_minutes || 0
      : 0
  ) : 0
  
  const originalValue = appointment ? (appointment.total_value ? parseFloat(appointment.total_value) : 0) : 0
  
  // Determinar se houve mudanças
  const hasChanges = isEditMode && (
    totalDuration !== originalDuration || 
    totalValue !== originalValue ||
    (appointment && selectedTime && (() => {
      const [hours, minutes] = selectedTime.split(':')
      const newDateTime = new Date(selectedDate)
      newDateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0)
      const originalDateTime = new Date(appointment.start_datetime)
      return newDateTime.getTime() !== originalDateTime.getTime()
    })())
  )

  const validateForm = () => {
    // Validar serviços
    if (!selectedServices || selectedServices.length === 0) {
      setError('Selecione pelo menos um serviço')
      return false
    }
    
    // Validar data e horário
    if (!selectedDate) {
      setError('Selecione uma data')
      return false
    }
    
    if (!selectedTime) {
      setError('Selecione um horário disponível')
      return false
    }
    
    // Validar nome do cliente
    if (!customerName.trim() || customerName.trim().length < 2) {
      setError('Nome do cliente é obrigatório e deve ter pelo menos 2 caracteres')
      return false
    }
    
    // Validar contato do cliente
    if (!customerContact.trim()) {
      setError('Contato do cliente é obrigatório')
      return false
    }
    
    // Validar formato de contato (telefone ou e-mail)
    const contactTrimmed = customerContact.trim()
    const isPhone = /^[\d\s\(\)\-\+]+$/.test(contactTrimmed)
    const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactTrimmed)
    
    if (!isPhone && !isEmail) {
      setError('Contato deve ser um telefone válido ou um e-mail válido')
      return false
    }
    
    // Validar telefone (mínimo 10 dígitos)
    if (isPhone) {
      const digitsOnly = contactTrimmed.replace(/\D/g, '')
      if (digitsOnly.length < 10) {
        setError('Telefone deve conter pelo menos 10 dígitos')
        return false
      }
    }
    
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Limpar erro anterior
    setError(null)
    
    // Validar formulário
    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      // Combinar data e hora selecionados (timezone local)
      const [hours, minutes] = selectedTime.split(':')
      const dateTime = new Date(selectedDate)
      dateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0)
      
      // Converter para UTC (o backend espera UTC e confia que já está em UTC)
      const utcDateTime = new Date(dateTime.getTime() - (dateTime.getTimezoneOffset() * 60000))
      
      if (isEditMode && appointment) {
        // Modo edição: PUT para atualizar agendamento
        const payload = {
          service_ids: selectedServices.map(s => s.id), // Array de IDs de serviços
          start_datetime: utcDateTime.toISOString()
        }
        
        try {
          await api.put(`/api/v1/admin/appointments/${appointment.id}`, payload)
          
          // Feedback visual de sucesso
          try {
            if (typeof window !== 'undefined' && typeof window.alert === 'function') {
              window.alert('Agendamento atualizado com sucesso!')
            }
          } catch {
            // Ignorar falhas em alert
          }
          
          if (onSuccess) {
            onSuccess()
          }
          
          onClose()
        } catch (err) {
          console.error('Erro ao atualizar agendamento:', err)
          
          // Tratar erro 409 (conflito de horário)
          if (err.response?.status === 409) {
            setError('Não há tempo suficiente para adicionar este serviço sem conflitar com o próximo cliente.')
          } else {
            setError(
              err.response?.data?.detail || 
              'Erro ao atualizar agendamento. Tente novamente.'
            )
          }
        }
      } else {
        // Modo criação: POST para criar novo agendamento
        const payload = {
          // tenant_id é inferido pelo backend a partir do token/header
          service_ids: selectedServices.map(s => s.id), // Array de IDs de serviços
          data_agendamento: utcDateTime.toISOString(),
          cliente_nome: customerName.trim(),
          cliente_contato: customerContact.trim(),
          // Se cliente foi selecionado, enviar client_id, senão enviar apenas dados para criar/buscar
          ...(selectedClientId ? { client_id: selectedClientId } : {}),
          // Enviar aniversário se preenchido (formato YYYY-MM-DD)
          ...(customerBirthDate ? { cliente_aniversario: customerBirthDate } : {})
        }

        await api.post('/api/v1/admin/appointments/manual', payload)

        // Feedback visual de sucesso
        try {
          if (typeof window !== 'undefined' && typeof window.alert === 'function') {
            window.alert('Agendamento manual criado com sucesso!')
          }
        } catch {
          // Ignorar falhas em alert
        }
        
        if (onSuccess) {
          onSuccess()
        }
        
        onClose()
      }
    } catch (err) {
      console.error('Erro ao processar agendamento:', err)
      setError(
        err.response?.data?.detail || 
        `Erro ao ${isEditMode ? 'atualizar' : 'criar'} agendamento. Tente novamente.`
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
    <Modal isOpen={isOpen} onClose={onClose} title={isEditMode ? "Editar Agendamento" : "Agendamento Manual"} size="lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Seleção de Serviços (Múltipla) */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-700">
              Serviços *
            </label>
            {selectedServices.length > 0 && (
              <span className="text-sm text-primary font-semibold">
                {selectedServices.length} selecionado{selectedServices.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
          {services.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800 text-sm">
                Nenhum serviço cadastrado. Por favor, cadastre um serviço antes de criar um agendamento.
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-60 overflow-y-auto border-2 border-gray-300 rounded-lg p-3">
              {services.map(service => {
                const isSelected = isServiceSelected(service.id)
                // Verificar se promoção está ativa (usar promotion_active se disponível, senão calcular)
                let isPromotionActive = false
                if (service.promotion_active !== undefined && service.promotion_active !== null) {
                  // Usar promotion_active do backend se disponível
                  isPromotionActive = service.promotion_active === true
                } else if (service.is_promotional && service.promotion_start_date && service.promotion_end_date && service.promotional_value) {
                  // Calcular manualmente se promotion_active não estiver disponível
                  const now = new Date()
                  const startDate = new Date(service.promotion_start_date)
                  const endDate = new Date(service.promotion_end_date)
                  isPromotionActive = now >= startDate && now <= endDate
                }
                const effectivePrice = isPromotionActive && service.promotional_value
                  ? parseFloat(service.promotional_value)
                  : parseFloat(service.price)
                const originalPrice = parseFloat(service.price)
                
                return (
                  <div
                    key={service.id}
                    onClick={() => handleServiceToggle(service)}
                    className={`flex items-center p-3 rounded-lg cursor-pointer transition-colors relative ${
                      isSelected
                        ? 'bg-primary bg-opacity-10 border-2 border-primary'
                        : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                    }`}
                    style={{
                      borderColor: !isSelected && isPromotionActive && service.promotion_color_code
                        ? service.promotion_color_code
                        : undefined
                    }}
                  >
                    {/* Badge de Promoção */}
                    {isPromotionActive && service.promotion_display_name && !isSelected && (
                      <div 
                        className="absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-bold text-white shadow-md z-10"
                        style={{ backgroundColor: service.promotion_color_code || '#FF0000' }}
                      >
                        {service.promotion_display_name}
                      </div>
                    )}
                    
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center mr-3 flex-shrink-0 ${
                      isSelected
                        ? 'bg-primary border-primary'
                        : 'border-gray-300 bg-white'
                    }`}>
                      {isSelected && (
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-text">{service.name}</div>
                      <div className="text-sm text-gray-600 flex items-center gap-2">
                        <span>{formatDuration(service.duration_minutes)}</span>
                        <span>•</span>
                        <div className="flex items-center gap-2">
                          {isPromotionActive && originalPrice > effectivePrice && (
                            <span className="text-gray-400 line-through text-xs">
                              {formatCurrency(originalPrice)}
                            </span>
                          )}
                          <span className={`font-bold ${isPromotionActive ? 'text-red-600' : 'text-gray-600'}`}>
                            {formatCurrency(effectivePrice)}
                          </span>
                        </div>
                      </div>
                    </div>
                    {/* Botão para remover (se selecionado) */}
                    {isSelected && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleServiceToggle(service)
                        }}
                        className="ml-2 p-1 hover:bg-primary/20 rounded-full transition-colors flex-shrink-0"
                        aria-label={`Remover ${service.name}`}
                        type="button"
                      >
                        <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
          
          {/* Resumo em tempo real */}
          {selectedServices.length > 0 && (
            <div className="mt-3 bg-primary/5 border-2 border-primary/20 rounded-lg p-3">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-4">
                    <span className="font-semibold text-text">
                      Total: <span className="text-primary">{selectedServices.length}</span> serviço{selectedServices.length > 1 ? 's' : ''}
                    </span>
                    <span className="font-semibold text-text">
                      {isEditMode ? 'Nova ' : ''}Duração: <span className="text-primary">{formatDuration(totalDuration)}</span>
                      {isEditMode && originalDuration !== totalDuration && (
                        <span className="text-gray-500 ml-1">
                          (anterior: {formatDuration(originalDuration)})
                        </span>
                      )}
                    </span>
                  </div>
                  <span className="text-lg font-bold text-primary">
                    {isEditMode ? 'Novo ' : ''}Valor: {formatCurrency(totalValue)}
                    {isEditMode && originalValue !== totalValue && (
                      <span className="text-gray-500 text-sm font-normal ml-1">
                        (anterior: {formatCurrency(originalValue)})
                      </span>
                    )}
                  </span>
                </div>
                {isEditMode && hasChanges && (
                  <div className="text-xs text-blue-600 font-semibold pt-1 border-t border-primary/20">
                    ⚠️ Alterações detectadas - O horário será recalculado automaticamente
                  </div>
                )}
              </div>
            </div>
          )}
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
              {isEditMode ? 'Horário' : 'Horário Disponível'} *
            </label>
            
            {isLoadingSlots ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : availableSlots.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-yellow-800 text-sm">
                  {isEditMode 
                    ? 'Não há horários disponíveis para esta data. Você pode manter o horário atual ou selecionar outro horário disponível.'
                    : 'Não há horários disponíveis para esta data.'
                  }
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
          {/* Busca de Cliente (Autocomplete) */}
          <div className="client-search-container">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Buscar Cliente Existente (Opcional)
            </label>
            <div className="relative">
              <input
                type="text"
                value={clientSearchQuery}
                onChange={(e) => {
                  setClientSearchQuery(e.target.value)
                  setError(null)
                  // Se limpar a busca, também limpar seleção
                  if (!e.target.value.trim()) {
                    handleClearClientSelection()
                  }
                }}
                onFocus={() => {
                  if (clientSearchResults.length > 0) {
                    setShowClientSuggestions(true)
                  }
                }}
                className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-base"
                placeholder="Digite nome ou telefone para buscar..."
                disabled={!!selectedClientId}
              />
              {selectedClientId && (
                <button
                  type="button"
                  onClick={handleClearClientSelection}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  title="Limpar seleção"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
              
              {/* Sugestões de Clientes */}
              {showClientSuggestions && clientSearchResults.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-white border-2 border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {isSearchingClients && (
                    <div className="p-4 text-center text-gray-500 text-sm">
                      Buscando...
                    </div>
                  )}
                  {!isSearchingClients && clientSearchResults.map((client) => (
                    <button
                      key={client.id}
                      type="button"
                      onClick={() => handleSelectClient(client)}
                      className="w-full text-left px-4 py-3 hover:bg-primary/10 border-b border-gray-100 last:border-b-0 transition-colors"
                    >
                      <div className="font-semibold text-text">{client.name}</div>
                      <div className="text-sm text-gray-600">{client.phone_number}</div>
                      {client.birth_date && (() => {
                        // Extrair apenas a parte da data (YYYY-MM-DD) para evitar problemas de timezone
                        let dateStr = client.birth_date
                        if (typeof client.birth_date === 'string' && client.birth_date.includes('T')) {
                          dateStr = client.birth_date.split('T')[0]
                        }
                        // Parsear a data diretamente: YYYY-MM-DD
                        const [year, month, day] = dateStr.split('-').map(Number)
                        const date = new Date(year, month - 1, day) // month é 0-indexed no JS
                        return (
                          <div className="text-xs text-gray-500 mt-1">
                            Nascimento: {format(date, 'dd/MM/yyyy', { locale: ptBR })}
                          </div>
                        )
                      })()}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {selectedClientId && (
              <p className="text-xs text-green-600 mt-1">
                ✓ Cliente selecionado - Campos preenchidos automaticamente
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Nome do Cliente *
            </label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => {
                setCustomerName(e.target.value)
                setError(null)
                // Se editar manualmente, limpar seleção de cliente
                if (selectedClientId) {
                  setSelectedClientId(null)
                }
              }}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-base"
              placeholder="Ex: João Silva"
              minLength={2}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Mínimo de 2 caracteres
            </p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Contato (Telefone ou E-mail) *
            </label>
            <input
              type="text"
              value={customerContact}
              onChange={(e) => {
                setCustomerContact(e.target.value)
                setError(null)
                // Se editar manualmente, limpar seleção de cliente
                if (selectedClientId) {
                  setSelectedClientId(null)
                }
              }}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-base"
              placeholder="Ex: 11987654321 ou email@exemplo.com"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Telefone (mínimo 10 dígitos) ou e-mail válido
            </p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Data de Nascimento (Opcional)
            </label>
            <input
              type="date"
              value={customerBirthDate}
              onChange={(e) => {
                setCustomerBirthDate(e.target.value)
                setError(null)
                // Se editar manualmente, limpar seleção de cliente
                if (selectedClientId) {
                  setSelectedClientId(null)
                }
              }}
              max={format(new Date(), 'yyyy-MM-dd')} // Não permitir datas futuras
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-base"
            />
            <p className="text-xs text-gray-500 mt-1">
              Informe a data de nascimento para aparecer na seção de aniversariantes
            </p>
          </div>
        </div>
        )}

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
        <div className="flex flex-col sm:flex-row gap-3 justify-end pt-4 border-t border-gray-200">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isSubmitting}
            className="w-full sm:w-auto"
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={
              isSubmitting || 
              !selectedTime || 
              selectedServices.length === 0 || 
              (!isEditMode && (!customerName.trim() || !customerContact.trim())) ||
              services.length === 0 ||
              (isEditMode && !hasChanges) // Em modo edição, só permitir salvar se houver mudanças
            }
            className="w-full sm:w-auto"
          >
            {isSubmitting 
              ? (isEditMode ? 'Salvando...' : 'Agendando...') 
              : (isEditMode ? 'Salvar Alterações' : 'Agendar Manualmente')
            }
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default ManualAppointmentModal

