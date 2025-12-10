import React, { useState } from 'react'
import { Modal, Button, Input } from '../../components/ui'
import { api } from '../../utils/api'

/**
 * Modal de Cadastro Rápido de Cliente.
 * 
 * Permite cadastrar um cliente rapidamente com nome, telefone, email e data de nascimento.
 */
const ClientQuickRegisterModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    phone_number: '',
    email: '',
    birth_date: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

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
      setSuccess(false)

      // Preparar dados para envio
      const payload = {
        name: formData.name.trim(),
        phone_number: formData.phone_number.trim(),
        email: formData.email.trim() || null,
        birth_date: formData.birth_date || null
      }

      await api.post('/api/v1/admin/clients', payload)

      setSuccess(true)
      
      // Limpar formulário
      setFormData({
        name: '',
        phone_number: '',
        email: '',
        birth_date: ''
      })

      // Chamar callback de sucesso após um breve delay
      setTimeout(() => {
        if (onSuccess) onSuccess()
        onClose()
        setSuccess(false)
      }, 1500)

    } catch (err) {
      console.error('Erro ao cadastrar cliente:', err)
      setError(err.response?.data?.detail || 'Erro ao cadastrar cliente. Tente novamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setFormData({
        name: '',
        phone_number: '',
        email: '',
        birth_date: ''
      })
      setError(null)
      setSuccess(false)
      onClose()
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Cadastrar Cliente"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Mensagens de feedback */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
            ✅ Cliente cadastrado com sucesso!
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
            {isSubmitting ? 'Cadastrando...' : 'Cadastrar Cliente'}
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

export default ClientQuickRegisterModal

