import React, { useState, useEffect } from 'react'
import { api, formatCurrency } from '../../utils/api'
import { Card, Button, Modal } from '../../components/ui'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

/**
 * Página de Gestão de Devedores (Contas a Receber).
 * 
 * Exibe:
 * - Lista de devedores pendentes e pagos
 * - Botão para dar baixa em devedores pendentes
 * - Filtros por status
 */
const DebtorsPage = () => {
  const [debtors, setDebtors] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('PENDING') // 'PENDING' ou 'PAID' ou null para todos
  
  // Modal de baixa
  const [isSettleModalOpen, setIsSettleModalOpen] = useState(false)
  const [selectedDebtor, setSelectedDebtor] = useState(null)
  const [paymentMethods, setPaymentMethods] = useState([])
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('')
  const [installments, setInstallments] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Carregar dados
  useEffect(() => {
    fetchDebtors()
    fetchPaymentMethods()
  }, [statusFilter])
  
  const fetchDebtors = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const params = statusFilter ? `?status=${statusFilter}` : ''
      const response = await api.get(`/api/v1/admin/debtors${params}`)
      setDebtors(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar devedores:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar devedores')
    } finally {
      setIsLoading(false)
    }
  }
  
  const fetchPaymentMethods = async () => {
    try {
      const response = await api.get('/api/v1/admin/payment-config/methods')
      setPaymentMethods(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar formas de pagamento:', err)
    }
  }
  
  const handleOpenSettleModal = (debtor) => {
    setSelectedDebtor(debtor)
    setSelectedPaymentMethod('')
    setInstallments(1)
    setIsSettleModalOpen(true)
  }
  
  const handleCloseSettleModal = () => {
    setIsSettleModalOpen(false)
    setSelectedDebtor(null)
    setSelectedPaymentMethod('')
    setInstallments(1)
  }
  
  const handleSettle = async (e) => {
    e.preventDefault()
    
    if (!selectedDebtor || !selectedPaymentMethod) {
      setError('Selecione uma forma de pagamento')
      return
    }
    
    try {
      setIsSubmitting(true)
      setError(null)
      
      const payload = {
        payment_method_id: selectedPaymentMethod,
        installments: installments > 1 ? installments : undefined
      }
      
      await api.post(`/api/v1/admin/debtors/${selectedDebtor.id}/settle`, payload)
      
      // Recarregar lista
      await fetchDebtors()
      
      handleCloseSettleModal()
    } catch (err) {
      console.error('Erro ao dar baixa:', err)
      setError(err.response?.data?.detail || 'Erro ao dar baixa no devedor')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const formatDate = (dateTime) => {
    return format(new Date(dateTime), 'dd/MM/yyyy', { locale: ptBR })
  }
  
  const formatDateTime = (dateTime) => {
    return format(new Date(dateTime), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
  }
  
  const isOverdue = (dueDate) => {
    return new Date(dueDate) < new Date()
  }
  
  const isCreditCard = (methodId) => {
    const method = paymentMethods.find(m => m.id === methodId)
    return method && (method.method_name.toLowerCase().includes('crédito') || 
                      method.method_name.toLowerCase().includes('credit'))
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">Devedores (Contas a Receber)</h1>
        <p className="text-gray-600 mt-1">
          Gerencie as contas a receber do seu estúdio
        </p>
      </div>
      
      {/* Mensagem de erro */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      
      {/* Filtros */}
      <Card className="p-4">
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setStatusFilter(null)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === null
                ? 'bg-primary text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => setStatusFilter('PENDING')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === 'PENDING'
                ? 'bg-orange-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Pendentes
          </button>
          <button
            onClick={() => setStatusFilter('PAID')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === 'PAID'
                ? 'bg-green-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Pagos
          </button>
        </div>
      </Card>
      
      {/* Lista de Devedores */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : debtors.length === 0 ? (
        <Card className="p-8">
          <p className="text-gray-500 text-center">
            {statusFilter === 'PENDING' 
              ? 'Nenhuma conta a receber pendente.'
              : statusFilter === 'PAID'
              ? 'Nenhuma conta a receber paga encontrada.'
              : 'Nenhuma conta a receber registrada.'}
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {debtors.map((debtor) => (
            <Card key={debtor.id} className="p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-bold text-text">{debtor.client_name}</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      debtor.status === 'PAID'
                        ? 'bg-green-100 text-green-800'
                        : isOverdue(debtor.due_date)
                        ? 'bg-red-100 text-red-800'
                        : 'bg-orange-100 text-orange-800'
                    }`}>
                      {debtor.status === 'PAID' ? 'Pago' : isOverdue(debtor.due_date) ? 'Vencido' : 'Pendente'}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-600">
                    {debtor.client_phone && (
                      <div>
                        <span className="font-semibold">Telefone:</span> {debtor.client_phone}
                      </div>
                    )}
                    <div>
                      <span className="font-semibold">Vencimento:</span>{' '}
                      <span className={isOverdue(debtor.due_date) && debtor.status === 'PENDING' ? 'text-red-600 font-bold' : ''}>
                        {formatDate(debtor.due_date)}
                      </span>
                    </div>
                    <div>
                      <span className="font-semibold">Valor:</span>{' '}
                      <span className="text-primary font-bold text-lg">
                        {formatCurrency(parseFloat(debtor.value_due))}
                      </span>
                    </div>
                    {debtor.status === 'PAID' && debtor.paid_at && (
                      <div>
                        <span className="font-semibold">Pago em:</span> {formatDateTime(debtor.paid_at)}
                      </div>
                    )}
                  </div>
                </div>
                
                {debtor.status === 'PENDING' && (
                  <div>
                    <Button
                      variant="primary"
                      onClick={() => handleOpenSettleModal(debtor)}
                      className="w-full sm:w-auto"
                    >
                      💰 Dar Baixa
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
      
      {/* Modal de Baixa */}
      <Modal
        isOpen={isSettleModalOpen}
        onClose={handleCloseSettleModal}
        title="Dar Baixa em Conta a Receber"
      >
        {selectedDebtor && (
          <form onSubmit={handleSettle} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}
            
            {/* Informações do Devedor */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Informações da Conta</h3>
              <div className="space-y-1 text-sm">
                <div>
                  <span className="font-semibold">Cliente:</span> {selectedDebtor.client_name}
                </div>
                <div>
                  <span className="font-semibold">Valor:</span>{' '}
                  <span className="text-primary font-bold">
                    {formatCurrency(parseFloat(selectedDebtor.value_due))}
                  </span>
                </div>
                <div>
                  <span className="font-semibold">Vencimento:</span> {formatDate(selectedDebtor.due_date)}
                </div>
              </div>
            </div>
            
            {/* Forma de Pagamento */}
            <div>
              <label className="block text-sm font-semibold text-text mb-2">
                Forma de Pagamento *
              </label>
              <select
                value={selectedPaymentMethod}
                onChange={(e) => setSelectedPaymentMethod(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              >
                <option value="">Selecione...</option>
                {paymentMethods.map(method => (
                  <option key={method.id} value={method.id}>
                    {method.method_name}
                  </option>
                ))}
              </select>
            </div>
            
            {/* Parcelas (se cartão de crédito) */}
            {isCreditCard(selectedPaymentMethod) && (
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Parcelas
                </label>
                <input
                  type="number"
                  min="1"
                  max="12"
                  value={installments}
                  onChange={(e) => setInstallments(parseInt(e.target.value))}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={isSubmitting}
                />
              </div>
            )}
            
            {/* Botões */}
            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={handleCloseSettleModal}
                disabled={isSubmitting}
                className="flex-1"
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                variant="primary"
                disabled={isSubmitting || !selectedPaymentMethod}
                className="flex-1"
              >
                {isSubmitting ? 'Processando...' : 'Confirmar Baixa'}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  )
}

export default DebtorsPage

