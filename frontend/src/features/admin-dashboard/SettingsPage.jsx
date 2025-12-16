import React, { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { Card, Button, Input } from '../../components/ui'
import PaymentConfigSection from './PaymentConfigSection'
import StopTimesSection from './StopTimesSection'

/**
 * Página de Configurações do Tenant (Estúdio).
 * 
 * Permite ao administrador configurar:
 * - Nome da Empresa (exibido, não editável - baseado no slug)
 * - Horário de Funcionamento (abertura e fechamento)
 * - Número de WhatsApp para Notificações
 * 
 * Design mobile-first com formulário simples e feedback visual claro.
 */
const SettingsPage = () => {
  const [config, setConfig] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  
  // Campos do formulário
  const [companyName, setCompanyName] = useState('')
  const [name, setName] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [description, setDescription] = useState('')
  const [address, setAddress] = useState('')
  const [phoneContact, setPhoneContact] = useState('')
  const [scheduleDisplayText, setScheduleDisplayText] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [notificationPhone, setNotificationPhone] = useState('')
  const [notificationDays, setNotificationDays] = useState(3)
  
  // Carregar configurações ao montar
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const response = await api.get('/api/v1/admin/config')
        const data = response.data
        
        setConfig(data)
        setCompanyName(data.company_name || '')
        setName(data.name || '')
        setLogoUrl(data.logo_url || '')
        setDescription(data.description || '')
        setAddress(data.address || '')
        setPhoneContact(data.phone_contact || '')
        setScheduleDisplayText(data.schedule_display_text || '')
        setStartTime(data.default_start_time || '09:00')
        setEndTime(data.default_end_time || '18:00')
        setNotificationPhone(data.notification_phone_number || '')

        // Buscar configurações específicas do tenant (como notification_days)
        try {
          const tenantResponse = await api.get('/api/v1/admin/tenant')
          const tenantData = tenantResponse.data
          setNotificationDays(
            typeof tenantData.notification_days === 'number'
              ? tenantData.notification_days
              : 3
          )
        } catch (tenantErr) {
          console.error('Erro ao carregar dados do tenant:', tenantErr)
          // Se falhar, manter valor padrão
          setNotificationDays(3)
        }
      } catch (err) {
        console.error('Erro ao carregar configurações:', err)
        setError(err.response?.data?.detail || 'Erro ao carregar configurações')
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchConfig()
  }, [])
  
  // Salvar configurações
  const handleSave = async (e) => {
    e.preventDefault()
    
    // Validações
    if (startTime && endTime && startTime >= endTime) {
      setError('Horário de abertura deve ser anterior ao horário de fechamento')
      return
    }
    
    try {
      setIsSaving(true)
      setError(null)
      setSuccess(false)
      
      // Construir objeto de atualização com todos os campos de configuração geral
      const updateData = {
        name: name || null,
        logo_url: logoUrl || null,
        description: description || null,
        address: address || null,
        phone_contact: phoneContact || null,
        schedule_display_text: scheduleDisplayText || null,
        notification_phone_number: notificationPhone || null,
      }
      
      // Horários de funcionamento - sempre enviar se preenchidos
      if (startTime && endTime) {
        updateData.default_start_time = startTime
        updateData.default_end_time = endTime
      }
      
      console.log('📤 Enviando dados para atualização (config):', updateData)
      
      const response = await api.put('/api/v1/admin/config', updateData)
      
      console.log('✅ Resposta do servidor (config):', response.data)
      
      // Atualizar estado local com os dados retornados
      setConfig(response.data)
      setCompanyName(response.data.company_name || '')
      setName(response.data.name || '')
      setLogoUrl(response.data.logo_url || '')
      setDescription(response.data.description || '')
      setAddress(response.data.address || '')
      setPhoneContact(response.data.phone_contact || '')
      setScheduleDisplayText(response.data.schedule_display_text || '')
      setStartTime(response.data.default_start_time || '09:00')
      setEndTime(response.data.default_end_time || '18:00')
      setNotificationPhone(response.data.notification_phone_number || '')

      // Atualizar configuração específica do tenant (notification_days)
      const notificationDaysInt = parseInt(notificationDays, 10)
      if (!Number.isNaN(notificationDaysInt)) {
        await api.put('/api/v1/admin/tenant', {
          notification_days: notificationDaysInt,
        })
      }
      
      setSuccess(true)
      
      // Scroll para o topo para mostrar a mensagem de sucesso
      window.scrollTo({ top: 0, behavior: 'smooth' })
      
      // Limpar mensagem de sucesso após 5 segundos (aumentado para melhor visibilidade)
      setTimeout(() => setSuccess(false), 5000)
      
    } catch (err) {
      console.error('Erro ao salvar configurações:', err)
      setError(err.response?.data?.detail || 'Erro ao salvar configurações')
    } finally {
      setIsSaving(false)
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        <p className="ml-2 text-text">Carregando configurações...</p>
      </div>
    )
  }
  
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-text mb-6">Configurações</h1>
      
      {/* Mensagens de feedback */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      )}
      
      {success && (
        <div className="bg-green-50 border-2 border-green-400 text-green-800 px-4 py-4 rounded-lg mb-4 shadow-md animate-fade-in">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="font-semibold text-green-800">✅ Configurações salvas com sucesso!</p>
              <p className="text-sm text-green-700 mt-1">Suas alterações foram aplicadas e estão ativas.</p>
            </div>
          </div>
        </div>
      )}
      
      <Card className="p-6">
        <form onSubmit={handleSave} className="space-y-6">
          {/* Nome da Empresa (editável) */}
          <Input
            type="text"
            label="Nome da Empresa"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ex: Estúdio Bella"
            disabled={isSaving}
          />
          <p className="text-xs text-gray-500 -mt-4">
            Nome que será exibido na página pública de agendamento.
          </p>
          
          {/* Upload de Logo */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-text">
              Logo do Estúdio
            </label>
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Preview da logo atual */}
              {logoUrl && (
                <div className="flex-shrink-0">
                  <img 
                    src={logoUrl.startsWith('http') ? logoUrl : `${api.defaults.baseURL}${logoUrl}`}
                    alt="Logo atual"
                    className="h-24 w-24 object-contain border-2 border-gray-200 rounded-lg p-2"
                    onError={(e) => {
                      e.target.style.display = 'none'
                    }}
                  />
                </div>
              )}
              
              {/* Input de arquivo */}
              <div className="flex-1">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    
                    // Validar tamanho (5MB)
                    if (file.size > 5 * 1024 * 1024) {
                      setError('Arquivo muito grande. Tamanho máximo: 5MB')
                      return
                    }
                    
                    // Validar tipo
                    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                    if (!allowedTypes.includes(file.type)) {
                      setError('Tipo de arquivo não permitido. Use: JPEG, PNG, GIF ou WebP')
                      return
                    }
                    
                    try {
                      setIsSaving(true)
                      setError(null)
                      
                      // Criar FormData para upload
                      const formData = new FormData()
                      formData.append('file', file)
                      
                      // Fazer upload (o interceptor do axios remove Content-Type automaticamente para FormData)
                      const uploadResponse = await api.post('/api/v1/admin/upload/logo', formData)
                      
                      // Atualizar logo_url com a URL retornada
                      const uploadedUrl = uploadResponse.data.logo_url
                      setLogoUrl(uploadedUrl)
                      
                      // Atualizar no backend também
                      await api.put('/api/v1/admin/config', {
                        logo_url: uploadedUrl
                      })
                      
                      setSuccess(true)
                      window.scrollTo({ top: 0, behavior: 'smooth' })
                      setTimeout(() => setSuccess(false), 5000)
                      
                    } catch (err) {
                      console.error('Erro ao fazer upload:', err)
                      setError(err.response?.data?.detail || 'Erro ao fazer upload da logo')
                    } finally {
                      setIsSaving(false)
                    }
                  }}
                  disabled={isSaving}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Envie uma imagem (JPEG, PNG, GIF ou WebP) com no máximo 5MB.
                </p>
              </div>
            </div>
          </div>
          
          {/* Descrição */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-text">
              Descrição do Estúdio
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Breve descrição do estúdio e serviços oferecidos..."
              disabled={isSaving}
              rows={4}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <p className="text-xs text-gray-500">
              Descrição que será exibida na página pública de agendamento.
            </p>
          </div>
          
          {/* Endereço */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-text">
              Endereço
            </label>
            <textarea
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Rua das Flores, 123 - São Paulo, SP"
              disabled={isSaving}
              rows={2}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <p className="text-xs text-gray-500">
              Endereço físico do estúdio (será exibido na página de agendamento).
            </p>
          </div>
          
          {/* Telefone de Contato Público */}
          <Input
            type="tel"
            label="Telefone de Contato Público"
            value={phoneContact}
            onChange={(e) => setPhoneContact(e.target.value)}
            placeholder="5511999999999"
            disabled={isSaving}
          />
          <p className="text-xs text-gray-500 -mt-4">
            Número de telefone público para contato (formato internacional). Será exibido na página de agendamento.
          </p>
          
          {/* Texto do Horário de Funcionamento */}
          <Input
            type="text"
            label="Texto do Horário de Funcionamento"
            value={scheduleDisplayText}
            onChange={(e) => setScheduleDisplayText(e.target.value)}
            placeholder="Ex: Segunda a Sexta, 09:00 - 18:00"
            disabled={isSaving}
          />
          <p className="text-xs text-gray-500 -mt-4">
            Texto amigável do horário de funcionamento (será exibido na página de agendamento).
          </p>

          {/* Configuração de dias de notificação */}
          <div className="mt-4">
            <label className="block text-sm font-semibold text-text mb-2">
              Avisar sobre agendamentos nos próximos (dias)
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={30}
                value={notificationDays}
                onChange={(e) => {
                  const value = e.target.value
                  // Permitir campo vazio temporariamente no input
                  if (value === '') {
                    setNotificationDays('')
                    return
                  }
                  const intVal = parseInt(value, 10)
                  if (!Number.isNaN(intVal)) {
                    // Limitar entre 1 e 30
                    const clamped = Math.min(Math.max(intVal, 1), 30)
                    setNotificationDays(clamped)
                  }
                }}
                disabled={isSaving}
                className="w-24 px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-center"
              />
              <span className="text-sm text-gray-700">
                O sistema exibirá um aviso com a quantidade de agendamentos nos próximos dias configurados.
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Valor entre 1 e 30 dias. Se não configurado, o padrão é 3 dias.
            </p>
          </div>
          
          <div className="border-t border-gray-200 pt-6 mt-6">
            <h3 className="text-lg font-semibold text-text mb-4">Configurações Internas</h3>
          </div>
          
          {/* Seção de Configurações Financeiras */}
          <PaymentConfigSection />
          
          {/* Seção de Intervalos de Parada/Almoço */}
          <div className="border-t border-gray-200 pt-6 mt-6">
            <StopTimesSection />
          </div>
          
          {/* Horário de Funcionamento */}
          <div>
            <label className="block text-sm font-semibold text-text mb-3">
              Horário de Funcionamento
            </label>
            <div className="grid grid-cols-2 gap-4">
              <Input
                type="time"
                label="Abertura"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                placeholder="09:00"
                disabled={isSaving}
              />
              <Input
                type="time"
                label="Fechamento"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                placeholder="18:00"
                disabled={isSaving}
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Este horário será aplicado a todos os dias da semana.
            </p>
          </div>
          
          {/* Número de WhatsApp para Notificações */}
          <Input
            type="tel"
            label="Número de WhatsApp para Notificações"
            value={notificationPhone}
            onChange={(e) => setNotificationPhone(e.target.value)}
            placeholder="5511999999999"
            disabled={isSaving}
            error={null}
          />
          <p className="text-xs text-gray-500 -mt-4">
            Número no formato internacional (ex: 5511999999999). Este número receberá notificações de novos agendamentos.
          </p>
          
          {/* Botão Salvar */}
          <div className="pt-4">
            <Button
              type="submit"
              variant="primary"
              disabled={isSaving}
              className="w-full sm:w-auto"
            >
              {isSaving ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Salvando...
                </span>
              ) : (
                'Salvar Configurações'
              )}
            </Button>
          </div>
        </form>
      </Card>
      
      {/* Informações adicionais */}
      <Card className="p-4 mt-6 bg-gray-50">
        <h3 className="font-semibold text-text mb-4">Informações do Estúdio</h3>
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1">Slug do Estúdio:</p>
            <code className="bg-gray-200 px-2 py-1 rounded text-sm">{config?.slug || 'N/A'}</code>
          </div>
          
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1">ID do Tenant:</p>
            <code className="bg-gray-200 px-2 py-1 rounded text-xs">{config?.tenant_id || 'N/A'}</code>
          </div>
          
          {/* Link de Agendamento */}
          {config?.slug && (
            <div className="pt-3 border-t border-gray-300">
              <p className="text-sm font-medium text-gray-700 mb-2">🔗 Link Público de Agendamento:</p>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  readOnly
                  value={`${window.location.origin}/booking/${config.slug}`}
                  className="flex-1 px-3 py-2 bg-white border-2 border-gray-300 rounded-lg text-sm font-mono text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary"
                  onClick={(e) => e.target.select()}
                />
                <button
                  type="button"
                  onClick={() => {
                    const url = `${window.location.origin}/booking/${config.slug}`
                    navigator.clipboard.writeText(url).then(() => {
                      alert('✅ Link copiado para a área de transferência!')
                    }).catch(() => {
                      // Fallback para navegadores antigos
                      const input = document.createElement('input')
                      input.value = url
                      document.body.appendChild(input)
                      input.select()
                      document.execCommand('copy')
                      document.body.removeChild(input)
                      alert('✅ Link copiado para a área de transferência!')
                    })
                  }}
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium whitespace-nowrap"
                >
                  📋 Copiar Link
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Compartilhe este link com seus clientes para que eles possam fazer agendamentos online.
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

export default SettingsPage

