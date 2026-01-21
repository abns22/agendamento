import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, formatCurrency } from '../../utils/api'
import { Card, Button, Input, Modal } from '../../components/ui'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

/**
 * Página de Gerenciamento de Despesas.
 * 
 * Funcionalidades:
 * - Listagem de despesas com filtros
 * - Formulário para criar nova despesa
 * - Exclusão de despesas (estorno)
 */
const ExpensesPage = () => {
  const navigate = useNavigate()
  const [expenses, setExpenses] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [expenseToDelete, setExpenseToDelete] = useState(null)
  
  // Filtros obrigatórios
  const [startDate, setStartDate] = useState(new Date())
  const [endDate, setEndDate] = useState(new Date())
  const [searchQuery, setSearchQuery] = useState('')
  const [paymentMethodFilter, setPaymentMethodFilter] = useState('')
  
  // Formulário
  const [formData, setFormData] = useState({
    description: '',
    item_name: '',
    amount: '',
    payment_method: 'CASH',
    payment_date: new Date(),
    category: ''
  })
  
  // Métodos de pagamento disponíveis
  const paymentMethods = [
    { value: 'CASH', label: 'Dinheiro' },
    { value: 'CREDIT_CARD', label: 'Cartão de Crédito' },
    { value: 'DEBIT_CARD', label: 'Cartão de Débito' },
    { value: 'PIX', label: 'PIX' },
    { value: 'BANK_TRANSFER', label: 'Transferência Bancária' }
  ]
  
  // Carregar despesas quando filtros mudarem
  useEffect(() => {
    fetchExpenses()
  }, [startDate, endDate, searchQuery, paymentMethodFilter])
  
  const fetchExpenses = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const params = new URLSearchParams()
      params.append('start_date', format(startDate, 'yyyy-MM-dd'))
      params.append('end_date', format(endDate, 'yyyy-MM-dd'))
      
      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim())
      }
      
      if (paymentMethodFilter) {
        params.append('payment_method', paymentMethodFilter)
      }
      
      const response = await api.get(`/api/v1/admin/expenses?${params.toString()}`)
      setExpenses(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar despesas:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar despesas')
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleOpenModal = () => {
    setFormData({
      description: '',
      item_name: '',
      amount: '',
      payment_method: 'CASH',
      payment_date: new Date(),
      category: ''
    })
    setIsModalOpen(true)
    setError(null)
  }
  
  const handleCloseModal = () => {
    setIsModalOpen(false)
    setFormData({
      description: '',
      item_name: '',
      amount: '',
      payment_method: 'CASH',
      payment_date: new Date(),
      category: ''
    })
  }
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.description.trim() || !formData.amount || parseFloat(formData.amount) <= 0) {
      setError('Preencha a descrição e um valor válido')
      return
    }
    
    try {
      setIsSubmitting(true)
      setError(null)
      
      const payload = {
        description: formData.description.trim(),
        item_name: formData.item_name.trim() || null,
        amount: parseFloat(formData.amount),
        payment_method: formData.payment_method,
        payment_date: formData.payment_date.toISOString(),
        category: formData.category.trim() || null
      }
      
      await api.post('/api/v1/admin/expenses', payload)
      
      await fetchExpenses()
      handleCloseModal()
    } catch (err) {
      console.error('Erro ao criar despesa:', err)
      setError(err.response?.data?.detail || 'Erro ao criar despesa')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const handleDeleteClick = (expense) => {
    setExpenseToDelete(expense)
  }
  
  const handleDeleteConfirm = async () => {
    if (!expenseToDelete) return
    
    try {
      setIsLoading(true)
      await api.delete(`/api/v1/admin/expenses/${expenseToDelete.id}`)
      await fetchExpenses()
      setExpenseToDelete(null)
    } catch (err) {
      console.error('Erro ao deletar despesa:', err)
      setError(err.response?.data?.detail || 'Erro ao deletar despesa')
    } finally {
      setIsLoading(false)
    }
  }
  
  const getPaymentMethodLabel = (method) => {
    const found = paymentMethods.find(pm => pm.value === method)
    return found ? found.label : method
  }
  
  const totalExpenses = expenses.reduce((sum, expense) => {
    return sum + parseFloat(expense.amount || 0)
  }, 0)
  
  const formatDate = (dateString) => {
    return format(new Date(dateString), 'dd/MM/yyyy', { locale: ptBR })
  }
  
  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text">Gerenciar Despesas</h1>
          <p className="text-gray-600 mt-1">
            Gerencie as saídas financeiras do seu estúdio
          </p>
        </div>
        <Button
          variant="primary"
          onClick={handleOpenModal}
          className="flex items-center gap-2"
        >
          <span>➕</span>
          Lançar Despesa
        </Button>
      </div>
      
      {/* Mensagem de erro */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      
      {/* Filtros */}
      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Data Inicial */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Data Inicial *
            </label>
            <DatePicker
              selected={startDate}
              onChange={(date) => setStartDate(date)}
              dateFormat="dd/MM/yyyy"
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              locale={ptBR}
            />
          </div>
          
          {/* Data Final */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Data Final *
            </label>
            <DatePicker
              selected={endDate}
              onChange={(date) => setEndDate(date)}
              dateFormat="dd/MM/yyyy"
              minDate={startDate}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              locale={ptBR}
            />
          </div>
          
          {/* Busca */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Buscar
            </label>
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Descrição ou item..."
            />
          </div>
          
          {/* Método de Pagamento */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Método de Pagamento
            </label>
            <select
              value={paymentMethodFilter}
              onChange={(e) => setPaymentMethodFilter(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Todos</option>
              {paymentMethods.map(method => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>
      
      {/* Tabela de Despesas */}
      <Card className="p-6">
        <h2 className="text-xl font-bold text-text mb-4">📋 Despesas</h2>
        
        {isLoading ? (
          <div className="flex justify-center items-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : expenses.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            Nenhuma despesa encontrada para o período selecionado.
          </p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Data</th>
                    <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Descrição</th>
                    <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Item</th>
                    <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Método</th>
                    <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Valor</th>
                    <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map((expense) => (
                    <tr key={expense.id} className="hover:bg-gray-50">
                      <td className="border border-gray-300 px-4 py-2 text-sm">
                        {formatDate(expense.payment_date)}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-sm">
                        {expense.description}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-sm text-gray-600">
                        {expense.item_name || '-'}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-sm">
                        {getPaymentMethodLabel(expense.payment_method)}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-sm font-bold text-red-600">
                        -{formatCurrency(parseFloat(expense.amount))}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-sm">
                        <button
                          onClick={() => handleDeleteClick(expense)}
                          className="text-red-600 hover:text-red-800 text-xs font-medium"
                          title="Excluir despesa"
                        >
                          🗑️ Excluir
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-gray-100 font-bold">
                    <td colSpan="4" className="border border-gray-300 px-4 py-3 text-right">
                      Total de Despesas:
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-red-600 text-lg">
                      -{formatCurrency(totalExpenses)}
                    </td>
                    <td className="border border-gray-300 px-4 py-3"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </>
        )}
      </Card>
      
      {/* Modal de Nova Despesa */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title="Lançar Nova Despesa"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          {/* Descrição */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Descrição *
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Ex: Conta de Luz, Produtos de Limpeza..."
              required
              rows={3}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              disabled={isSubmitting}
            />
          </div>
          
          {/* Item Comprado */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Item Comprado (opcional)
            </label>
            <Input
              type="text"
              value={formData.item_name}
              onChange={(e) => setFormData({ ...formData, item_name: e.target.value })}
              placeholder="Ex: Produtos de limpeza, Material..."
              maxLength={200}
              disabled={isSubmitting}
            />
          </div>
          
          {/* Valor */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Valor (R$) *
            </label>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              placeholder="0.00"
              required
              disabled={isSubmitting}
            />
          </div>
          
          {/* Data do Pagamento */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Data do Pagamento *
            </label>
            <DatePicker
              selected={formData.payment_date}
              onChange={(date) => setFormData({ ...formData, payment_date: date })}
              dateFormat="dd/MM/yyyy"
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              locale={ptBR}
            />
          </div>
          
          {/* Forma de Pagamento */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Forma de Pagamento *
            </label>
            <select
              value={formData.payment_method}
              onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
              required
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isSubmitting}
            >
              {paymentMethods.map(method => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
          </div>
          
          {/* Categoria */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Categoria (opcional)
            </label>
            <Input
              type="text"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              placeholder="Ex: FIXO, VARIAVEL..."
              maxLength={100}
              disabled={isSubmitting}
            />
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
              {isSubmitting ? 'Salvando...' : 'Salvar Despesa'}
            </Button>
          </div>
        </form>
      </Modal>
      
      {/* Modal de Confirmação de Exclusão */}
      <Modal
        isOpen={!!expenseToDelete}
        onClose={() => setExpenseToDelete(null)}
        title="Confirmar Exclusão"
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            Tem certeza que deseja excluir esta despesa?
          </p>
          {expenseToDelete && (
            <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
              <p><strong>Descrição:</strong> {expenseToDelete.description}</p>
              <p><strong>Valor:</strong> {formatCurrency(parseFloat(expenseToDelete.amount))}</p>
              <p><strong>Data:</strong> {formatDate(expenseToDelete.payment_date)}</p>
            </div>
          )}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setExpenseToDelete(null)}
              disabled={isLoading}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={handleDeleteConfirm}
              disabled={isLoading}
              className="flex-1 bg-red-500 hover:bg-red-600"
            >
              {isLoading ? 'Excluindo...' : 'Confirmar Exclusão'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default ExpensesPage
