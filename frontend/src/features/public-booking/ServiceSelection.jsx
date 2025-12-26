import React, { useEffect, useState } from 'react'
import { useServices } from '../../hooks/usePublicBooking'
import { formatCurrency, formatDuration } from '../../utils/api'
import { Modal } from '../../components/ui'

/**
 * Componente para seleção de serviços (múltipla seleção).
 * 
 * Exibe uma lista de serviços disponíveis em cards com checkboxes,
 * permitindo selecionar múltiplos serviços para o agendamento.
 */
const ServiceSelection = ({ tenantSlug, onSelectServices, selectedServices = [] }) => {
  const { services, loading, error, fetchServices } = useServices(tenantSlug)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedServiceForModal, setSelectedServiceForModal] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  
  // Filtrar serviços baseado no termo de busca
  const filteredServices = services.filter(service => {
    const searchLower = searchTerm.toLowerCase()
    return (
      service.name.toLowerCase().includes(searchLower) ||
      (service.long_description && service.long_description.toLowerCase().includes(searchLower))
    )
  })

  useEffect(() => {
    if (tenantSlug) {
      console.log('🔍 ServiceSelection: Buscando serviços para tenantSlug:', tenantSlug)
      fetchServices()
    } else {
      console.warn('⚠️ ServiceSelection: tenantSlug não fornecido')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantSlug]) // fetchServices é estável, não precisa estar nas dependências

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (error) {
    // Verificar se é erro 404 (tenant não encontrado)
    const isNotFound = error.toLowerCase().includes('não encontrado') || 
                       error.toLowerCase().includes('not found') ||
                       error.toLowerCase().includes('404')
    
    return (
      <div className="p-6">
        <div className={`border rounded-lg p-4 ${
          isNotFound 
            ? 'bg-red-50 border-red-200' 
            : 'bg-yellow-50 border-yellow-200'
        }`}>
          <div className="flex items-start">
            <svg 
              className={`w-5 h-5 mr-3 mt-0.5 ${
                isNotFound ? 'text-red-600' : 'text-yellow-600'
              }`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className={`text-sm font-semibold mb-1 ${
                isNotFound ? 'text-red-800' : 'text-yellow-800'
              }`}>
                {isNotFound ? 'Estúdio não encontrado' : 'Erro ao carregar serviços'}
              </p>
              <p className={`text-sm ${
                isNotFound ? 'text-red-700' : 'text-yellow-700'
              }`}>
                {error}
              </p>
              {isNotFound && (
                <p className="text-xs text-red-600 mt-2">
                  Verifique se o link de agendamento está correto.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (services.length === 0) {
    return (
      <div className="p-6">
        <p className="text-gray-500 text-center">Nenhum serviço disponível no momento.</p>
      </div>
    )
  }

  const handleServiceToggle = (service) => {
    // Se o serviço tem long_description, mostrar modal primeiro (para ler descrição)
    if (service.long_description && !selectedServices.find(s => s.id === service.id)) {
      setSelectedServiceForModal(service)
      setIsModalOpen(true)
      return
    }
    
    // Toggle do serviço na lista
    const serviceId = service.id
    const isSelected = selectedServices.find(s => s.id === serviceId)
    
    let newSelected
    if (isSelected) {
      // Remover da seleção
      newSelected = selectedServices.filter(s => s.id !== serviceId)
    } else {
      // Adicionar à seleção
      newSelected = [...selectedServices, service]
    }
    
    onSelectServices(newSelected)
  }
  
  const handleConfirmSelection = () => {
    if (selectedServiceForModal) {
      const serviceId = selectedServiceForModal.id
      const isSelected = selectedServices.find(s => s.id === serviceId)
      
      if (!isSelected) {
        const newSelected = [...selectedServices, selectedServiceForModal]
        onSelectServices(newSelected)
      }
      
      setIsModalOpen(false)
      setSelectedServiceForModal(null)
    }
  }
  
  const isServiceSelected = (serviceId) => {
    return selectedServices.some(s => s.id === serviceId)
  }
  
  // Calcular duração total e valor total
  const totalDuration = selectedServices.reduce((sum, s) => sum + (s.duration_minutes || 0), 0)
  const totalValue = selectedServices.reduce((sum, s) => {
    const isPromo = s.promotion_active && s.is_promotional && s.promotional_value
    return sum + parseFloat(isPromo ? s.promotional_value : s.price)
  }, 0)
  
  return (
    <div className="relative pb-24">
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-text">Selecione os serviços</h2>
          {selectedServices.length > 0 && (
            <span className="text-sm text-primary font-semibold">
              {selectedServices.length} selecionado{selectedServices.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      
      {/* Campo de busca */}
      <div className="relative">
        <input
          type="text"
          placeholder="Buscar serviço..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-3 pl-10 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
        />
        <svg 
          className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      
      {/* Mensagem quando não há resultados */}
      {searchTerm && filteredServices.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>Nenhum serviço encontrado para "{searchTerm}"</p>
        </div>
      )}
      
      <div className="space-y-3">
        {filteredServices.map((service) => {
          const isPromotionActive = service.promotion_active && service.is_promotional
          const effectivePrice = isPromotionActive && service.promotional_value 
            ? parseFloat(service.promotional_value) 
            : parseFloat(service.price)
          const originalPrice = parseFloat(service.price)
          const borderColor = isPromotionActive && service.promotion_color_code 
            ? service.promotion_color_code 
            : null
          
          const isSelected = isServiceSelected(service.id)
          
          return (
          <div
            key={service.id}
            onClick={() => handleServiceToggle(service)}
            className={`w-full text-left p-5 rounded-xl border-2 transition-all duration-200 relative cursor-pointer ${
              isSelected
                ? 'bg-primary bg-opacity-5 shadow-md border-primary'
                : 'bg-white hover:shadow-sm hover:border-gray-400'
            }`}
            style={{
              borderColor: isSelected 
                ? undefined 
                : (borderColor || '#e5e7eb')
            }}
          >
            {/* Badge de Promoção */}
            {isPromotionActive && service.promotion_display_name && !isSelected && (
              <div 
                className="absolute top-3 right-12 px-3 py-1 rounded-full text-xs font-bold text-white shadow-md z-10"
                style={{ backgroundColor: borderColor || '#FF0000' }}
              >
                {service.promotion_display_name}
              </div>
            )}
            
            <div className="flex items-start justify-between gap-3">
              {/* Checkbox */}
              <div className="flex-shrink-0 mt-1">
                <div className={`w-6 h-6 rounded border-2 flex items-center justify-center transition-all ${
                  isSelected
                    ? 'bg-primary border-primary'
                    : 'border-gray-300 bg-white'
                }`}>
                  {isSelected && (
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
              </div>
              
              {/* Conteúdo do serviço */}
              <div className="flex-1 min-w-0">
                <h3 className={`text-lg font-semibold mb-2 ${
                  isSelected ? 'text-primary' : 'text-text'
                }`}>
                  {service.name}
                </h3>
                <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {formatDuration(service.duration_minutes)}
                  </span>
                  <div className="flex items-center gap-2">
                    {isPromotionActive && originalPrice > effectivePrice && (
                      <span className="text-gray-400 line-through text-sm">
                        {formatCurrency(originalPrice)}
                      </span>
                    )}
                    <span 
                      className={`font-bold ${
                        isPromotionActive ? 'text-red-600 text-base' : 'text-primary'
                      }`}
                    >
                      {formatCurrency(effectivePrice)}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Indicador de selecionado (ícone de check adicional) */}
              {isSelected && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                </div>
              )}
            </div>
          </div>
        )})}
      </div>
      
      {/* Barra Fixa no Rodapé com Resumo (Sticky) */}
      {selectedServices.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t-2 border-primary shadow-lg z-50 p-4">
          <div className="max-w-md mx-auto">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-4 text-sm">
                <span className="font-semibold text-text">
                  Total: <span className="text-primary">{selectedServices.length}</span> serviço{selectedServices.length > 1 ? 's' : ''}
                </span>
                <span className="font-semibold text-text">
                  Tempo: <span className="text-primary">{formatDuration(totalDuration)}</span>
                </span>
              </div>
              <span className="text-xl font-bold text-primary">
                {formatCurrency(totalValue)}
              </span>
            </div>
            
            {/* Lista de serviços selecionados com opção de remover */}
            <div className="flex flex-wrap gap-2 mt-2 max-h-20 overflow-y-auto">
              {selectedServices.map((service) => (
                <div
                  key={service.id}
                  className="flex items-center gap-1 bg-primary/10 text-primary px-2 py-1 rounded-full text-xs font-semibold"
                >
                  <span>{service.name}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleServiceToggle(service)
                    }}
                    className="ml-1 hover:bg-primary/20 rounded-full p-0.5 transition-colors"
                    aria-label={`Remover ${service.name}`}
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* Modal com descrição detalhada */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedServiceForModal(null)
        }}
        title={selectedServiceForModal?.name || 'Detalhes do Serviço'}
      >
        {selectedServiceForModal && (
          <div className="space-y-4">
            {selectedServiceForModal.long_description ? (
              <div>
                <h3 className="font-semibold text-text mb-2">Descrição</h3>
                <p className="text-gray-700 whitespace-pre-line">
                  {selectedServiceForModal.long_description}
                </p>
              </div>
            ) : (
              <p className="text-gray-500">Nenhuma descrição detalhada disponível.</p>
            )}
            
            <div className="flex items-center gap-4 text-sm text-gray-600 pt-4 border-t">
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {formatDuration(selectedServiceForModal.duration_minutes)}
              </span>
              <span className="font-semibold text-primary">
                {formatCurrency(parseFloat(selectedServiceForModal.price))}
              </span>
            </div>
            
            <div className="flex gap-2 pt-4">
              <button
                onClick={handleConfirmSelection}
                className="flex-1 bg-primary text-white py-3 rounded-lg font-semibold hover:bg-primary-dark transition-colors"
              >
                Selecionar este serviço
              </button>
              <button
                onClick={() => {
                  setIsModalOpen(false)
                  setSelectedServiceForModal(null)
                }}
                className="px-4 py-3 border-2 border-gray-300 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </Modal>
      </div>
    </div>
  )
}

export default ServiceSelection

