import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { api } from '../../utils/api'
import ServiceSelection from './ServiceSelection'
import TimeSlotPicker from './TimeSlotPicker'
import BookingForm from './BookingForm'

/**
 * Componente principal que gerencia o fluxo de agendamento (Wizard).
 * 
 * Apresenta os componentes em sequência linear sem recarregar a página,
 * simulando uma experiência de app mobile.
 */
const BookingWizard = () => {
  const { tenantSlug } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [step, setStep] = useState(1) // 1: Serviço, 2: Data/Hora, 3: Formulário
  const [selectedService, setSelectedService] = useState(null)
  const [selectedDate, setSelectedDate] = useState(null)
  const [selectedTime, setSelectedTime] = useState(null)
  const [selectedDateTime, setSelectedDateTime] = useState(null)
  const [appointmentCreated, setAppointmentCreated] = useState(false)
  const [tenantError, setTenantError] = useState(null)
  const [tenantData, setTenantData] = useState(null)
  const [isLoadingTenant, setIsLoadingTenant] = useState(true)
  const hasRedirected = useRef(false)

  // Redirecionar /book/:tenantSlug para /booking/:tenantSlug (compatibilidade)
  useEffect(() => {
    if (
      location.pathname.startsWith('/book/') && 
      tenantSlug && 
      !location.pathname.startsWith('/booking/') &&
      !hasRedirected.current
    ) {
      console.log('🔄 BookingWizard: Redirecionando /book/ para /booking/', tenantSlug)
      hasRedirected.current = true
      navigate(`/booking/${tenantSlug}`, { replace: true })
    }
  }, [location.pathname, tenantSlug, navigate])

  // Validar tenantSlug e buscar dados do tenant
  useEffect(() => {
    if (tenantSlug) {
      // Validar formato básico do slug (apenas letras minúsculas, números e hífens)
      const slugPattern = /^[a-z0-9-]+$/
      if (!slugPattern.test(tenantSlug)) {
        setTenantError('Slug do estúdio inválido. Use apenas letras minúsculas, números e hífens.')
        setIsLoadingTenant(false)
      } else {
        setTenantError(null)
        // Buscar dados públicos do tenant
        const fetchTenantData = async () => {
          try {
            setIsLoadingTenant(true)
            const response = await api.get(`/api/v1/public/tenant/${tenantSlug}`)
            setTenantData(response.data)
            console.log('✅ Dados do tenant carregados:', response.data)
          } catch (err) {
            console.error('Erro ao buscar dados do tenant:', err)
            if (err.response?.status === 404) {
              setTenantError(`Estúdio '${tenantSlug}' não encontrado ou inativo.`)
            } else {
              setTenantError('Erro ao carregar informações do estúdio.')
            }
          } finally {
            setIsLoadingTenant(false)
          }
        }
        fetchTenantData()
      }
    }
  }, [tenantSlug])

  // Avançar para seleção de data/hora
  const handleServiceSelect = (service) => {
    setSelectedService(service)
    setStep(2)
  }

  // Avançar para formulário
  const handleDateTimeSelect = (date, time) => {
    setSelectedDate(date)
    setSelectedTime(time)
    
    if (date && time) {
      const [hours, minutes] = time.split(':')
      // IMPORTANTE: Os horários do backend são timezone-naive (sem timezone)
      // Quando o usuário seleciona "10:30", ele está selecionando o horário local
      // Criar datetime no horário local (não UTC) para manter consistência
      const year = date.getFullYear()
      const month = date.getMonth()
      const day = date.getDate()
      const dateTime = new Date(year, month, day, parseInt(hours), parseInt(minutes), 0, 0)
      setSelectedDateTime(dateTime)
      setStep(3)
    }
  }

  // Voltar para seleção de data/hora
  const handleBackToTime = () => {
    setStep(2)
  }

  // Voltar para seleção de serviço
  const handleBackToService = () => {
    setStep(1)
    setSelectedService(null)
    setSelectedDate(null)
    setSelectedTime(null)
    setSelectedDateTime(null)
  }

  // Sucesso no agendamento
  const handleSuccess = () => {
    setAppointmentCreated(true)
  }

  // Resetar para novo agendamento
  const handleNewBooking = () => {
    setStep(1)
    setSelectedService(null)
    setSelectedDate(null)
    setSelectedTime(null)
    setSelectedDateTime(null)
    setAppointmentCreated(false)
  }

  // Validação de tenantSlug
  if (!tenantSlug) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md w-full">
          <div className="flex items-center mb-4">
            <svg className="w-8 h-8 text-red-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-xl font-bold text-red-800">Estúdio não encontrado</h2>
          </div>
          <p className="text-red-700 mb-4">
            O link de agendamento está incompleto. Verifique se você acessou o link correto.
          </p>
          <button
            onClick={() => navigate('/')}
            className="btn-primary w-full"
          >
            Voltar para a página inicial
          </button>
        </div>
      </div>
    )
  }

  // Erro de validação do slug
  if (tenantError) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md w-full">
          <div className="flex items-center mb-4">
            <svg className="w-8 h-8 text-red-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-xl font-bold text-red-800">Link inválido</h2>
          </div>
          <p className="text-red-700 mb-4">{tenantError}</p>
          <button
            onClick={() => navigate('/')}
            className="btn-primary w-full"
          >
            Voltar para a página inicial
          </button>
        </div>
      </div>
    )
  }

  // Tela de sucesso
  if (appointmentCreated) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
        <div className="w-20 h-20 rounded-full bg-success flex items-center justify-center mb-6">
          <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-text mb-4 text-center">
          Agendamento Confirmado!
        </h2>
        <p className="text-gray-600 text-center mb-6">
          Enviamos a confirmação para seu WhatsApp.
        </p>
        <button
          onClick={handleNewBooking}
          className="btn-primary"
        >
          Fazer Novo Agendamento
        </button>
      </div>
    )
  }

  // Mostrar loading enquanto busca dados do tenant
  if (isLoadingTenant) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-text">Carregando informações do estúdio...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      {/* Cabeçalho com informações do tenant */}
      {tenantData && (
        <div className="bg-white border-b border-gray-200 px-4 py-6">
          <div className="max-w-md mx-auto">
            {/* Logo */}
            {tenantData.logo_url && (
              <div className="flex justify-center mb-4">
                <img 
                  src={
                    tenantData.logo_url.startsWith('http') 
                      ? tenantData.logo_url 
                      : tenantData.logo_url.startsWith('/api/v1/')
                        ? `${api.defaults.baseURL}${tenantData.logo_url}`
                        : `${api.defaults.baseURL}/api/v1${tenantData.logo_url}`
                  }
                  alt={tenantData.name || tenantData.slug}
                  className="h-24 w-auto object-contain rounded-lg transition-transform duration-300 hover:scale-105"
                  onError={(e) => {
                    console.error('Erro ao carregar logo:', tenantData.logo_url)
                    e.target.style.display = 'none'
                  }}
                />
              </div>
            )}
            
            {/* Nome do Estúdio */}
            <h1 className="text-2xl font-bold text-text text-center mb-2">
              {tenantData.name || tenantData.slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </h1>
            
            {/* Descrição */}
            {tenantData.description && (
              <p className="text-sm text-gray-600 text-center mb-3 leading-relaxed">
                {tenantData.description}
              </p>
            )}
            
            {/* Informações Adicionais */}
            <div className="space-y-2">
              {/* Horário de Funcionamento */}
              {tenantData.schedule_display_text && (
                <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{tenantData.schedule_display_text}</span>
                </div>
              )}
              
              {/* Endereço */}
              {tenantData.address && (
                <div className="flex items-start justify-center gap-2 text-xs text-gray-500">
                  <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="text-center">{tenantData.address}</span>
                </div>
              )}
              
              {/* Telefone de Contato */}
              {tenantData.phone_contact && (
                <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  <a 
                    href={`tel:${tenantData.phone_contact.replace(/\D/g, '')}`}
                    className="text-primary hover:text-primary-dark transition-colors"
                  >
                    {(() => {
                      const digits = tenantData.phone_contact.replace(/\D/g, '')
                      if (digits.length === 11 && digits.startsWith('55')) {
                        // Formato: 55 (11) 99999-9999
                        return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 9)}-${digits.slice(9)}`
                      } else if (digits.length === 11) {
                        // Formato: (11) 99999-9999
                        return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
                      } else if (digits.length === 10) {
                        // Formato: (11) 9999-9999
                        return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`
                      }
                      return tenantData.phone_contact
                    })()}
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Indicador de progresso */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between max-w-md mx-auto">
          <div className={`flex items-center ${step >= 1 ? 'text-primary' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 1 ? 'bg-primary text-white' : 'bg-gray-200 text-gray-400'
            }`}>
              {step > 1 ? '✓' : '1'}
            </div>
            <span className="ml-2 text-xs font-medium hidden sm:inline">Serviço</span>
          </div>
          <div className={`flex-1 h-1 mx-2 ${step >= 2 ? 'bg-primary' : 'bg-gray-200'}`}></div>
          <div className={`flex items-center ${step >= 2 ? 'text-primary' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 2 ? 'bg-primary text-white' : 'bg-gray-200 text-gray-400'
            }`}>
              {step > 2 ? '✓' : '2'}
            </div>
            <span className="ml-2 text-xs font-medium hidden sm:inline">Horário</span>
          </div>
          <div className={`flex-1 h-1 mx-2 ${step >= 3 ? 'bg-primary' : 'bg-gray-200'}`}></div>
          <div className={`flex items-center ${step >= 3 ? 'text-primary' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 3 ? 'bg-primary text-white' : 'bg-gray-200 text-gray-400'
            }`}>
              3
            </div>
            <span className="ml-2 text-xs font-medium hidden sm:inline">Dados</span>
          </div>
        </div>
      </div>

      {/* Conteúdo do wizard */}
      <div className="pb-6">
        {step === 1 && (
          <ServiceSelection
            tenantSlug={tenantSlug}
            onSelectService={handleServiceSelect}
            selectedService={selectedService}
          />
        )}

        {step === 2 && (
          <div>
            <button
              onClick={handleBackToService}
              className="p-4 flex items-center text-primary hover:text-primary-dark"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Voltar
            </button>
            <TimeSlotPicker
              tenantSlug={tenantSlug}
              serviceId={selectedService?.id ? String(selectedService.id) : null}
              onSelectDateTime={handleDateTimeSelect}
              selectedDate={selectedDate}
              selectedTime={selectedTime}
            />
          </div>
        )}

        {step === 3 && (
          <div>
            <button
              onClick={handleBackToTime}
              className="p-4 flex items-center text-primary hover:text-primary-dark"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Voltar
            </button>
            <BookingForm
              tenantSlug={tenantSlug}
              serviceId={selectedService?.id}
              selectedDateTime={selectedDateTime}
              onSuccess={handleSuccess}
              onBack={handleBackToTime}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default BookingWizard

