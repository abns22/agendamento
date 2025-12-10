import React, { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { Button, Input } from '../../components/ui'

/**
 * Seção de Configuração de Intervalos de Parada/Almoço.
 * 
 * Permite ao administrador configurar intervalos de tempo de parada
 * para cada dia da semana (ex: Almoço das 12:00 às 13:00).
 */
const StopTimesSection = () => {
  const [stopTimes, setStopTimes] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  
  // Estado do formulário de novo StopTime
  const [isAdding, setIsAdding] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [selectedDays, setSelectedDays] = useState([]) // Array de dias selecionados
  const [formData, setFormData] = useState({
    day_of_week: 0,
    start_time: '12:00',
    end_time: '13:00',
    description: 'Almoço'
  })
  
  const daysOfWeek = [
    { value: 0, label: 'Segunda-feira' },
    { value: 1, label: 'Terça-feira' },
    { value: 2, label: 'Quarta-feira' },
    { value: 3, label: 'Quinta-feira' },
    { value: 4, label: 'Sexta-feira' },
    { value: 5, label: 'Sábado' },
    { value: 6, label: 'Domingo' }
  ]
  
  // Carregar StopTimes ao montar
  useEffect(() => {
    fetchStopTimes()
  }, [])
  
  const fetchStopTimes = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await api.get('/api/v1/admin/stop-times')
      setStopTimes(response.data)
    } catch (err) {
      console.error('Erro ao carregar intervalos de parada:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar intervalos de parada')
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleAdd = () => {
    setIsAdding(true)
    setEditingId(null)
    setSelectedDays([]) // Limpar seleção de dias
    setFormData({
      day_of_week: 0,
      start_time: '12:00',
      end_time: '13:00',
      description: 'Almoço'
    })
    setError(null)
  }
  
  const handleEdit = (stopTime) => {
    setIsAdding(false)
    setEditingId(stopTime.id)
    setFormData({
      day_of_week: stopTime.day_of_week,
      start_time: stopTime.start_time,
      end_time: stopTime.end_time,
      description: stopTime.description || ''
    })
    setError(null)
  }
  
  const handleCancel = () => {
    setIsAdding(false)
    setEditingId(null)
    setSelectedDays([]) // Limpar seleção de dias
    setFormData({
      day_of_week: 0,
      start_time: '12:00',
      end_time: '13:00',
      description: 'Almoço'
    })
    setError(null)
  }

  const handleDayToggle = (dayValue) => {
    setSelectedDays(prev => {
      if (prev.includes(dayValue)) {
        return prev.filter(d => d !== dayValue)
      } else {
        return [...prev, dayValue]
      }
    })
  }
  
  const handleSave = async (e) => {
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }
    
    // Validações
    if (formData.start_time >= formData.end_time) {
      setError('Horário de início deve ser anterior ao horário de fim')
      return
    }
    
    try {
      setIsSaving(true)
      setError(null)
      setSuccess(false)
      
      if (editingId) {
        // Atualizar existente (modo de edição - apenas um dia)
        await api.put(`/api/v1/admin/stop-times/${editingId}`, formData)
        setSuccess(true)
        setTimeout(() => setSuccess(false), 3000)
        await fetchStopTimes()
        handleCancel()
      } else {
        // Criar novos (modo de adição - múltiplos dias)
        if (selectedDays.length === 0) {
          setError('Selecione pelo menos um dia da semana')
          setIsSaving(false)
          return
        }
        
        // Criar um stop time para cada dia selecionado
        const promises = selectedDays.map(dayValue => 
          api.post('/api/v1/admin/stop-times', {
            day_of_week: dayValue,
            start_time: formData.start_time,
            end_time: formData.end_time,
            description: formData.description
          })
        )
        
        await Promise.all(promises)
        
        setSuccess(true)
        setTimeout(() => setSuccess(false), 3000)
        
        // Recarregar lista
        await fetchStopTimes()
        
        // Limpar formulário
        handleCancel()
      }
      
    } catch (err) {
      console.error('Erro ao salvar intervalo de parada:', err)
      setError(err.response?.data?.detail || 'Erro ao salvar intervalo de parada')
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja excluir este intervalo de parada?')) {
      return
    }
    
    try {
      setIsSaving(true)
      setError(null)
      await api.delete(`/api/v1/admin/stop-times/${id}`)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      await fetchStopTimes()
    } catch (err) {
      console.error('Erro ao excluir intervalo de parada:', err)
      setError(err.response?.data?.detail || 'Erro ao excluir intervalo de parada')
    } finally {
      setIsSaving(false)
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p className="ml-2 text-text">Carregando intervalos de parada...</p>
      </div>
    )
  }
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text">Intervalos de Parada/Almoço</h3>
          <p className="text-sm text-gray-600 mt-1">
            Configure horários de parada que não estarão disponíveis para agendamentos (ex: Almoço, Pausa).
          </p>
        </div>
        {!isAdding && !editingId && (
          <Button
            type="button"
            variant="secondary"
            onClick={handleAdd}
            disabled={isSaving}
          >
            + Adicionar
          </Button>
        )}
      </div>
      
      {/* Mensagens de feedback */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
          ✅ Operação realizada com sucesso!
        </div>
      )}
      
      {/* Formulário de adicionar/editar */}
      {(isAdding || editingId) && (
        <div className="bg-gray-50 border-2 border-primary rounded-lg p-3 sm:p-4 space-y-4">
          <h4 className="font-semibold text-text">
            {editingId ? 'Editar Intervalo de Parada' : 'Novo Intervalo de Parada'}
          </h4>
          
          <div className="space-y-4" onSubmit={(e) => { e.preventDefault(); handleSave(e); }}>
            {editingId ? (
              // Modo de edição: seleção única
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Dia da Semana
                </label>
                <select
                  value={formData.day_of_week}
                  onChange={(e) => setFormData({ ...formData, day_of_week: parseInt(e.target.value) })}
                  disabled={isSaving}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                >
                  {daysOfWeek.map(day => (
                    <option key={day.value} value={day.value}>
                      {day.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              // Modo de adição: seleção múltipla
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Dias da Semana (selecione um ou mais)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 sm:gap-3">
                  {daysOfWeek.map(day => (
                    <label
                      key={day.value}
                      className="flex items-center space-x-2 p-2 sm:p-3 border-2 rounded-lg cursor-pointer transition-colors hover:bg-gray-100"
                      style={{
                        borderColor: selectedDays.includes(day.value) ? '#004B6B' : '#d1d5db',
                        backgroundColor: selectedDays.includes(day.value) ? '#e6f2f7' : 'white'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedDays.includes(day.value)}
                        onChange={() => handleDayToggle(day.value)}
                        disabled={isSaving}
                        className="w-4 h-4 flex-shrink-0 text-primary focus:ring-primary border-gray-300 rounded"
                      />
                      <span className="text-xs sm:text-sm font-medium text-text whitespace-nowrap">{day.label}</span>
                    </label>
                  ))}
                </div>
                {selectedDays.length === 0 && (
                  <p className="text-xs text-red-600 mt-1">Selecione pelo menos um dia</p>
                )}
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Horário de Início
                </label>
                <Input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                  disabled={isSaving}
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Horário de Fim
                </label>
                <Input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                  disabled={isSaving}
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-text mb-2">
                Descrição (opcional)
              </label>
              <Input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Ex: Almoço, Pausa"
                disabled={isSaving}
              />
            </div>
            
            <div className="flex gap-2">
              <Button
                type="button"
                variant="primary"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? 'Salvando...' : (editingId ? 'Salvar Alterações' : `Adicionar ${selectedDays.length > 0 ? `(${selectedDays.length} ${selectedDays.length === 1 ? 'dia' : 'dias'})` : ''}`)}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={handleCancel}
                disabled={isSaving}
              >
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {/* Lista de StopTimes */}
      {stopTimes.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>Nenhum intervalo de parada configurado.</p>
          <p className="text-sm mt-2">Clique em "Adicionar" para criar um novo intervalo.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {stopTimes.map(stopTime => (
            <div
              key={stopTime.id}
              className="bg-white border-2 border-gray-200 rounded-lg p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 hover:border-primary transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                  <span className="font-semibold text-text text-sm sm:text-base">
                    {daysOfWeek.find(d => d.value === stopTime.day_of_week)?.label}
                  </span>
                  <span className="text-gray-600 text-sm sm:text-base">
                    {stopTime.start_time} - {stopTime.end_time}
                  </span>
                  {stopTime.description && (
                    <span className="text-xs sm:text-sm text-gray-500">
                      ({stopTime.description})
                    </span>
                  )}
                </div>
              </div>
              
              <div className="flex gap-2 flex-shrink-0">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => handleEdit(stopTime)}
                  disabled={isSaving || isAdding || editingId}
                  className="text-xs sm:text-sm px-3 py-1.5 sm:px-4 sm:py-2"
                >
                  Editar
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => handleDelete(stopTime.id)}
                  disabled={isSaving || isAdding || editingId}
                  className="text-xs sm:text-sm text-red-600 hover:text-red-700 px-3 py-1.5 sm:px-4 sm:py-2"
                >
                  Excluir
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default StopTimesSection

