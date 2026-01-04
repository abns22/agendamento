import React, { useState, useEffect } from 'react'
import { Modal, Button, Input } from '../../components/ui'
import { api } from '../../utils/api'
import { format } from 'date-fns'

/**
 * Modal de Edição de Cliente.
 * 
 * Permite editar um cliente existente com nome, telefone, email e data de nascimento.
 */
const EditClientModal = ({ isOpen, onClose, client, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    phone_number: '',
    email: '',
    birth_date: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Preencher formulário quando cliente mudar
  useEffect(() => {
    if (client) {
      setFormData({
        name: client.name || '',
        phone_number: client.phone_number || '',
        email: client.email || '',
        birth_date: client.birth_date 
          ? format(new Date(client.birth_date), 'yyyy-MM-dd')
          : ''
      })
      setError(null)
    }
  }, [client])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    setError(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Validações básicas
    if (!formData.name.trim()) {
      setError('Nome é obrigatório')
      return
    }
    
    if (!formData.phone_number.trim()) {
      setError('Telefone é obrigatório')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      // Preparar dados para envio (apenas campos que mudaram)
      const payload = {
        name: formData.name.trim(),
        phone_number: formData.phone_number.trim(),
        email: formData.email.trim() || null,
        birth_date: formData.birth_date || null
      }

      await api.put(`/api/v1/admin/clients/${client.id}`, payload)

      // Chamar callback de sucesso
      if (onSuccess) onSuccess()
      onClose()

    } catch (err) {
      console.error('Erro ao atualizar cliente:', err)
      setError(err.response?.data?.detail || 'Erro ao atualizar cliente. Tente novamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setError(null)
      onClose()
    }
  }

  if (!client) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Editar Cliente"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Mensagem de erro */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Nome */}
        <Input
          type="text"
          name="name"
          label="Nome Completo *"
          value={formData.name}
          onChange={handleChange}
          placeholder="Ex: Maria Silva"
          disabled={isSubmitting}
          required
        />

        {/* Telefone */}
        <Input
          type="tel"
          name="phone_number"
          label="Telefone *"
          value={formData.phone_number}
          onChange={handleChange}
          placeholder="Ex: 11987654321"
          disabled={isSubmitting}
          required
        />

        {/* Email */}
        <Input
          type="email"
          name="email"
          label="Email (opcional)"
          value={formData.email}
          onChange={handleChange}
          placeholder="Ex: maria@email.com"
          disabled={isSubmitting}
        />

        {/* Data de Nascimento */}
        <Input
          type="date"
          name="birth_date"
          label="Data de Nascimento (opcional)"
          value={formData.birth_date}
          onChange={handleChange}
          disabled={isSubmitting}
          max={format(new Date(), 'yyyy-MM-dd')}
        />
        <p className="text-xs text-gray-500 -mt-3">
          Para receber notificações de aniversários
        </p>

        {/* Botões */}
        <div className="flex gap-2 pt-4">
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            className="flex-1"
          >
            {isSubmitting ? 'Salvando...' : 'Salvar Alterações'}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default EditClientModal

