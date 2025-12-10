import React, { useState, useEffect } from 'react'
import { api, formatCurrency } from '../../utils/api'
import { Card, Button, Input, Modal } from '../../components/ui'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

/**
 * Página de Caixa e Relatórios Financeiros.
 * 
 * Exibe:
 * - Resumo do caixa (diário e mensal)
 * - Tabela detalhada de transações
 * - Filtros por data, cliente e forma de pagamento
 */
const CaixaPage = () => {
  const [cashSummary, setCashSummary] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [isLoadingSummary, setIsLoadingSummary] = useState(true)
  const [isLoadingTransactions, setIsLoadingTransactions] = useState(true)
  const [isLoadingExpenses, setIsLoadingExpenses] = useState(true)
  const [error, setError] = useState(null)
  
  // Modo de visualização: 'daily' ou 'custom'
  const [viewMode, setViewMode] = useState('daily')
  
  // Despesas
  const [expenses, setExpenses] = useState([])
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false)
  const [isSubmittingExpense, setIsSubmittingExpense] = useState(false)
  
  // Formulário de despesa
  const [expenseForm, setExpenseForm] = useState({
    description: '',
    value: '',
    category: '',
    date_time: new Date()
  })
  
  // Filtros de data
  const [selectedDate, setSelectedDate] = useState(new Date()) // Modo Diário
  const [startDate, setStartDate] = useState(null) // Modo Período Personalizado
  const [endDate, setEndDate] = useState(null) // Modo Período Personalizado
  const [customerFilter, setCustomerFilter] = useState('')
  const [paymentMethods, setPaymentMethods] = useState([])
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('')
  
  // Carregar dados quando os filtros mudarem
  useEffect(() => {
    fetchCashSummary()
    fetchPaymentMethods()
  }, [viewMode, selectedDate, startDate, endDate])
  
  useEffect(() => {
    fetchTransactions()
  }, [viewMode, selectedDate, startDate, endDate, customerFilter, selectedPaymentMethod])
  
  useEffect(() => {
    fetchExpenses()
  }, [viewMode, selectedDate, startDate, endDate])
  
  const fetchCashSummary = async () => {
    try {
      setIsLoadingSummary(true)
      setError(null)
      
      let url = '/api/v1/admin/reports/cash-summary?'
      const params = new URLSearchParams()
      
      if (viewMode === 'daily') {
        // Modo Diário: usar a mesma data para start_date e end_date
        const dateStr = format(selectedDate, 'yyyy-MM-dd')
        params.append('start_date', dateStr)
        params.append('end_date', dateStr)
      } else {
        // Modo Período Personalizado: usar startDate e endDate
        if (startDate) {
          params.append('start_date', format(startDate, 'yyyy-MM-dd'))
        }
        if (endDate) {
          params.append('end_date', format(endDate, 'yyyy-MM-dd'))
        }
        // Se nenhum for fornecido, usar hoje (padrão do backend)
      }
      
      const response = await api.get(url + params.toString())
      setCashSummary(response.data)
    } catch (err) {
      console.error('Erro ao carregar resumo do caixa:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar resumo do caixa')
    } finally {
      setIsLoadingSummary(false)
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
  
  const fetchExpenses = async () => {
    try {
      setIsLoadingExpenses(true)
      const params = new URLSearchParams()
      
      // Se modo diário, usar selectedDate para ambos
      if (viewMode === 'daily') {
        const dateStr = format(selectedDate, 'yyyy-MM-dd')
        params.append('start_date', dateStr)
        params.append('end_date', dateStr)
      } else {
        // Modo período personalizado
        if (startDate) {
          params.append('start_date', format(startDate, 'yyyy-MM-dd'))
        }
        if (endDate) {
          params.append('end_date', format(endDate, 'yyyy-MM-dd'))
        }
      }
      
      const response = await api.get(`/api/v1/admin/expenses?${params.toString()}`)
      setExpenses(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar despesas:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar despesas')
    } finally {
      setIsLoadingExpenses(false)
    }
  }
  
  const handleOpenExpenseModal = () => {
    setExpenseForm({
      description: '',
      value: '',
      category: '',
      date_time: new Date()
    })
    setIsExpenseModalOpen(true)
  }
  
  const handleCloseExpenseModal = () => {
    setIsExpenseModalOpen(false)
    setExpenseForm({
      description: '',
      value: '',
      category: '',
      date_time: new Date()
    })
  }
  
  const handleSubmitExpense = async (e) => {
    e.preventDefault()
    
    if (!expenseForm.description.trim() || !expenseForm.value || parseFloat(expenseForm.value) <= 0) {
      setError('Preencha a descrição e um valor válido')
      return
    }
    
    try {
      setIsSubmittingExpense(true)
      setError(null)
      
      const payload = {
        description: expenseForm.description.trim(),
        value: parseFloat(expenseForm.value),
        category: expenseForm.category.trim() || null,
        date_time: expenseForm.date_time.toISOString()
      }
      
      await api.post('/api/v1/admin/expenses', payload)
      
      // Recarregar despesas e resumo
      await fetchExpenses()
      await fetchCashSummary()
      
      handleCloseExpenseModal()
    } catch (err) {
      console.error('Erro ao criar despesa:', err)
      setError(err.response?.data?.detail || 'Erro ao criar despesa')
    } finally {
      setIsSubmittingExpense(false)
    }
  }
  
  const fetchTransactions = async () => {
    try {
      setIsLoadingTransactions(true)
      setError(null)
      
      const params = new URLSearchParams()
      
      // Se modo diário, usar selectedDate para ambos
      if (viewMode === 'daily') {
        const dateStr = format(selectedDate, 'yyyy-MM-dd')
        params.append('start_date', dateStr)
        params.append('end_date', dateStr)
      } else {
        // Modo período personalizado
        if (startDate) {
          params.append('start_date', format(startDate, 'yyyy-MM-dd'))
        }
        if (endDate) {
          params.append('end_date', format(endDate, 'yyyy-MM-dd'))
        }
      }
      
      if (customerFilter) {
        params.append('customer_name', customerFilter)
      }
      if (selectedPaymentMethod) {
        params.append('payment_method_id', selectedPaymentMethod)
      }
      
      const response = await api.get(`/api/v1/admin/reports/transactions?${params.toString()}`)
      setTransactions(response.data.transactions || [])
    } catch (err) {
      console.error('Erro ao carregar transações:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar transações')
    } finally {
      setIsLoadingTransactions(false)
    }
  }
  
  const formatDateTime = (dateTime) => {
    return format(new Date(dateTime), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
  }
  
  const getPaymentMethodTotals = (summary) => {
    if (!summary || !summary.payment_methods_summary) return {}
    
    const totals = {
      cash: { name: 'Dinheiro', total: 0 },
      pix: { name: 'PIX', total: 0 },
      card: { name: 'Cartão/Conta Bancária', total: 0 }
    }
    
    summary.payment_methods_summary.forEach(pm => {
      const methodName = pm.method_name.toLowerCase()
      const value = parseFloat(pm.total_received)
      
      if (methodName.includes('dinheiro') || methodName.includes('cash')) {
        totals.cash.total += value
      } else if (methodName.includes('pix')) {
        totals.pix.total += value
      } else if (pm.is_bank_account || methodName.includes('cartão') || methodName.includes('card')) {
        totals.card.total += value
      }
    })
    
    return totals
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">Caixa e Relatórios</h1>
        <p className="text-gray-600 mt-1">
          Acompanhe o faturamento, custos e lucro do seu estúdio
        </p>
      </div>
      
      {/* Mensagem de erro */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      
      {/* Filtros de Data */}
      <Card className="p-4">
        <div className="space-y-4">
          {/* Seletor de Modo */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Modo de Visualização
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setViewMode('daily')
                  setStartDate(null)
                  setEndDate(null)
                }}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  viewMode === 'daily'
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                📅 Diário
              </button>
              <button
                type="button"
                onClick={() => setViewMode('custom')}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  viewMode === 'custom'
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                📊 Período Personalizado
              </button>
            </div>
          </div>
          
          {/* Inputs de Data baseado no Modo */}
          {viewMode === 'daily' ? (
            <div>
              <label className="block text-sm font-semibold text-text mb-2">
                Data
              </label>
              <DatePicker
                selected={selectedDate}
                onChange={(date) => setSelectedDate(date)}
                dateFormat="dd/MM/yyyy"
                className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                locale={ptBR}
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Data de Início
                </label>
                <DatePicker
                  selected={startDate}
                  onChange={(date) => setStartDate(date)}
                  dateFormat="dd/MM/yyyy"
                  placeholderText="Selecione a data inicial..."
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                  locale={ptBR}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Data de Fim
                </label>
                <DatePicker
                  selected={endDate}
                  onChange={(date) => setEndDate(date)}
                  dateFormat="dd/MM/yyyy"
                  placeholderText="Selecione a data final..."
                  minDate={startDate}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                  locale={ptBR}
                />
              </div>
            </div>
          )}
        </div>
      </Card>
      
      {/* Resumo do Caixa */}
      {isLoadingSummary ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : cashSummary && cashSummary.summary ? (
        <Card className="p-6">
          <h2 className="text-xl font-bold text-text mb-4">
            {cashSummary.is_daily ? '📅 Resumo Diário' : '📊 Resumo do Período'}
          </h2>
          {!cashSummary.is_daily && (
            <p className="text-sm text-gray-600 mb-4">
              Período: {format(new Date(cashSummary.period_start), 'dd/MM/yyyy', { locale: ptBR })} até{' '}
              {format(new Date(cashSummary.period_end), 'dd/MM/yyyy', { locale: ptBR })}
            </p>
          )}
          
          <div className="space-y-4">
            {/* Faturamento */}
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Faturamento</h3>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Bruto:</span>
                  <span className="font-semibold">
                    {formatCurrency(parseFloat(cashSummary.summary.gross_revenue))}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Líquido:</span>
                  <span className="font-bold text-primary text-lg">
                    {formatCurrency(parseFloat(cashSummary.summary.net_revenue))}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Custos e Lucro */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Custos e Lucro</h3>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Custo Total:</span>
                  <span className="font-semibold text-red-600">
                    -{formatCurrency(parseFloat(cashSummary.summary.total_cost))}
                  </span>
                </div>
                {parseFloat(cashSummary.summary.total_expenses) > 0 && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Despesas:</span>
                    <span className="font-semibold text-orange-600">
                      -{formatCurrency(parseFloat(cashSummary.summary.total_expenses))}
                    </span>
                  </div>
                )}
                <div className="flex justify-between border-t border-gray-300 pt-1 mt-1">
                  <span className="text-sm font-semibold">Lucro Bruto:</span>
                  <span className="font-bold text-green-600">
                    {formatCurrency(parseFloat(cashSummary.summary.total_profit))}
                  </span>
                </div>
                {parseFloat(cashSummary.summary.total_expenses) > 0 && (
                  <div className="flex justify-between border-t border-gray-300 pt-1 mt-1">
                    <span className="text-sm font-semibold">Lucro Líquido:</span>
                    <span className="font-bold text-blue-600 text-lg">
                      {formatCurrency(
                        parseFloat(cashSummary.summary.total_profit) - 
                        parseFloat(cashSummary.summary.total_expenses)
                      )}
                    </span>
                  </div>
                )}
              </div>
            </div>
            
            {/* Formas de Pagamento */}
            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Formas de Pagamento</h3>
              <div className="space-y-1">
                {(() => {
                  const totals = getPaymentMethodTotals(cashSummary.summary)
                  return Object.values(totals).map((method, idx) => (
                    method.total > 0 && (
                      <div key={idx} className="flex justify-between">
                        <span className="text-sm text-gray-600">{method.name}:</span>
                        <span className="font-semibold">{formatCurrency(method.total)}</span>
                      </div>
                    )
                  ))
                })()}
              </div>
            </div>
            
            {/* Estatísticas */}
            <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-200">
              {cashSummary.summary.total_transactions} transação(ões) • {cashSummary.summary.total_appointments} agendamento(s)
            </div>
          </div>
        </Card>
      ) : (
        <Card className="p-6">
          <p className="text-gray-500 text-center py-8">
            Selecione um período para visualizar o resumo do caixa.
          </p>
        </Card>
      )}
      
      {/* Tabela de Transações */}
      <Card className="p-6">
        <h2 className="text-xl font-bold text-text mb-4">📋 Transações Detalhadas</h2>
        
        {/* Filtros */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-sm font-semibold text-text mb-2">Data Inicial</label>
            <DatePicker
              selected={startDate}
              onChange={(date) => setStartDate(date)}
              dateFormat="dd/MM/yyyy"
              placeholderText="Selecione..."
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              locale={ptBR}
            />
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-text mb-2">Data Final</label>
            <DatePicker
              selected={endDate}
              onChange={(date) => setEndDate(date)}
              dateFormat="dd/MM/yyyy"
              placeholderText="Selecione..."
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              locale={ptBR}
            />
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-text mb-2">Cliente</label>
            <Input
              type="text"
              value={customerFilter}
              onChange={(e) => setCustomerFilter(e.target.value)}
              placeholder="Nome do cliente..."
            />
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-text mb-2">Forma de Pagamento</label>
            <select
              value={selectedPaymentMethod}
              onChange={(e) => setSelectedPaymentMethod(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Todas</option>
              {paymentMethods.map(method => (
                <option key={method.id} value={method.id}>
                  {method.method_name}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        {/* Tabela */}
        {isLoadingTransactions ? (
          <div className="flex justify-center items-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : transactions.length === 0 ? (
          <p className="text-gray-500 text-center py-8">Nenhuma transação encontrada para os filtros selecionados.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Data/Hora</th>
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Cliente</th>
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Serviço</th>
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Bruto</th>
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Líquido</th>
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Custo</th>
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Lucro</th>
                  <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Pagamentos</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-gray-50">
                    <td className="border border-gray-300 px-4 py-2 text-sm">
                      {formatDateTime(transaction.date_time)}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-sm">
                      {transaction.customer_name || 'N/A'}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-sm">
                      {transaction.service_name || 'N/A'}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-sm font-semibold">
                      {formatCurrency(parseFloat(transaction.gross_value))}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-sm font-semibold text-primary">
                      {formatCurrency(parseFloat(transaction.net_value))}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-sm text-red-600">
                      -{formatCurrency(parseFloat(transaction.total_cost))}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-sm font-bold text-green-600">
                      {formatCurrency(parseFloat(transaction.total_profit))}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-sm">
                      {transaction.payment_entries && transaction.payment_entries.length > 0 ? (
                        <div className="text-xs">
                          {transaction.payment_entries.map((pe, idx) => (
                            <span key={idx}>
                              {pe.payment_method_name}: {formatCurrency(parseFloat(pe.value_paid))}
                              {pe.installments && ` (${pe.installments}x)`}
                              {idx < transaction.payment_entries.length - 1 ? ' | ' : ''}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-gray-400 text-xs">Sem pagamento</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      
      {/* Modal de Lançamento de Despesa */}
      <Modal
        isOpen={isExpenseModalOpen}
        onClose={handleCloseExpenseModal}
        title="Lançar Despesa"
      >
        <form onSubmit={handleSubmitExpense} className="space-y-4">
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
              value={expenseForm.description}
              onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
              placeholder="Ex: Compra de material de limpeza"
              required
              rows={3}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isSubmittingExpense}
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
              value={expenseForm.value}
              onChange={(e) => setExpenseForm({ ...expenseForm, value: e.target.value })}
              placeholder="0.00"
              required
              disabled={isSubmittingExpense}
            />
          </div>
          
          {/* Categoria */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Categoria
            </label>
            <input
              type="text"
              value={expenseForm.category}
              onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
              placeholder="Ex: Aluguel, Material, Salário"
              maxLength={100}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isSubmittingExpense}
            />
          </div>
          
          {/* Data */}
          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Data
            </label>
            <DatePicker
              selected={expenseForm.date_time}
              onChange={(date) => setExpenseForm({ ...expenseForm, date_time: date })}
              dateFormat="dd/MM/yyyy"
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              locale={ptBR}
            />
          </div>
          
          {/* Botões */}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCloseExpenseModal}
              disabled={isSubmittingExpense}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmittingExpense}
              className="flex-1"
            >
              {isSubmittingExpense ? 'Salvando...' : 'Salvar Despesa'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

export default CaixaPage

