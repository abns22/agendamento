import React, { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { Card, Button, Input } from '../../components/ui'

/**
 * Página exclusiva do Super Admin para gerenciamento de tenants (estúdios).
 * 
 * Esta página é acessível apenas para usuários com role SUPER_ADMIN.
 * Permite criar novos estúdios e gerenciar (listar/editar) estúdios existentes.
 */
const SuperAdminPage = () => {
  // Estados para criação de tenant
  const [formData, setFormData] = useState({
    company_name: '',
    slug: '',
    admin_name: '',
    admin_email: '',
    notification_phone: '',
    password: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [createdTenant, setCreatedTenant] = useState(null)

  // Estados para listagem e edição
  const [tenants, setTenants] = useState([])
  const [isLoadingTenants, setIsLoadingTenants] = useState(false)
  const [editingTenant, setEditingTenant] = useState(null)
  const [editFormData, setEditFormData] = useState({})
  const [isSavingEdit, setIsSavingEdit] = useState(false)
  const [editError, setEditError] = useState(null)
  const [editSuccess, setEditSuccess] = useState(false)

  // Tab ativa (criar ou gerenciar)
  const [activeTab, setActiveTab] = useState('create')

  // Carregar lista de tenants ao montar
  useEffect(() => {
    if (activeTab === 'manage') {
      loadTenants()
    }
  }, [activeTab])

  // Carregar lista de tenants
  const loadTenants = async () => {
    try {
      setIsLoadingTenants(true)
      const response = await api.get('/api/v1/super-admin/tenants')
      setTenants(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar tenants:', err)
      setError('Erro ao carregar lista de tenants')
    } finally {
      setIsLoadingTenants(false)
    }
  }

  // Iniciar edição de um tenant
  const handleStartEdit = (tenant) => {
    setEditingTenant(tenant.id)
    setEditFormData({
      name: tenant.name || '',
      slug: tenant.slug || '',
      description: tenant.description || '',
      address: tenant.address || '',
      phone_contact: tenant.phone_contact || '',
      schedule_display_text: tenant.schedule_display_text || '',
      logo_url: tenant.logo_url || '',
      is_active: tenant.is_active !== undefined ? tenant.is_active : true
    })
    setEditError(null)
    setEditSuccess(false)
  }

  // Cancelar edição
  const handleCancelEdit = () => {
    setEditingTenant(null)
    setEditFormData({})
    setEditError(null)
    setEditSuccess(false)
  }

  // Salvar edição
  const handleSaveEdit = async (e) => {
    e.preventDefault()
    setEditError(null)
    setEditSuccess(false)

    try {
      setIsSavingEdit(true)
      const response = await api.put(`/api/v1/super-admin/tenants/${editingTenant}`, editFormData)
      
      // Atualizar lista
      await loadTenants()
      
      setEditSuccess(true)
      setTimeout(() => {
        setEditingTenant(null)
        setEditFormData({})
        setEditSuccess(false)
      }, 2000)
    } catch (err) {
      console.error('Erro ao salvar edição:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao salvar alterações'
      setEditError(typeof errorMessage === 'string' ? errorMessage : 'Erro ao salvar alterações')
    } finally {
      setIsSavingEdit(false)
    }
  }

  // Handler para criação de tenant
  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setCreatedTenant(null)

    // Validações básicas
    if (!formData.company_name || !formData.slug || !formData.admin_email || !formData.admin_name) {
      setError('Preencha todos os campos obrigatórios')
      return
    }

    // Validar formato do slug
    const slugPattern = /^[a-z0-9-]+$/
    if (!slugPattern.test(formData.slug)) {
      setError('Slug inválido. Use apenas letras minúsculas, números e hífens.')
      return
    }

    try {
      setIsSubmitting(true)

      const requestData = {
        company_name: formData.company_name,
        slug: formData.slug,
        admin_name: formData.admin_name.trim(),
        admin_email: formData.admin_email.trim(),
        notification_phone: formData.notification_phone?.trim() || null,
        password: formData.password?.trim() || null
      }

      const response = await api.post('/api/v1/super-admin/onboard-tenant', requestData)
      
      setCreatedTenant(response.data)
      setSuccess('Tenant criado com sucesso!')
      
      // Limpar formulário
      setFormData({
        company_name: '',
        slug: '',
        admin_name: '',
        admin_email: '',
        notification_phone: '',
        password: ''
      })

      // Recarregar lista se estiver na aba de gerenciamento
      if (activeTab === 'manage') {
        await loadTenants()
      }

    } catch (err) {
      console.error('Erro ao criar tenant:', err)
      
      // Tratar erro de validação (422)
      if (err.response?.status === 422) {
        const validationErrors = err.response?.data?.detail
        if (Array.isArray(validationErrors)) {
          const errorMessages = validationErrors.map(e => {
            const field = e.loc?.join('.') || 'campo'
            return `${field}: ${e.msg}`
          }).join(', ')
          setError(`Erro de validação: ${errorMessages}`)
        } else if (typeof validationErrors === 'string') {
          setError(validationErrors)
        } else {
          setError('Erro de validação. Verifique os campos preenchidos.')
        }
      } else {
        const errorMessage = err.response?.data?.detail || err.message || 'Erro ao criar tenant'
        setError(typeof errorMessage === 'string' ? errorMessage : 'Erro ao criar tenant')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8">
      <h1 className="text-3xl font-bold text-text mb-6 text-center">Gerenciamento de Estúdios</h1>
      
      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => setActiveTab('create')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'create'
              ? 'border-b-2 border-primary text-primary'
              : 'text-gray-600 hover:text-primary'
          }`}
        >
          ➕ Criar Novo Estúdio
        </button>
        <button
          onClick={() => setActiveTab('manage')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'manage'
              ? 'border-b-2 border-primary text-primary'
              : 'text-gray-600 hover:text-primary'
          }`}
        >
          📋 Gerenciar Estúdios
        </button>
      </div>

      {/* Tab: Criar Novo */}
      {activeTab === 'create' && (
        <div>
          {/* Mensagens de feedback */}
          {error && (
            <div className="bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{error}</span>
              </div>
            </div>
          )}
          
          {success && createdTenant && (
            <div className="bg-green-50 border-2 border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="font-semibold">{success}</span>
              </div>
              <div className="mt-3 p-3 bg-white rounded border border-green-200">
                <h3 className="font-semibold mb-2">Credenciais do Administrador:</h3>
                <p className="text-sm"><strong>Email:</strong> {createdTenant.admin_email}</p>
                <p className="text-sm"><strong>Senha Temporária:</strong> <code className="bg-gray-100 px-2 py-1 rounded">{createdTenant.temporary_password}</code></p>
                <p className="text-xs text-gray-600 mt-2">⚠️ Guarde estas credenciais! A senha temporária é exibida apenas uma vez.</p>
              </div>
            </div>
          )}
          
          <Card className="p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Informações do Estúdio */}
              <div>
                <h2 className="text-xl font-semibold text-text mb-4">Informações do Estúdio</h2>
                
                <div className="space-y-4">
                  <Input
                    type="text"
                    name="company_name"
                    label="Nome da Empresa *"
                    value={formData.company_name}
                    onChange={handleChange}
                    placeholder="Ex: Estúdio Bella"
                    disabled={isSubmitting}
                    required
                  />
                  
                  <Input
                    type="text"
                    name="slug"
                    label="Slug (URL) *"
                    value={formData.slug}
                    onChange={handleChange}
                    placeholder="ex: estudio-bella"
                    disabled={isSubmitting}
                    required
                  />
                  <p className="text-xs text-gray-500 -mt-4">
                    URL única do estúdio (apenas letras minúsculas, números e hífens). Ex: /booking/estudio-bella
                  </p>
                  
                  <Input
                    type="tel"
                    name="notification_phone"
                    label="Telefone para Notificações"
                    value={formData.notification_phone}
                    onChange={handleChange}
                    placeholder="5511999999999"
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-gray-500 -mt-4">
                    Número que receberá notificações de novos agendamentos (formato internacional)
                  </p>
                </div>
              </div>
              
              {/* Informações do Administrador */}
              <div className="border-t border-gray-200 pt-6">
                <h2 className="text-xl font-semibold text-text mb-4">Administrador do Estúdio</h2>
                
                <div className="space-y-4">
                  <Input
                    type="text"
                    name="admin_name"
                    label="Nome do Administrador *"
                    value={formData.admin_name}
                    onChange={handleChange}
                    placeholder="Ex: Maria Silva"
                    disabled={isSubmitting}
                    required
                  />
                  
                  <Input
                    type="email"
                    name="admin_email"
                    label="Email do Administrador *"
                    value={formData.admin_email}
                    onChange={handleChange}
                    placeholder="admin@estudio.com"
                    disabled={isSubmitting}
                    required
                  />
                  
                  <Input
                    type="password"
                    name="password"
                    label="Senha do Administrador"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Deixe em branco para gerar automaticamente"
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-gray-500 -mt-4">
                    Se não preenchida, uma senha temporária será gerada automaticamente
                  </p>
                </div>
              </div>
              
              {/* Botão Submit */}
              <div className="pt-4">
                <Button
                  type="submit"
                  variant="primary"
                  disabled={isSubmitting}
                  className="w-full sm:w-auto"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Criando...
                    </span>
                  ) : (
                    'Criar Estúdio'
                  )}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Tab: Gerenciar Estúdios */}
      {activeTab === 'manage' && (
        <div>
          {isLoadingTenants ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <p className="mt-2 text-gray-600">Carregando estúdios...</p>
            </div>
          ) : tenants.length === 0 ? (
            <Card className="p-6 text-center">
              <p className="text-gray-600">Nenhum estúdio cadastrado ainda.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {tenants.map((tenant) => (
                <Card key={tenant.id} className="p-6">
                  {editingTenant === tenant.id ? (
                    // Modo de edição
                    <form onSubmit={handleSaveEdit} className="space-y-4">
                      {editSuccess && (
                        <div className="bg-green-50 border-2 border-green-400 text-green-700 px-4 py-3 rounded-lg mb-4">
                          <div className="flex items-center gap-2">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            <span className="font-semibold">Alterações salvas com sucesso!</span>
                          </div>
                        </div>
                      )}
                      
                      {editError && (
                        <div className="bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
                          <span>{editError}</span>
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                          label="Nome do Estúdio"
                          value={editFormData.name || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                          disabled={isSavingEdit}
                        />
                        <Input
                          label="Slug (URL)"
                          value={editFormData.slug || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, slug: e.target.value })}
                          disabled={isSavingEdit}
                        />
                        <Input
                          label="Descrição"
                          value={editFormData.description || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                          disabled={isSavingEdit}
                        />
                        <Input
                          label="Endereço"
                          value={editFormData.address || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, address: e.target.value })}
                          disabled={isSavingEdit}
                        />
                        <Input
                          label="Telefone de Contato"
                          value={editFormData.phone_contact || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, phone_contact: e.target.value })}
                          disabled={isSavingEdit}
                        />
                        <Input
                          label="Texto de Horário"
                          value={editFormData.schedule_display_text || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, schedule_display_text: e.target.value })}
                          disabled={isSavingEdit}
                        />
                        <Input
                          label="URL da Logo"
                          value={editFormData.logo_url || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, logo_url: e.target.value })}
                          disabled={isSavingEdit}
                        />
                        <div>
                          <label className="block text-sm font-semibold text-gray-700 mb-2">
                            Status
                          </label>
                          <select
                            value={editFormData.is_active ? 'true' : 'false'}
                            onChange={(e) => setEditFormData({ ...editFormData, is_active: e.target.value === 'true' })}
                            disabled={isSavingEdit}
                            className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                          >
                            <option value="true">Ativo</option>
                            <option value="false">Inativo</option>
                          </select>
                        </div>
                      </div>

                      <div className="flex gap-2 pt-4">
                        <Button
                          type="submit"
                          variant="primary"
                          disabled={isSavingEdit}
                        >
                          {isSavingEdit ? 'Salvando...' : 'Salvar Alterações'}
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={handleCancelEdit}
                          disabled={isSavingEdit}
                        >
                          Cancelar
                        </Button>
                      </div>
                    </form>
                  ) : (
                    // Modo de visualização
                    <div>
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-xl font-bold text-text">{tenant.name || tenant.slug}</h3>
                          <p className="text-sm text-gray-600">Slug: <code className="bg-gray-100 px-2 py-1 rounded">{tenant.slug}</code></p>
                          <p className="text-xs text-gray-500 mt-1">ID: {tenant.id}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            tenant.is_active 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {tenant.is_active ? '✅ Ativo' : '❌ Inativo'}
                          </span>
                          <Button
                            variant="secondary"
                            onClick={() => handleStartEdit(tenant)}
                            className="text-sm"
                          >
                            ✏️ Editar
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        {tenant.description && (
                          <div>
                            <span className="font-semibold text-gray-700">Descrição:</span>
                            <p className="text-gray-600">{tenant.description}</p>
                          </div>
                        )}
                        {tenant.address && (
                          <div>
                            <span className="font-semibold text-gray-700">Endereço:</span>
                            <p className="text-gray-600">{tenant.address}</p>
                          </div>
                        )}
                        {tenant.phone_contact && (
                          <div>
                            <span className="font-semibold text-gray-700">Telefone:</span>
                            <p className="text-gray-600">{tenant.phone_contact}</p>
                          </div>
                        )}
                        {tenant.schedule_display_text && (
                          <div>
                            <span className="font-semibold text-gray-700">Horário:</span>
                            <p className="text-gray-600">{tenant.schedule_display_text}</p>
                          </div>
                        )}
                        {tenant.logo_url && (
                          <div className="md:col-span-2">
                            <span className="font-semibold text-gray-700">Logo:</span>
                            <p className="text-gray-600 break-all">{tenant.logo_url}</p>
                          </div>
                        )}
                      </div>

                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <a
                          href={`${window.location.origin}/booking/${tenant.slug}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline text-sm"
                        >
                          🔗 Ver página de agendamento pública
                        </a>
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SuperAdminPage
