import React, { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { Card, Button, Modal } from '../../components/ui'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import EditClientModal from './EditClientModal'

/**
 * Página de Gerenciamento de Clientes.
 * 
 * Funcionalidades:
 * - Listar clientes do tenant
 * - Buscar por nome ou telefone
 * - Filtrar aniversariantes por mês
 * - Abrir WhatsApp com mensagem pré-definida
 * - Design mobile-first
 */
const ClientsPage = () => {
  const [clients, setClients] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedMonth, setSelectedMonth] = useState(null) // null = "Todos", 1-12 = mês específico
  const [tenantName, setTenantName] = useState('Estúdio') // Nome do tenant para mensagem do WhatsApp
  const [editingClient, setEditingClient] = useState(null) // Cliente sendo editado
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [deletingClientId, setDeletingClientId] = useState(null) // ID do cliente sendo deletado
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)

  // Meses do ano
  const months = [
    { value: null, label: 'Todos' },
    { value: 1, label: 'Janeiro' },
    { value: 2, label: 'Fevereiro' },
    { value: 3, label: 'Março' },
    { value: 4, label: 'Abril' },
    { value: 5, label: 'Maio' },
    { value: 6, label: 'Junho' },
    { value: 7, label: 'Julho' },
    { value: 8, label: 'Agosto' },
    { value: 9, label: 'Setembro' },
    { value: 10, label: 'Outubro' },
    { value: 11, label: 'Novembro' },
    { value: 12, label: 'Dezembro' }
  ]

  // Carregar nome do tenant ao montar o componente
  useEffect(() => {
    const fetchTenantName = async () => {
      try {
        const response = await api.get('/api/v1/admin/tenant')
        const tenantData = response.data
        
        // Formatar slug como nome do estúdio
        // Ex: "estudio-bella" → "Estúdio Bella"
        if (tenantData.slug) {
          const formattedName = tenantData.slug
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ')
          setTenantName(formattedName)
        } else if (tenantData.name) {
          setTenantName(tenantData.name)
        } else {
          setTenantName('Estúdio')
        }
      } catch (error) {
        console.error('Erro ao buscar nome do tenant:', error)
        setTenantName('Estúdio') // Fallback
      }
    }
    
    fetchTenantName()
  }, [])

  // Carregar clientes quando busca ou mês mudarem
  useEffect(() => {
    fetchClients()
  }, [searchTerm, selectedMonth])

  const fetchClients = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Construir query params
      const params = new URLSearchParams()
      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim())
      }
      if (selectedMonth !== null) {
        params.append('birth_month', selectedMonth)
      }
      
      const response = await api.get(`/api/v1/admin/clients?${params.toString()}`)
      setClients(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar clientes:', err)
      setError('Erro ao carregar clientes. Tente novamente.')
    } finally {
      setIsLoading(false)
    }
  }

  // Verificar se cliente é aniversariante do mês atual
  const isCurrentMonthBirthday = (client) => {
    if (!client.birth_date) return false
    const birthDate = new Date(client.birth_date)
    const currentMonth = new Date().getMonth() + 1 // getMonth() retorna 0-11
    return birthDate.getMonth() + 1 === currentMonth
  }

  // Formatar telefone brasileiro
  const formatPhone = (phone) => {
    if (!phone) return ''
    // Remove caracteres não numéricos
    const cleaned = phone.replace(/\D/g, '')
    
    // Formatar: (11) 98765-4321 para 11 dígitos
    if (cleaned.length === 11) {
      return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`
    }
    // Formatar: (11) 9876-5432 para 10 dígitos
    if (cleaned.length === 10) {
      return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 6)}-${cleaned.slice(6)}`
    }
    return phone
  }

  // Formatar data de nascimento (evitando problemas de timezone)
  const formatBirthDate = (birthDate) => {
    if (!birthDate) return 'Não informado'
    try {
      // Extrair apenas a parte da data (YYYY-MM-DD) para evitar problemas de timezone
      let dateStr = birthDate
      if (typeof birthDate === 'string' && birthDate.includes('T')) {
        dateStr = birthDate.split('T')[0]
      }
      // Parsear a data diretamente: YYYY-MM-DD
      const [year, month, day] = dateStr.split('-').map(Number)
      const date = new Date(year, month - 1, day) // month é 0-indexed no JS
      return format(date, "dd 'de' MMMM 'de' yyyy", { locale: ptBR })
    } catch (error) {
      return 'Data inválida'
    }
  }

  // Abrir WhatsApp com mensagem pré-definida
  const openWhatsApp = (client) => {
    if (!client.phone_number) {
      alert('Cliente não possui telefone cadastrado')
      return
    }
    
    // Remover caracteres não numéricos do telefone
    const phone = client.phone_number.replace(/\D/g, '')
    
    // Mensagem pré-definida usando o nome do tenant
    const message = encodeURIComponent(
      `Olá ${client.name}, o ${tenantName} deseja um feliz aniversário! 🎂🎉`
    )
    
    // Link do WhatsApp (formato internacional: 55 + DDD + número)
    // Se o telefone já começar com 55, usar direto, senão adicionar 55
    const whatsappPhone = phone.startsWith('55') ? phone : `55${phone}`
    const whatsappUrl = `https://wa.me/${whatsappPhone}?text=${message}`
    
    window.open(whatsappUrl, '_blank')
  }

  // Obter dia do mês do aniversário (evitando problemas de timezone)
  const getBirthdayDay = (birthDate) => {
    if (!birthDate) return null
    try {
      // Extrair apenas a parte da data (YYYY-MM-DD) para evitar problemas de timezone
      let dateStr = birthDate
      if (typeof birthDate === 'string' && birthDate.includes('T')) {
        dateStr = birthDate.split('T')[0]
      }
      // Parsear a data diretamente: YYYY-MM-DD
      const [year, month, day] = dateStr.split('-').map(Number)
      return day
    } catch (error) {
      return null
    }
  }

  // Abrir modal de edição
  const handleEditClick = (client) => {
    setEditingClient(client)
    setIsEditModalOpen(true)
  }

  // Fechar modal de edição
  const handleCloseEditModal = () => {
    setIsEditModalOpen(false)
    setEditingClient(null)
  }

  // Sucesso na edição
  const handleEditSuccess = () => {
    fetchClients() // Recarregar lista
    handleCloseEditModal()
  }

  // Abrir modal de confirmação de exclusão
  const handleDeleteClick = (client) => {
    setDeletingClientId(client.id)
    setIsDeleteModalOpen(true)
  }

  // Fechar modal de exclusão
  const handleCloseDeleteModal = () => {
    setIsDeleteModalOpen(false)
    setDeletingClientId(null)
  }

  // Confirmar exclusão
  const handleConfirmDelete = async () => {
    if (!deletingClientId) return

    try {
      await api.delete(`/api/v1/admin/clients/${deletingClientId}`)
      handleCloseDeleteModal()
      fetchClients() // Recarregar lista
    } catch (err) {
      console.error('Erro ao excluir cliente:', err)
      alert(err.response?.data?.detail || 'Erro ao excluir cliente. Tente novamente.')
    }
  }

  // Obter nome do cliente sendo deletado
  const deletingClientName = deletingClientId 
    ? clients.find(c => c.id === deletingClientId)?.name 
    : ''

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-2xl font-bold text-text">Clientes</h1>
        <p className="text-gray-600 mt-1">
          Gerencie seus clientes e identifique aniversariantes
        </p>
      </div>

      {/* Filtros */}
      <Card className="p-4">
        <div className="space-y-4">
          {/* Barra de Busca */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              🔍 Buscar Cliente
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Digite o nome ou telefone..."
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {/* Seletor de Mês */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              📅 Filtrar por Mês de Aniversário
            </label>
            <select
              value={selectedMonth === null ? '' : selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value === '' ? null : parseInt(e.target.value))}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              {months.map(month => (
                <option key={month.value === null ? 'all' : month.value} value={month.value === null ? '' : month.value}>
                  {month.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

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
          <p className="text-gray-600">Carregando clientes...</p>
        </div>
      )}

      {/* Lista vazia */}
      {!isLoading && clients.length === 0 && (
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">👥</div>
            <h3 className="text-lg font-semibold text-text mb-2">
              {searchTerm || selectedMonth !== null 
                ? 'Nenhum cliente encontrado' 
                : 'Nenhum cliente cadastrado'}
            </h3>
            <p className="text-gray-600">
              {searchTerm || selectedMonth !== null
                ? 'Tente ajustar os filtros de busca'
                : 'Comece cadastrando seus primeiros clientes'}
            </p>
          </div>
        </Card>
      )}

      {/* Lista de Clientes */}
      {!isLoading && clients.length > 0 && (
        <div className="space-y-4">
          {clients.map((client) => {
            const isBirthday = isCurrentMonthBirthday(client)
            const birthdayDay = getBirthdayDay(client.birth_date)
            
            return (
              <Card
                key={client.id}
                className={`${
                  isBirthday 
                    ? 'border-2 border-pink-400 bg-gradient-to-r from-pink-50 to-purple-50' 
                    : 'border border-gray-200'
                }`}
              >
                <div className="p-4 space-y-3">
                  {/* Cabeçalho do Card */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-bold text-text truncate">
                          {client.name}
                        </h3>
                        {isBirthday && (
                          <span className="text-2xl flex-shrink-0" title="Aniversariante do mês">
                            🎂
                          </span>
                        )}
                      </div>
                      {isBirthday && birthdayDay && (
                        <p className="text-xs text-pink-600 font-semibold mb-2">
                          Aniversário: dia {birthdayDay}
                        </p>
                      )}
                    </div>
                    {/* Botões de ação */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleEditClick(client)}
                        className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors"
                        title="Editar cliente"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteClick(client)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Excluir cliente"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Informações do Cliente */}
                  <div className="space-y-2">
                    {/* Telefone */}
                    {client.phone_number && (
                      <div className="flex items-center gap-2">
                        <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                        </svg>
                        <span className="text-sm text-gray-700 flex-1">
                          {formatPhone(client.phone_number)}
                        </span>
                      </div>
                    )}

                    {/* Email */}
                    {client.email && (
                      <div className="flex items-center gap-2">
                        <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                        <span className="text-sm text-gray-700 truncate">
                          {client.email}
                        </span>
                      </div>
                    )}

                    {/* Data de Nascimento */}
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <span className="text-sm text-gray-700">
                        {formatBirthDate(client.birth_date)}
                      </span>
                    </div>

                    {/* Botão WhatsApp - discreto, abaixo das informações */}
                    {client.phone_number && (
                      <div className="pt-2 border-t border-gray-200">
                        <button
                          onClick={() => openWhatsApp(client)}
                          className="w-full flex items-center justify-center gap-2 bg-green-50 hover:bg-green-100 text-green-700 px-3 py-2 rounded-lg text-sm font-medium transition-colors border border-green-200"
                          title="Enviar mensagem de aniversário via WhatsApp"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                          </svg>
                          <span>Enviar mensagem de aniversário</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Modal de Edição */}
      <EditClientModal
        isOpen={isEditModalOpen}
        onClose={handleCloseEditModal}
        client={editingClient}
        onSuccess={handleEditSuccess}
      />

      {/* Modal de Confirmação de Exclusão */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={handleCloseDeleteModal}
        title="Confirmar Exclusão"
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            Tem certeza que deseja excluir o cliente <strong>{deletingClientName}</strong>?
          </p>
          <p className="text-sm text-gray-600">
            Esta ação não pode ser desfeita. O cliente será removido permanentemente do sistema.
          </p>
          <div className="flex gap-2 pt-4">
            <Button
              variant="secondary"
              onClick={handleCloseDeleteModal}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirmDelete}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              Excluir
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default ClientsPage

