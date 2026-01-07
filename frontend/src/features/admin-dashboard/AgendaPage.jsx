import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { format, startOfMonth, endOfMonth } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { api, formatCurrency, formatDuration } from '../../utils/api'
import { Card, Button, Modal, Input } from '../../components/ui'
import CheckoutModal from './CheckoutModal'
import ManualAppointmentModal from './ManualAppointmentModal'
import RescheduleAppointmentModal from './RescheduleAppointmentModal'

/**
 * Página de Gerenciamento de Agenda.
 * 
 * Funcionalidades:
 * - Seletor de data
 * - Listagem de agendamentos do dia
 * - Visualização em timeline/lista
 * - Ações: Confirmar, Cancelar, Editar
 * - Criar bloqueio manual
 */
const AgendaPage = () => {
  // Inicializar useSearchParams primeiro
  const [searchParams, setSearchParams] = useSearchParams()
  
  // Estados principais
  const [appointments, setAppointments] = useState([])
  const [services, setServices] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingServices, setIsLoadingServices] = useState(false)
  const [error, setError] = useState(null)
  const [selectedAppointment, setSelectedAppointment] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isBlockModalOpen, setIsBlockModalOpen] = useState(false)
  const [isCheckoutModalOpen, setIsCheckoutModalOpen] = useState(false)
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false)
  const [isManualAppointmentModalOpen, setIsManualAppointmentModalOpen] = useState(false)
  const [isRescheduleModalOpen, setIsRescheduleModalOpen] = useState(false)
  const [editingAppointment, setEditingAppointment] = useState(null)
  const [showActionMenu, setShowActionMenu] = useState(false)
  const [selectedService, setSelectedService] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [cancellationReason, setCancellationReason] = useState('')
  const [appointmentsSummary, setAppointmentsSummary] = useState(null)
  const [showAppointmentsSummary, setShowAppointmentsSummary] = useState(true)
  
  // Filtros - inicializar com valores padrão (serão sincronizados com URL via useEffect)
  const [searchQuery, setSearchQuery] = useState('')
  const [startDate, setStartDate] = useState(null)
  const [endDate, setEndDate] = useState(null)
  const [daysAhead, setDaysAhead] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [serviceFilter, setServiceFilter] = useState('')
  
  // Ref para debounce
  const searchDebounceRef = useRef(null)

  // Função helper para criar Date a partir de string YYYY-MM-DD sem problemas de timezone
  const parseDateFromString = useCallback((dateStr) => {
    if (!dateStr) return null
    try {
      // Parse da string YYYY-MM-DD diretamente, sem usar new Date() que pode ter problemas de timezone
      const [year, month, day] = dateStr.split('-').map(Number)
      // Criar Date usando componentes locais (sem timezone)
      return new Date(year, month - 1, day)
    } catch (e) {
      return null
    }
  }, [])

  // Sincronizar estados locais com URL quando ela mudar (ex: botão voltar/avançar)
  useEffect(() => {
    const search = searchParams.get('search') || ''
    const startDateParam = searchParams.get('start_date')
    const endDateParam = searchParams.get('end_date')
    const daysAheadParam = searchParams.get('days_ahead')
    const status = searchParams.get('status') || ''
    const serviceId = searchParams.get('service_id') || ''
    
    setSearchQuery(search)
    
    if (startDateParam) {
      const parsedDate = parseDateFromString(startDateParam)
      setStartDate(parsedDate)
    } else {
      setStartDate(null)
    }
    
    if (endDateParam) {
      const parsedDate = parseDateFromString(endDateParam)
      setEndDate(parsedDate)
    } else {
      setEndDate(null)
    }
    
    if (daysAheadParam) {
      const daysAheadNum = parseInt(daysAheadParam)
      setDaysAhead(isNaN(daysAheadNum) ? null : daysAheadNum)
    } else {
      setDaysAhead(null)
    }
    
    setStatusFilter(status)
    setServiceFilter(serviceId)
  }, [searchParams])

  // Formulário de bloqueio
  const [blockForm, setBlockForm] = useState({
    start_datetime: '',
    end_datetime: '',
    description: ''
  })

  // Função helper para formatar data sem problemas de timezone
  const formatDateForAPI = useCallback((date) => {
    if (!date) return null
    // Usar getFullYear, getMonth, getDate para evitar problemas de timezone
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }, [])

  // Função para atualizar URL com os filtros
  const updateURLParams = useCallback((updates) => {
    const newParams = new URLSearchParams(searchParams)

    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === '' || value === undefined) {
        newParams.delete(key)
      } else {
        if (value instanceof Date) {
          newParams.set(key, formatDateForAPI(value))
        } else {
          newParams.set(key, value.toString())
        }
      }
    })
    
    setSearchParams(newParams, { replace: true })
  }, [searchParams, setSearchParams, formatDateForAPI])

  // Função para obter data atual no timezone do Brasil (America/Sao_Paulo)
  const getBrazilianDate = useCallback(() => {
    const now = new Date()
    // Obter a data atual no timezone do Brasil
    const brazilDateStr = now.toLocaleString('pt-BR', { 
      timeZone: 'America/Sao_Paulo',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
    // Criar uma nova data a partir da string formatada (sem timezone)
    const [day, month, year] = brazilDateStr.split('/')
    return new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
  }, [])

  const fetchServices = async () => {
    try {
      setIsLoadingServices(true)
      const response = await api.get('/api/v1/admin/services')
      setServices(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar serviços:', err)
    } finally {
      setIsLoadingServices(false)
    }
  }

  const fetchAppointments = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Obter valores atuais dos filtros da URL
      const currentSearch = searchParams.get('search') || ''
      const currentDaysAhead = searchParams.get('days_ahead')
      const currentStartDate = searchParams.get('start_date')
      const currentEndDate = searchParams.get('end_date')
      const currentStatus = searchParams.get('status') || ''
      const currentServiceId = searchParams.get('service_id') || ''
      
      // Construir query params
      const params = new URLSearchParams()
      
      // Prioridade: days_ahead sobrescreve start_date/end_date
      if (currentDaysAhead) {
        params.append('days_ahead', currentDaysAhead)
      } else {
        if (currentStartDate) {
          params.append('start_date', currentStartDate)
        }
        if (currentEndDate) {
          params.append('end_date', currentEndDate)
        }
      }
      
      if (currentSearch) {
        params.append('search', currentSearch)
      }
      
      if (currentStatus) {
        params.append('status', currentStatus)
      }
      
      if (currentServiceId) {
        params.append('service_id', currentServiceId)
      }
      
      const response = await api.get(`/api/v1/admin/appointments?${params.toString()}`)
      setAppointments(response.data)
    } catch (err) {
      console.error('Erro ao carregar agendamentos:', err)
      setError('Erro ao carregar agendamentos. Tente novamente.')
    } finally {
      setIsLoading(false)
    }
  }, [searchParams])

  // Carregar serviços ao montar componente
  useEffect(() => {
    fetchServices()
  }, [])

  // Debounce para busca
  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current)
    }
    
    searchDebounceRef.current = setTimeout(() => {
      updateURLParams({ search: searchQuery })
    }, 300)
    
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current)
      }
    }
  }, [searchQuery, updateURLParams])

  // Carregar agendamentos quando filtros mudarem
  useEffect(() => {
    fetchAppointments()
  }, [fetchAppointments])

  // Abrir modal de detalhes se appointment_id estiver na URL
  useEffect(() => {
    const appointmentId = searchParams.get('appointment_id')
    if (appointmentId && appointments.length > 0) {
      const appointment = appointments.find(apt => apt.id === appointmentId)
      if (appointment) {
        setSelectedAppointment(appointment)
        setIsModalOpen(true)
        // Remover appointment_id da URL após abrir o modal
        const newParams = new URLSearchParams(searchParams)
        newParams.delete('appointment_id')
        setSearchParams(newParams, { replace: true })
      }
    }
  }, [appointments, searchParams, setSearchParams])

  // Handlers para botões de atalho
  const handleQuickFilter = (days) => {
    setDaysAhead(days)
    setStartDate(null)
    setEndDate(null)
    updateURLParams({ 
      days_ahead: days.toString(),
      start_date: null,
      end_date: null
    })
  }

  const handleToday = () => {
    handleQuickFilter(1)
  }

  const handleNext2Days = () => {
    handleQuickFilter(2)
  }

  const handleNext7Days = () => {
    handleQuickFilter(7)
  }

  const handleCurrentMonth = () => {
    const today = getBrazilianDate()
    const monthStart = startOfMonth(today)
    const monthEnd = endOfMonth(today)
    
    setDaysAhead(null)
    setStartDate(monthStart)
    setEndDate(monthEnd)
    updateURLParams({
      days_ahead: null,
      start_date: formatDateForAPI(monthStart),
      end_date: formatDateForAPI(monthEnd)
    })
  }

  // Handlers para mudanças nos filtros
  const handleSearchChange = (value) => {
    setSearchQuery(value)
  }

  const handleStartDateChange = (date) => {
    setStartDate(date)
    setDaysAhead(null) // Limpar days_ahead quando usar data customizada
    updateURLParams({ 
      start_date: date ? formatDateForAPI(date) : null,
      days_ahead: null
    })
  }

  const handleEndDateChange = (date) => {
    setEndDate(date)
    setDaysAhead(null) // Limpar days_ahead quando usar data customizada
    updateURLParams({ 
      end_date: date ? formatDateForAPI(date) : null,
      days_ahead: null
    })
  }

  const handleStatusFilterChange = (value) => {
    setStatusFilter(value)
    updateURLParams({ status: value || null })
  }

  const handleServiceFilterChange = (value) => {
    setServiceFilter(value)
    updateURLParams({ service_id: value || null })
  }

  // Buscar contagem de agendamentos futuros (notificação discreta)
  useEffect(() => {
    const fetchFutureAppointmentsCount = async () => {
      try {
        const response = await api.get('/api/v1/admin/appointments/count')
        const data = response.data
        setAppointmentsSummary(data)
        setShowAppointmentsSummary((data?.count || 0) > 0)
      } catch (err) {
        console.error('Erro ao buscar contagem de agendamentos futuros:', err)
      }
    }

    fetchFutureAppointmentsCount()
  }, [])

  // Abrir modal de detalhes do agendamento
  const handleAppointmentClick = (appointment) => {
    setSelectedAppointment(appointment)
    setIsModalOpen(true)
  }

  // Fechar modal
  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedAppointment(null)
    setSelectedService(null)
  }

  // Abrir modal de cancelamento
  const handleOpenCancelModal = () => {
    setIsCancelModalOpen(true)
    setCancellationReason('')
  }

  // Fechar modal de cancelamento
  const handleCloseCancelModal = () => {
    setIsCancelModalOpen(false)
    setCancellationReason('')
  }

  // Abrir modal de reagendamento
  const handleOpenRescheduleModal = () => {
    if (!selectedAppointment) return
    setIsRescheduleModalOpen(true)
  }

  const handleCloseRescheduleModal = () => {
    setIsRescheduleModalOpen(false)
  }

  // Cancelar agendamento com motivo
  const handleCancelAppointment = async () => {
    if (!selectedAppointment) return
    
    if (!cancellationReason.trim()) {
      alert('Por favor, informe o motivo do cancelamento.')
      return
    }

    try {
      setIsSubmitting(true)
      await api.post(`/api/v1/admin/appointments/${selectedAppointment.id}/cancel`, {
        cancellation_reason: cancellationReason.trim()
      })
      
      // Recarregar lista
      await fetchAppointments()
      handleCloseCancelModal()
      handleCloseModal()
    } catch (err) {
      console.error('Erro ao cancelar agendamento:', err)
      alert(
        err.response?.data?.detail || 
        'Erro ao cancelar agendamento. Tente novamente.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // Atualizar status do agendamento (para outros status que não cancelamento)
  const handleUpdateStatus = async (newStatus) => {
    if (!selectedAppointment) return
    
    // Se for cancelamento, abrir modal de cancelamento
    if (newStatus === 'CANCELED') {
      handleOpenCancelModal()
      return
    }

    try {
      setIsSubmitting(true)
      await api.put(`/api/v1/admin/appointments/${selectedAppointment.id}`, {
        status: newStatus
      })
      
      // Recarregar lista
      await fetchAppointments()
      handleCloseModal()
    } catch (err) {
      console.error('Erro ao atualizar status:', err)
      alert(
        err.response?.data?.detail || 
        'Erro ao atualizar agendamento. Tente novamente.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // Abrir modal de bloqueio
  const handleOpenBlockModal = () => {
    // Preencher com horário padrão (próxima hora)
    // Usar startDate se disponível, senão usar data atual
    const baseDate = startDate || new Date()
    const now = new Date(baseDate)
    now.setHours(now.getHours() + 1, 0, 0, 0)
    const endTime = new Date(now)
    endTime.setHours(endTime.getHours() + 1)

    setBlockForm({
      start_datetime: format(now, "yyyy-MM-dd'T'HH:mm"),
      end_datetime: format(endTime, "yyyy-MM-dd'T'HH:mm"),
      description: ''
    })
    setIsBlockModalOpen(true)
  }

  // Fechar modal de bloqueio
  const handleCloseBlockModal = () => {
    setIsBlockModalOpen(false)
    setBlockForm({
      start_datetime: '',
      end_datetime: '',
      description: ''
    })
  }

  // Criar bloqueio
  const handleCreateBlock = async (e) => {
    e.preventDefault()

    try {
      setIsSubmitting(true)
      const payload = {
        start_datetime: new Date(blockForm.start_datetime).toISOString(),
        end_datetime: new Date(blockForm.end_datetime).toISOString(),
        description: blockForm.description || null
      }

      await api.post('/api/v1/admin/agenda/blocks', payload)
      
      // Recarregar lista
      await fetchAppointments()
      handleCloseBlockModal()
    } catch (err) {
      console.error('Erro ao criar bloqueio:', err)
      alert(
        err.response?.data?.detail || 
        'Erro ao criar bloqueio. Tente novamente.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // Abrir modal de checkout
  const handleOpenCheckout = async () => {
    if (!selectedAppointment) return
    
    // Buscar serviços do agendamento (múltiplos serviços suportados)
    const serviceIds = selectedAppointment.service_ids || (selectedAppointment.service_id ? [selectedAppointment.service_id] : [])
    
    if (!serviceIds || serviceIds.length === 0) {
      alert('Este agendamento não possui serviço associado.')
      return
    }
    
    try {
      // Buscar todos os serviços do agendamento
      const servicesPromises = serviceIds.map(serviceId => 
        api.get(`/api/v1/admin/services/${serviceId}`).then(res => res.data)
      )
      const servicesArray = await Promise.all(servicesPromises)
      setSelectedService(servicesArray) // Agora é um array
      setIsCheckoutModalOpen(true)
    } catch (err) {
      console.error('Erro ao buscar serviços:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Erro desconhecido'
      alert(`Erro ao carregar dados dos serviços: ${errorMessage}`)
    }
  }

  // Fechar modal de checkout
  const handleCloseCheckout = () => {
    setIsCheckoutModalOpen(false)
    setSelectedService(null)
  }

  // Sucesso na finalização
  const handleFinalizationSuccess = async () => {
    // Recarregar lista de agendamentos
    await fetchAppointments()
    // Fechar modais
    handleCloseCheckout()
    handleCloseModal()
  }

  // Sucesso no reagendamento
  const handleRescheduleSuccess = async () => {
    await fetchAppointments()
    setIsRescheduleModalOpen(false)
    handleCloseModal()
  }

  // Formatar horário para exibição
  const formatTime = (datetimeStr) => {
    const date = new Date(datetimeStr)
    return format(date, 'HH:mm', { locale: ptBR })
  }

  // Formatar data completa
  const formatDateTime = (datetimeStr) => {
    const date = new Date(datetimeStr)
    return format(date, "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
  }

  // Obter cor do status
  const getStatusColor = (status) => {
    switch (status) {
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800'
      case 'CONFIRMED':
        return 'bg-green-100 text-green-800'
      case 'CANCELED':
        return 'bg-red-100 text-red-800'
      case 'COMPLETED':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // Traduzir status
  const translateStatus = (status) => {
    const translations = {
      'PENDING': 'Pendente',
      'CONFIRMED': 'Confirmado',
      'CANCELED': 'Cancelado',
      'COMPLETED': 'Concluído'
    }
    return translations[status] || status
  }

  return (
    <div className="space-y-6">
      {/* Notificação discreta de agendamentos futuros */}
      {appointmentsSummary && showAppointmentsSummary && appointmentsSummary.count > 0 && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg flex items-start justify-between gap-3">
          <div className="flex-1 text-sm">
            <p className="font-semibold">Aviso de agendamentos</p>
            <p className="mt-1">
              Você tem {appointmentsSummary.count}{' '}
              agendamento(s) nos próximos {appointmentsSummary.days}{' '}
              dia(s).
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowAppointmentsSummary(false)}
            className="text-blue-500 hover:text-blue-700 text-sm font-semibold ml-2"
            aria-label="Fechar aviso de agendamentos futuros"
          >
            ×
          </button>
        </div>
      )}

      {/* Cabeçalho */}
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-text">Agenda</h1>
            <p className="text-gray-600 mt-1">
              Gerencie os agendamentos do seu estúdio
            </p>
          </div>
          
          {/* Botão de Ações com Menu */}
          <div className="relative">
            <div className="flex justify-end">
              <Button
                onClick={() => setShowActionMenu(!showActionMenu)}
                variant="primary"
                className="flex items-center gap-2"
              >
                <span className="text-xl">+</span>
                <span className="hidden sm:inline">Nova Ação</span>
              </Button>
            </div>
            
            {/* Menu Dropdown */}
            {showActionMenu && (
              <>
                {/* Overlay para fechar ao clicar fora */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowActionMenu(false)}
                />
                {/*
                  Menu responsivo:
                  - Em mobile: alinhado à direita da tela com margem, abaixo do topo
                  - Em telas maiores: alinhado à direita do botão (dropdown clássico)
                */}
                <div
                  className="fixed sm:absolute z-20 w-56 max-w-[calc(100vw-2rem)] 
                             right-4 top-20
                             sm:right-0 sm:top-auto sm:mt-2
                             bg-white rounded-lg shadow-lg border border-gray-200"
                >
                  <button
                    onClick={() => {
                      setIsManualAppointmentModalOpen(true)
                      setShowActionMenu(false)
                    }}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 rounded-t-lg transition-colors"
                  >
                    <span className="font-semibold text-text">📅 Agendamento Manual</span>
                  </button>
                  <button
                    onClick={() => {
                      handleOpenBlockModal()
                      setShowActionMenu(false)
                    }}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 rounded-b-lg transition-colors"
                  >
                    <span className="font-semibold text-text">⏸️ Registrar Pausa</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
        
        {/* Barra de Ferramentas de Filtros */}
        <Card className="p-4 space-y-4">
          {/* Campo de Busca */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              🔍 Buscar por Cliente
            </label>
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Digite o nome do cliente ou e-mail..."
              className="w-full"
            />
          </div>

          {/* Botões de Atalho (Quick Filters) */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              ⚡ Filtros Rápidos
            </label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant={daysAhead === 1 ? "primary" : "secondary"}
                onClick={handleToday}
                className="text-sm"
              >
                Hoje
              </Button>
              <Button
                type="button"
                variant={daysAhead === 2 ? "primary" : "secondary"}
                onClick={handleNext2Days}
                className="text-sm"
              >
                Próximos 2 dias
              </Button>
              <Button
                type="button"
                variant={daysAhead === 7 ? "primary" : "secondary"}
                onClick={handleNext7Days}
                className="text-sm"
              >
                Próximos 7 dias
              </Button>
              <Button
                type="button"
                variant={!daysAhead && startDate && endDate ? "primary" : "secondary"}
                onClick={handleCurrentMonth}
                className="text-sm"
              >
                Mês Atual
              </Button>
            </div>
          </div>

          {/* Filtro de Período Customizado */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              📅 Período Customizado
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">De</label>
                <DatePicker
                  selected={startDate}
                  onChange={handleStartDateChange}
                  dateFormat="dd/MM/yyyy"
                  locale={ptBR}
                  placeholderText="Data inicial"
                  className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Até</label>
                <DatePicker
                  selected={endDate}
                  onChange={handleEndDateChange}
                  dateFormat="dd/MM/yyyy"
                  locale={ptBR}
                  placeholderText="Data final"
                  minDate={startDate || undefined}
                  className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                />
              </div>
            </div>
          </div>

          {/* Filtros Adicionais */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-gray-200">
            {/* Filtro de Status */}
            <div>
              <label className="block text-sm font-semibold text-text mb-2">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => handleStatusFilterChange(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">Todos os Status</option>
                <option value="SCHEDULED">Agendado</option>
                <option value="CONFIRMED">Confirmado</option>
                <option value="COMPLETED">Concluído</option>
                <option value="CANCELED">Cancelado</option>
              </select>
            </div>
            
            {/* Filtro de Serviço */}
            <div>
              <label className="block text-sm font-semibold text-text mb-2">
                Serviço
              </label>
              <select
                value={serviceFilter}
                onChange={(e) => handleServiceFilterChange(e.target.value)}
                disabled={isLoadingServices}
                className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100"
              >
                <option value="">Todos os Serviços</option>
                {services.map(service => (
                  <option key={service.id} value={service.id}>
                    {service.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Card>
      </div>

      {/* Mensagem de erro */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando agendamentos...</p>
        </div>
      )}

      {/* Lista vazia */}
      {!isLoading && appointments.length === 0 && (
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📅</div>
            <h3 className="text-lg font-semibold text-text mb-2">
              Nenhum agendamento encontrado
            </h3>
            <p className="text-gray-600 mb-6">
              {daysAhead 
                ? `Nos próximos ${daysAhead} dia(s)`
                : startDate && endDate
                  ? `De ${format(startDate, "dd 'de' MMMM 'de' yyyy", { locale: ptBR })} até ${format(endDate, "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}`
                  : startDate
                    ? `A partir de ${format(startDate, "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}`
                    : 'Neste período'
              }
            </p>
            <Button onClick={handleOpenBlockModal} variant="primary">
              Marcar Horário Manualmente
            </Button>
          </div>
        </Card>
      )}

      {/* Lista de Agendamentos */}
      {!isLoading && appointments.length > 0 && (
        <div className="space-y-4">
          {appointments.map((apt) => (
            <Card
              key={apt.id}
              className="cursor-pointer hover:shadow-lg transition-all duration-200"
              onClick={() => handleAppointmentClick(apt)}
              style={{
                borderLeft: apt.service_display_color_code 
                  ? `6px solid ${apt.service_display_color_code}` 
                  : '6px solid #004B6B',
                backgroundColor: apt.service_display_color_code 
                  ? `${apt.service_display_color_code}08` 
                  : undefined
              }}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Data e Horário em Destaque */}
                  <div className="mb-3">
                    {/* Data */}
                    <div className="mb-2">
                      <span className="text-sm font-semibold text-gray-600">
                        {format(new Date(apt.start_datetime), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
                      </span>
                    </div>
                    {/* Horário */}
                    <div className="flex items-baseline gap-2">
                      <span 
                        className="text-3xl sm:text-4xl font-bold"
                        style={{
                          color: apt.service_display_color_code || '#004B6B'
                        }}
                      >
                        {formatTime(apt.start_datetime)}
                      </span>
                      {apt.end_datetime && (
                        <>
                          <span className="text-gray-400 text-lg">-</span>
                          <span 
                            className="text-xl sm:text-2xl font-semibold"
                            style={{
                              color: apt.service_display_color_code || '#004B6B'
                            }}
                          >
                            {formatTime(apt.end_datetime)}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Tipo: Bloqueio ou Agendamento */}
                  {apt.is_manual_block ? (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-base font-bold text-gray-800">
                          🔒 Bloqueio Manual
                        </span>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(apt.status)}`}>
                          {translateStatus(apt.status)}
                        </span>
                      </div>
                      {apt.description && (
                        <p className="text-sm text-gray-700">{apt.description}</p>
                      )}
                    </div>
                  ) : (
                    <div>
                      <h3 className="text-xl font-bold text-text mb-2">
                        {apt.customer_name || 'Cliente não informado'}
                      </h3>
                      <div className="space-y-2 text-sm">
                        {/* Exibir serviços - usar service_names se disponível, senão usar service_name (compatibilidade) */}
                        {(apt.service_names && apt.service_names.length > 0) ? (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-lg">⚙️</span>
                            <div className="flex flex-wrap gap-1">
                              {apt.service_names.map((name, idx) => (
                                <span key={idx} className="font-semibold text-gray-700">
                                  {name}{idx < apt.service_names.length - 1 ? ',' : ''}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : apt.service_name && (
                          <div className="flex items-center gap-2">
                            <span className="text-lg">⚙️</span>
                            <span className="font-semibold text-gray-700">{apt.service_name}</span>
                          </div>
                        )}
                        {apt.customer_phone && (
                          <div className="flex items-center gap-2">
                            <span className="text-lg">📞</span>
                            <span className="text-gray-600">{apt.customer_phone}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2">
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(apt.status)}`}>
                            {translateStatus(apt.status)}
                          </span>
                          {/* Tag visual para agendamentos manuais (não são bloqueios) */}
                          {apt.description === 'Manual' && (
                            <span className="px-2 py-1 rounded-full text-[10px] font-semibold bg-purple-100 text-purple-700 border border-purple-200">
                              Manual
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Indicador visual melhorado */}
                <div className="flex-shrink-0">
                  {apt.status === 'COMPLETED' ? (
                    <span className="text-2xl" title="Pagamento finalizado">✅</span>
                  ) : (
                    <div 
                      className={`w-4 h-4 rounded-full shadow-md ${
                        apt.is_manual_block 
                          ? 'bg-orange-400' 
                          : apt.status === 'CONFIRMED' 
                            ? 'bg-green-400' 
                            : apt.status === 'CANCELED'
                              ? 'bg-red-400'
                              : 'bg-yellow-400'
                      }`}
                      style={{
                        backgroundColor: apt.service_display_color_code && !apt.is_manual_block
                          ? apt.service_display_color_code
                          : undefined
                      }}
                    ></div>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal de Detalhes do Agendamento */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={selectedAppointment?.is_manual_block ? 'Detalhes do Bloqueio' : 'Detalhes do Agendamento'}
      >
        {selectedAppointment && (
          <div className="space-y-4">
            {/* Informações */}
            <div className="space-y-3">
              {selectedAppointment.is_manual_block ? (
                <>
                  <div>
                    <label className="text-sm font-semibold text-gray-600">Descrição</label>
                    <p className="text-text">{selectedAppointment.description || 'Sem descrição'}</p>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-sm font-semibold text-gray-600">Cliente</label>
                    <p className="text-text">{selectedAppointment.customer_name || 'Não informado'}</p>
                  </div>
                  {selectedAppointment.customer_phone && (
                    <div>
                      <label className="text-sm font-semibold text-gray-600">Telefone</label>
                      <p className="text-text">{selectedAppointment.customer_phone}</p>
                    </div>
                  )}
                </>
              )}
              
              {/* Exibir serviços - usar service_names se disponível, senão usar service_name (compatibilidade) */}
              {((selectedAppointment.service_names && selectedAppointment.service_names.length > 0) || selectedAppointment.service_name) && (
                <div>
                  <label className="text-sm font-semibold text-gray-600">Serviço{selectedAppointment.service_names && selectedAppointment.service_names.length > 1 ? 's' : ''}</label>
                  {selectedAppointment.service_names && selectedAppointment.service_names.length > 0 ? (
                    <ul className="text-text list-disc list-inside">
                      {selectedAppointment.service_names.map((name, idx) => (
                        <li key={idx}>{name}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-text">{selectedAppointment.service_name}</p>
                  )}
                </div>
              )}
              
              <div>
                <label className="text-sm font-semibold text-gray-600">Horário</label>
                <p className="text-text">
                  {formatDateTime(selectedAppointment.start_datetime)} - {formatTime(selectedAppointment.end_datetime)}
                </p>
              </div>
              
              <div>
                <label className="text-sm font-semibold text-gray-600">Status</label>
                <p>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(selectedAppointment.status)}`}>
                    {translateStatus(selectedAppointment.status)}
                  </span>
                </p>
              </div>
            </div>

            {/* Ações */}
            {!selectedAppointment.is_manual_block && (
              <div className="space-y-2 pt-4 border-t border-gray-200">
                <p className="text-sm font-semibold text-gray-600 mb-3">Ações:</p>
                
                {selectedAppointment.status !== 'CONFIRMED' && selectedAppointment.status !== 'COMPLETED' && (
                  <Button
                    variant="primary"
                    onClick={() => handleUpdateStatus('CONFIRMED')}
                    disabled={isSubmitting}
                    className="w-full"
                  >
                    {isSubmitting ? 'Confirmando...' : 'Confirmar'}
                  </Button>
                )}
                
                {selectedAppointment.status !== 'CANCELED' && selectedAppointment.status !== 'COMPLETED' && (
                  <Button
                    variant="secondary"
                    onClick={handleOpenCancelModal}
                    disabled={isSubmitting}
                    className="w-full bg-red-500 hover:bg-red-600 text-white"
                  >
                    ❌ Cancelar Agendamento
                  </Button>
                )}

                {/* Editar - disponível para agendamentos não cancelados nem concluídos */}
                {selectedAppointment.status !== 'CANCELED' && selectedAppointment.status !== 'COMPLETED' && (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setEditingAppointment(selectedAppointment)
                      setIsManualAppointmentModalOpen(true)
                      handleCloseModal()
                    }}
                    disabled={isSubmitting}
                    className="w-full"
                  >
                    ✏️ Editar Agendamento
                  </Button>
                )}
                
                {/* Reagendar - disponível para agendamentos não cancelados nem concluídos */}
                {selectedAppointment.status !== 'CANCELED' && selectedAppointment.status !== 'COMPLETED' && (
                  <Button
                    variant="secondary"
                    onClick={handleOpenRescheduleModal}
                    disabled={isSubmitting || !selectedAppointment.service_id}
                    className="w-full"
                  >
                    🔁 Reagendar
                  </Button>
                )}
                
                {(selectedAppointment.status === 'SCHEDULED' || selectedAppointment.status === 'CONFIRMED') && (
                  <Button
                    variant="primary"
                    onClick={handleOpenCheckout}
                    disabled={isSubmitting || !selectedAppointment.service_id}
                    className="w-full"
                  >
                    💰 Finalizar Venda
                  </Button>
                )}
                
                {selectedAppointment.status === 'CONFIRMED' && (
                  <Button
                    variant="secondary"
                    onClick={() => handleUpdateStatus('COMPLETED')}
                    disabled={isSubmitting}
                    className="w-full"
                  >
                    {isSubmitting ? 'Marcando...' : 'Marcar como Concluído'}
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Modal de Criar Bloqueio */}
      <Modal
        isOpen={isBlockModalOpen}
        onClose={handleCloseBlockModal}
        title="Marcar Horário Manualmente"
      >
        <form onSubmit={handleCreateBlock} className="space-y-4">
          {/* Data/Hora Início */}
          <div>
            <label htmlFor="start_datetime" className="block text-sm font-semibold text-text mb-2">
              Data e Hora de Início *
            </label>
            <input
              id="start_datetime"
              type="datetime-local"
              value={blockForm.start_datetime}
              onChange={(e) => setBlockForm({ ...blockForm, start_datetime: e.target.value })}
              required
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              disabled={isSubmitting}
            />
          </div>

          {/* Data/Hora Fim */}
          <div>
            <label htmlFor="end_datetime" className="block text-sm font-semibold text-text mb-2">
              Data e Hora de Fim *
            </label>
            <input
              id="end_datetime"
              type="datetime-local"
              value={blockForm.end_datetime}
              onChange={(e) => setBlockForm({ ...blockForm, end_datetime: e.target.value })}
              required
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              disabled={isSubmitting}
            />
          </div>

          {/* Descrição */}
          <div>
            <label htmlFor="description" className="block text-sm font-semibold text-text mb-2">
              Descrição (opcional)
            </label>
            <textarea
              id="description"
              value={blockForm.description}
              onChange={(e) => setBlockForm({ ...blockForm, description: e.target.value })}
              placeholder="Ex: Almoço, Folga, Manutenção..."
              rows={3}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all resize-none"
              disabled={isSubmitting}
            />
          </div>

          {/* Botões */}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCloseBlockModal}
              disabled={isSubmitting}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? 'Criando...' : 'Criar Bloqueio'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Botão FAB para Criar Bloqueio */}
      <button
        onClick={handleOpenBlockModal}
        className="fixed bottom-24 sm:bottom-8 right-4 sm:right-8 w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 transition-all flex items-center justify-center z-30"
        aria-label="Marcar horário manualmente"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </button>
      
      {/* Modal de Checkout */}
      <CheckoutModal
        isOpen={isCheckoutModalOpen}
        onClose={handleCloseCheckout}
        appointment={selectedAppointment}
        service={selectedService}
        onSuccess={handleFinalizationSuccess}
      />
      
      {/* Modal de Cancelamento */}
      <Modal
        isOpen={isCancelModalOpen}
        onClose={handleCloseCancelModal}
        title="Cancelar Agendamento"
      >
        <div className="space-y-4">
          {selectedAppointment && (
            <>
              <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
                <p className="text-sm font-semibold text-red-800 mb-2">
                  ⚠️ Atenção: Esta ação não pode ser desfeita!
                </p>
                <p className="text-sm text-red-700">
                  O cliente será notificado automaticamente via WhatsApp sobre o cancelamento.
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Informações do Agendamento
                </label>
                <div className="bg-gray-50 p-3 rounded-lg space-y-1 text-sm">
                  <p><span className="font-semibold">Cliente:</span> {selectedAppointment.customer_name || 'Não informado'}</p>
                  {/* Exibir serviços - usar service_names se disponível, senão usar service_name (compatibilidade) */}
                  {((selectedAppointment.service_names && selectedAppointment.service_names.length > 0) || selectedAppointment.service_name) && (
                    <p>
                      <span className="font-semibold">Serviço{selectedAppointment.service_names && selectedAppointment.service_names.length > 1 ? 's' : ''}:</span>{' '}
                      {selectedAppointment.service_names && selectedAppointment.service_names.length > 0 
                        ? selectedAppointment.service_names.join(', ')
                        : selectedAppointment.service_name}
                    </p>
                  )}
                  <p><span className="font-semibold">Horário:</span> {formatDateTime(selectedAppointment.start_datetime)}</p>
                </div>
              </div>
              
              <div>
                <label htmlFor="cancellation_reason" className="block text-sm font-semibold text-text mb-2">
                  Motivo do Cancelamento *
                </label>
                <textarea
                  id="cancellation_reason"
                  value={cancellationReason}
                  onChange={(e) => setCancellationReason(e.target.value)}
                  placeholder="Ex: Cliente solicitou reagendamento, horário indisponível, etc."
                  rows={4}
                  required
                  minLength={3}
                  maxLength={500}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all resize-none"
                  disabled={isSubmitting}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Este motivo será enviado ao cliente via WhatsApp. Mínimo de 3 caracteres.
                </p>
              </div>
              
              <div className="flex gap-3 pt-4">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleCloseCancelModal}
                  disabled={isSubmitting}
                  className="flex-1"
                >
                  Voltar
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  onClick={handleCancelAppointment}
                  disabled={isSubmitting || !cancellationReason.trim() || cancellationReason.trim().length < 3}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white"
                >
                  {isSubmitting ? 'Cancelando...' : 'Confirmar Cancelamento'}
                </Button>
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Modal de Agendamento Manual */}
      <ManualAppointmentModal
        isOpen={isManualAppointmentModalOpen}
        onClose={() => {
          setIsManualAppointmentModalOpen(false)
          setEditingAppointment(null) // Limpar agendamento em edição ao fechar
        }}
        services={services}
        onSuccess={fetchAppointments}
        appointment={editingAppointment} // Passar agendamento para edição
      />

      {/* Modal de Reagendamento */}
      <RescheduleAppointmentModal
        isOpen={isRescheduleModalOpen}
        onClose={handleCloseRescheduleModal}
        services={services}
        appointment={selectedAppointment}
        onSuccess={handleRescheduleSuccess}
      />
    </div>
  )
}

export default AgendaPage

