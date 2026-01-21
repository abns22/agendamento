import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()
  const [cashSummary, setCashSummary] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [isLoadingSummary, setIsLoadingSummary] = useState(true)
  const [isLoadingTransactions, setIsLoadingTransactions] = useState(true)
  const [error, setError] = useState(null)
  
  // Modo de visualização: 'daily' ou 'custom'
  const [viewMode, setViewMode] = useState('daily')
  
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
  
  const fetchCashSummary = async () => {
    try {
      setIsLoadingSummary(true)
      setError(null)
      
      let url = '/api/v1/admin/reports/cash-summary-detailed?'
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
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text">Caixa e Relatórios</h1>
          <p className="text-gray-600 mt-1">
            Acompanhe o faturamento, custos e lucro do seu estúdio
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => navigate('/admin/expenses')}
          className="flex items-center gap-2"
        >
          <span>💸</span>
          Gerenciar Despesas
        </Button>
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
      
      {/* Cards de Resumo do Caixa */}
      {isLoadingSummary ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : cashSummary ? (
        <div className="space-y-6">
          {/* Cabeçalho do Período */}
          <div>
            <h2 className="text-xl font-bold text-text">
              {cashSummary.period_type === 'daily' ? '📅 Resumo Diário' : '📊 Resumo do Período'}
            </h2>
            {cashSummary.period_type === 'custom' && (
              <p className="text-sm text-gray-600 mt-1">
                Período: {format(new Date(cashSummary.period_start), 'dd/MM/yyyy', { locale: ptBR })} até{' '}
                {format(new Date(cashSummary.period_end), 'dd/MM/yyyy', { locale: ptBR })}
              </p>
            )}
          </div>
          
          {/* Cards de Resumo */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Card 1: Saldo Geral Líquido */}
            <Card className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300">
              <div className="flex items-center gap-3 mb-3">
                <div className="text-3xl">💰</div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">Saldo Geral Líquido</h3>
                  <p className="text-xs text-gray-500">Total consolidado</p>
                </div>
              </div>
              <div className="mt-4">
                <p className={`text-3xl font-bold ${
                  parseFloat(cashSummary.general.net_total || 0) >= 0 
                    ? 'text-green-600' 
                    : 'text-red-600'
                }`}>
                  {formatCurrency(parseFloat(cashSummary.general.net_total || 0))}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Bruto: {formatCurrency(parseFloat(cashSummary.general.gross_total || 0))}
                </p>
              </div>
            </Card>
            
            {/* Card 2: Em Caixa (Dinheiro) */}
            <Card className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-400">
              <div className="flex items-center gap-3 mb-3">
                <div className="text-3xl">💵</div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">Em Caixa</h3>
                  <p className="text-xs text-gray-500">Dinheiro físico</p>
                </div>
              </div>
              <div className="mt-4">
                <p className={`text-3xl font-bold text-green-700`}>
                  {formatCurrency(parseFloat(cashSummary.breakdown.physical_cash.balance || 0))}
                </p>
                {parseFloat(cashSummary.breakdown.physical_cash.expenses || 0) > 0 && (
                  <p className="text-xs text-red-600 mt-1">
                    Saídas: -{formatCurrency(parseFloat(cashSummary.breakdown.physical_cash.expenses || 0))}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Entradas: {formatCurrency(parseFloat(cashSummary.breakdown.physical_cash.income || 0))}
                </p>
              </div>
            </Card>
            
            {/* Card 3: Em Banco (Digital) */}
            <Card className="p-6 bg-gradient-to-br from-purple-50 to-indigo-50 border-2 border-purple-400">
              <div className="flex items-center gap-3 mb-3">
                <div className="text-3xl">🏦</div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">Em Banco</h3>
                  <p className="text-xs text-gray-500">Digital/PIX/Cartões</p>
                </div>
              </div>
              <div className="mt-4">
                <p className={`text-3xl font-bold text-purple-700`}>
                  {formatCurrency(parseFloat(cashSummary.breakdown.bank_digital.balance || 0))}
                </p>
                {parseFloat(cashSummary.breakdown.bank_digital.expenses || 0) > 0 && (
                  <p className="text-xs text-red-600 mt-1">
                    Saídas: -{formatCurrency(parseFloat(cashSummary.breakdown.bank_digital.expenses || 0))}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Entradas: {formatCurrency(parseFloat(cashSummary.breakdown.bank_digital.income || 0))}
                </p>
              </div>
            </Card>
          </div>
          
          {/* Detalhamento por Método */}
          <Card className="p-6">
            <h3 className="text-lg font-bold text-text mb-4">📊 Detalhamento por Método</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* PIX */}
              {parseFloat(cashSummary.methods_detailed.pix || 0) > 0 && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <p className="text-sm font-semibold text-gray-700 mb-1">💳 PIX</p>
                  <p className="text-xl font-bold text-blue-600">
                    {formatCurrency(parseFloat(cashSummary.methods_detailed.pix || 0))}
                  </p>
                </div>
              )}
              
              {/* Cartão de Crédito */}
              {parseFloat(cashSummary.methods_detailed.credit_card || 0) > 0 && (
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                  <p className="text-sm font-semibold text-gray-700 mb-1">💳 Crédito</p>
                  <p className="text-xl font-bold text-purple-600">
                    {formatCurrency(parseFloat(cashSummary.methods_detailed.credit_card || 0))}
                  </p>
                </div>
              )}
              
              {/* Cartão de Débito */}
              {parseFloat(cashSummary.methods_detailed.debit_card || 0) > 0 && (
                <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
                  <p className="text-sm font-semibold text-gray-700 mb-1">💳 Débito</p>
                  <p className="text-xl font-bold text-indigo-600">
                    {formatCurrency(parseFloat(cashSummary.methods_detailed.debit_card || 0))}
                  </p>
                </div>
              )}
              
              {/* Dinheiro */}
              {parseFloat(cashSummary.methods_detailed.cash || 0) > 0 && (
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <p className="text-sm font-semibold text-gray-700 mb-1">💵 Dinheiro</p>
                  <p className="text-xl font-bold text-green-600">
                    {formatCurrency(parseFloat(cashSummary.methods_detailed.cash || 0))}
                  </p>
                </div>
              )}
              
              {/* Transferência Bancária */}
              {parseFloat(cashSummary.methods_detailed.bank_transfer || 0) > 0 && (
                <div className="bg-teal-50 p-4 rounded-lg border border-teal-200">
                  <p className="text-sm font-semibold text-gray-700 mb-1">🏦 Transferência</p>
                  <p className="text-xl font-bold text-teal-600">
                    {formatCurrency(parseFloat(cashSummary.methods_detailed.bank_transfer || 0))}
                  </p>
                </div>
              )}
            </div>
            
            {/* Mensagem se não houver dados */}
            {parseFloat(cashSummary.methods_detailed.pix || 0) === 0 &&
             parseFloat(cashSummary.methods_detailed.credit_card || 0) === 0 &&
             parseFloat(cashSummary.methods_detailed.debit_card || 0) === 0 &&
             parseFloat(cashSummary.methods_detailed.cash || 0) === 0 &&
             parseFloat(cashSummary.methods_detailed.bank_transfer || 0) === 0 && (
              <p className="text-gray-500 text-center py-4">Nenhum pagamento registrado neste período.</p>
            )}
          </Card>
        </div>
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
    </div>
  )
}

export default CaixaPage

