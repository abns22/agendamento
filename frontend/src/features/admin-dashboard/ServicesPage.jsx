import React, { useState, useEffect } from 'react'
import { api, formatCurrency, formatDuration } from '../../utils/api'
import { Card, Button } from '../../components/ui'
import Modal from '../../components/ui/Modal'

/**
 * Página de Gerenciamento de Serviços (CRUD).
 * 
 * Funcionalidades:
 * - Listar serviços do tenant
 * - Criar novo serviço
 * - Editar serviço existente
 * - Deletar serviço
 * - Design mobile-first
 */
const ServicesPage = () => {
  const [services, setServices] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingService, setEditingService] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Formulário
  const [formData, setFormData] = useState({
    name: '',
    duration_minutes: '',
    price: '',
    is_promotional: false,
    promotion_start_date: '',
    promotion_start_time: '',
    promotion_end_date: '',
    promotion_end_time: '',
    promotional_value: '',
    promotion_display_name: '',
    promotion_description: '',
    promotion_color_code: '#FF0000'
  })

  // Carregar serviços
  useEffect(() => {
    fetchServices()
  }, [])

  const fetchServices = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await api.get('/api/v1/admin/services')
      setServices(response.data)
    } catch (err) {
      console.error('Erro ao carregar serviços:', err)
      setError('Erro ao carregar serviços. Tente novamente.')
    } finally {
      setIsLoading(false)
    }
  }

  // Abrir modal para criar novo serviço
  const handleCreateClick = () => {
    setEditingService(null)
    setFormData({
      name: '',
      duration_minutes: '',
      price: '',
      is_promotional: false,
      promotion_start_date: '',
      promotion_start_time: '',
      promotion_end_date: '',
      promotion_end_time: '',
      promotional_value: '',
      promotion_display_name: '',
      promotion_description: '',
      promotion_color_code: '#FF0000'
    })
    setIsModalOpen(true)
  }

  // Abrir modal para editar serviço
  const handleEditClick = (service) => {
    setEditingService(service)
    
    // Converter datas de promoção para formato de input
    let startDate = ''
    let startTime = ''
    let endDate = ''
    let endTime = ''
    
    if (service.promotion_start_date) {
      const start = new Date(service.promotion_start_date)
      startDate = start.toISOString().split('T')[0]
      startTime = start.toTimeString().slice(0, 5)
    }
    
    if (service.promotion_end_date) {
      const end = new Date(service.promotion_end_date)
      endDate = end.toISOString().split('T')[0]
      endTime = end.toTimeString().slice(0, 5)
    }
    
    setFormData({
      name: service.name,
      duration_minutes: service.duration_minutes.toString(),
      price: service.price.toString(),
      is_promotional: service.is_promotional || false,
      promotion_start_date: startDate,
      promotion_start_time: startTime,
      promotion_end_date: endDate,
      promotion_end_time: endTime,
      promotional_value: service.promotional_value ? service.promotional_value.toString() : '',
      promotion_display_name: service.promotion_display_name || '',
      promotion_description: service.promotion_description || '',
      promotion_color_code: service.promotion_color_code || '#FF0000'
    })
    setIsModalOpen(true)
  }

  // Fechar modal
  const handleCloseModal = () => {
    setIsModalOpen(false)
    setEditingService(null)
    setFormData({
      name: '',
      duration_minutes: '',
      price: '',
      is_promotional: false,
      promotion_start_date: '',
      promotion_start_time: '',
      promotion_end_date: '',
      promotion_end_time: '',
      promotional_value: '',
      promotion_display_name: '',
      promotion_description: '',
      promotion_color_code: '#FF0000'
    })
  }

  // Submeter formulário (criar ou editar)
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Validação básica
    if (!formData.name.trim()) {
      setError('Nome do serviço é obrigatório')
      return
    }
    
    if (!formData.duration_minutes || parseInt(formData.duration_minutes) <= 0) {
      setError('Duração deve ser maior que zero')
      return
    }
    
    if (!formData.price || parseFloat(formData.price) < 0) {
      setError('Preço deve ser maior ou igual a zero')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      const payload = {
        name: formData.name.trim(),
        duration_minutes: parseInt(formData.duration_minutes),
        price: parseFloat(formData.price),
        is_promotional: formData.is_promotional
      }
      
      // Adicionar campos de promoção se is_promotional for true
      if (formData.is_promotional) {
        // Validar campos de promoção
        if (!formData.promotion_start_date || !formData.promotion_start_time) {
          setError('Data e hora de início da promoção são obrigatórias')
          return
        }
        if (!formData.promotion_end_date || !formData.promotion_end_time) {
          setError('Data e hora de fim da promoção são obrigatórias')
          return
        }
        if (!formData.promotional_value || parseFloat(formData.promotional_value) < 0) {
          setError('Valor promocional deve ser maior ou igual a zero')
          return
        }
        
        // Combinar data e hora para criar datetime
        // IMPORTANTE: O horário informado pelo usuário deve ser salvo exatamente como informado (sem conversão de timezone)
        // Para isso, criamos a data como se fosse UTC desde o início, adicionando 'Z' ao final
        // Isso evita que o JavaScript converta o horário local para UTC (que adicionaria +3 horas no Brasil)
        const startDateTimeStr = `${formData.promotion_start_date}T${formData.promotion_start_time}:00Z`
        const endDateTimeStr = `${formData.promotion_end_date}T${formData.promotion_end_time}:00Z`
        
        const startDateTime = new Date(startDateTimeStr)
        const endDateTime = new Date(endDateTimeStr)
        
        // Validar que data de fim é posterior à data de início
        if (endDateTime <= startDateTime) {
          setError('Data de fim deve ser posterior à data de início')
          return
        }
        
        // Enviar como ISO string (já em UTC, sem conversão adicional)
        payload.promotion_start_date = startDateTime.toISOString()
        payload.promotion_end_date = endDateTime.toISOString()
        payload.promotional_value = parseFloat(formData.promotional_value)
        payload.promotion_display_name = formData.promotion_display_name.trim() || null
        payload.promotion_description = formData.promotion_description.trim() || null
        payload.promotion_color_code = formData.promotion_color_code || null
      } else {
        // Se não for promocional, limpar campos
        payload.promotion_start_date = null
        payload.promotion_end_date = null
        payload.promotional_value = null
        payload.promotion_display_name = null
        payload.promotion_description = null
        payload.promotion_color_code = null
      }

      if (editingService) {
        // Atualizar serviço existente
        await api.put(`/api/v1/admin/services/${editingService.id}`, payload)
      } else {
        // Criar novo serviço
        await api.post('/api/v1/admin/services', payload)
      }

      // Recarregar lista
      await fetchServices()
      
      // Fechar modal
      handleCloseModal()
    } catch (err) {
      console.error('Erro ao salvar serviço:', err)
      setError(
        err.response?.data?.detail || 
        'Erro ao salvar serviço. Tente novamente.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // Deletar serviço
  const handleDelete = async (serviceId) => {
    if (!window.confirm('Tem certeza que deseja excluir este serviço?')) {
      return
    }

    try {
      await api.delete(`/api/v1/admin/services/${serviceId}`)
      // Recarregar lista
      await fetchServices()
    } catch (err) {
      console.error('Erro ao deletar serviço:', err)
      alert(
        err.response?.data?.detail || 
        'Erro ao deletar serviço. Tente novamente.'
      )
    }
  }

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Serviços</h1>
          <p className="text-gray-600 mt-1">
            Gerencie os serviços oferecidos pelo seu estúdio
          </p>
        </div>
      </div>

      {/* Mensagem de erro global */}
      {error && !isModalOpen && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando serviços...</p>
        </div>
      )}

      {/* Lista vazia */}
      {!isLoading && services.length === 0 && (
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">⚙️</div>
            <h3 className="text-lg font-semibold text-text mb-2">
              Nenhum serviço cadastrado
            </h3>
            <p className="text-gray-600 mb-6">
              Comece criando seu primeiro serviço
            </p>
            <Button onClick={handleCreateClick} variant="primary">
              Criar Primeiro Serviço
            </Button>
          </div>
        </Card>
      )}

      {/* Lista de serviços */}
      {!isLoading && services.length > 0 && (
        <div className="space-y-4">
          {services.map((service) => (
            <Card key={service.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-lg font-semibold text-text">
                      {service.name}
                    </h3>
                    {service.is_promotional && (
                      <span
                        className="px-2 py-1 text-xs font-bold text-white rounded-full"
                        style={{
                          backgroundColor: service.promotion_color_code || '#FF0000'
                        }}
                      >
                        🎯 PROMOÇÃO
                      </span>
                    )}
                  </div>
                  <div className="space-y-1 text-sm text-gray-600">
                    <div className="flex items-center">
                      <span className="font-medium mr-2">⏱️ Duração:</span>
                      <span>{formatDuration(service.duration_minutes)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium mr-2">💰 Preço:</span>
                      {service.is_promotional && service.promotional_value ? (
                        <>
                          <span className="line-through text-gray-400">
                            {formatCurrency(parseFloat(service.price))}
                          </span>
                          <span
                            className="font-semibold"
                            style={{
                              color: service.promotion_color_code || '#FF0000'
                            }}
                          >
                            {formatCurrency(parseFloat(service.promotional_value))}
                          </span>
                        </>
                      ) : (
                        <span className="text-primary font-semibold">
                          {formatCurrency(parseFloat(service.price))}
                        </span>
                      )}
                    </div>
                    {service.is_promotional && service.promotion_display_name && (
                      <div className="flex items-center">
                        <span className="text-xs font-medium text-gray-500">
                          📢 {service.promotion_display_name}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Botões de ação */}
                <div className="flex flex-col gap-2 ml-4">
                  <button
                    onClick={() => handleEditClick(service)}
                    className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-opacity-90 transition-colors"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => handleDelete(service.id)}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition-colors"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal de Criar/Editar */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={editingService ? 'Editar Serviço' : 'Novo Serviço'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Mensagem de erro no modal */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Campo Nome */}
          <div>
            <label htmlFor="name" className="block text-sm font-semibold text-text mb-2">
              Nome do Serviço *
            </label>
            <input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ex: Corte de Cabelo"
              required
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              disabled={isSubmitting}
            />
          </div>

          {/* Campo Duração */}
          <div>
            <label htmlFor="duration" className="block text-sm font-semibold text-text mb-2">
              Duração (minutos) *
            </label>
            <input
              id="duration"
              type="number"
              min="1"
              max="480"
              value={formData.duration_minutes}
              onChange={(e) => setFormData({ ...formData, duration_minutes: e.target.value })}
              placeholder="Ex: 45"
              required
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              Duração em minutos (máximo 8 horas = 480 minutos)
            </p>
          </div>

          {/* Campo Preço */}
          <div>
            <label htmlFor="price" className="block text-sm font-semibold text-text mb-2">
              Preço (R$) *
            </label>
            <input
              id="price"
              type="number"
              min="0"
              step="0.01"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: e.target.value })}
              placeholder="Ex: 50.00"
              required
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              disabled={isSubmitting}
            />
          </div>

          {/* Seção de Promoção */}
          <div className="border-t pt-4 mt-4">
            <div className="flex items-center mb-4">
              <input
                id="is_promotional"
                type="checkbox"
                checked={formData.is_promotional}
                onChange={(e) => setFormData({ ...formData, is_promotional: e.target.checked })}
                className="w-5 h-5 text-primary border-gray-300 rounded focus:ring-primary focus:ring-2"
                disabled={isSubmitting}
              />
              <label htmlFor="is_promotional" className="ml-2 text-sm font-semibold text-text cursor-pointer">
                🎯 Este serviço está em promoção
              </label>
            </div>

            {/* Campos de Promoção (exibidos apenas se is_promotional for true) */}
            {formData.is_promotional && (
              <div className="space-y-4 bg-yellow-50 p-4 rounded-lg border-2 border-yellow-200">
                <h4 className="text-sm font-bold text-text mb-3">📢 Informações da Promoção</h4>

                {/* Data e Hora de Início */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="promotion_start_date" className="block text-xs font-semibold text-text mb-1">
                      Data de Início *
                    </label>
                    <input
                      id="promotion_start_date"
                      type="date"
                      value={formData.promotion_start_date}
                      onChange={(e) => setFormData({ ...formData, promotion_start_date: e.target.value })}
                      required={formData.is_promotional}
                      className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                      disabled={isSubmitting}
                    />
                  </div>
                  <div>
                    <label htmlFor="promotion_start_time" className="block text-xs font-semibold text-text mb-1">
                      Hora de Início *
                    </label>
                    <input
                      id="promotion_start_time"
                      type="time"
                      value={formData.promotion_start_time}
                      onChange={(e) => setFormData({ ...formData, promotion_start_time: e.target.value })}
                      required={formData.is_promotional}
                      className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                      disabled={isSubmitting}
                    />
                  </div>
                </div>

                {/* Data e Hora de Fim */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="promotion_end_date" className="block text-xs font-semibold text-text mb-1">
                      Data de Fim *
                    </label>
                    <input
                      id="promotion_end_date"
                      type="date"
                      value={formData.promotion_end_date}
                      onChange={(e) => setFormData({ ...formData, promotion_end_date: e.target.value })}
                      required={formData.is_promotional}
                      className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                      disabled={isSubmitting}
                    />
                  </div>
                  <div>
                    <label htmlFor="promotion_end_time" className="block text-xs font-semibold text-text mb-1">
                      Hora de Fim *
                    </label>
                    <input
                      id="promotion_end_time"
                      type="time"
                      value={formData.promotion_end_time}
                      onChange={(e) => setFormData({ ...formData, promotion_end_time: e.target.value })}
                      required={formData.is_promotional}
                      className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                      disabled={isSubmitting}
                    />
                  </div>
                </div>

                {/* Valor Promocional */}
                <div>
                  <label htmlFor="promotional_value" className="block text-xs font-semibold text-text mb-1">
                    Valor Promocional (R$) *
                  </label>
                  <input
                    id="promotional_value"
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.promotional_value}
                    onChange={(e) => setFormData({ ...formData, promotional_value: e.target.value })}
                    placeholder="Ex: 35.00"
                    required={formData.is_promotional}
                    className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Preço que será cobrado durante a promoção
                  </p>
                </div>

                {/* Nome da Promoção */}
                <div>
                  <label htmlFor="promotion_display_name" className="block text-xs font-semibold text-text mb-1">
                    Nome da Promoção
                  </label>
                  <input
                    id="promotion_display_name"
                    type="text"
                    value={formData.promotion_display_name}
                    onChange={(e) => setFormData({ ...formData, promotion_display_name: e.target.value })}
                    placeholder="Ex: Promoção de Natal"
                    maxLength={200}
                    className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                    disabled={isSubmitting}
                  />
                </div>

                {/* Descrição da Promoção */}
                <div>
                  <label htmlFor="promotion_description" className="block text-xs font-semibold text-text mb-1">
                    Descrição da Promoção
                  </label>
                  <textarea
                    id="promotion_description"
                    value={formData.promotion_description}
                    onChange={(e) => setFormData({ ...formData, promotion_description: e.target.value })}
                    placeholder="Ex: Aproveite nossa promoção especial de fim de ano!"
                    rows={3}
                    className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm resize-none"
                    disabled={isSubmitting}
                  />
                </div>

                {/* Cor da Promoção */}
                <div>
                  <label htmlFor="promotion_color_code" className="block text-xs font-semibold text-text mb-1">
                    Cor da Promoção
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      id="promotion_color_code"
                      type="color"
                      value={formData.promotion_color_code}
                      onChange={(e) => setFormData({ ...formData, promotion_color_code: e.target.value })}
                      className="w-16 h-10 rounded-lg border-2 border-gray-300 cursor-pointer"
                      disabled={isSubmitting}
                    />
                    <input
                      type="text"
                      value={formData.promotion_color_code}
                      onChange={(e) => setFormData({ ...formData, promotion_color_code: e.target.value })}
                      placeholder="#FF0000"
                      maxLength={7}
                      pattern="^#[0-9A-Fa-f]{6}$"
                      className="flex-1 px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm font-mono"
                      disabled={isSubmitting}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Cor para destacar a promoção na interface
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Botões */}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCloseModal}
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
              {isSubmitting ? 'Salvando...' : editingService ? 'Atualizar' : 'Criar'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Floating Action Button (FAB) */}
      <button
        onClick={handleCreateClick}
        className="fixed bottom-24 sm:bottom-8 right-4 sm:right-8 w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 transition-all flex items-center justify-center z-30"
        aria-label="Criar novo serviço"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>
  )
}

export default ServicesPage

