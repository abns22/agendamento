import React, { useState, useEffect } from 'react'
import { api, formatCurrency } from '../../utils/api'
import { Modal, Button, Input } from '../../components/ui'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { ptBR } from 'date-fns/locale'

/**
 * Modal de Checkout para finalização de agendamento.
 * 
 * Permite ao admin:
 * - Ver valor total do serviço
 * - Adicionar múltiplas formas de pagamento
 * - Ver cálculo automático de taxas
 * - Adicionar custo adicional opcional
 */
const CheckoutModal = ({ isOpen, onClose, appointment, service, onSuccess }) => {
  const [paymentMethods, setPaymentMethods] = useState([])
  const [isLoadingMethods, setIsLoadingMethods] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)
  
  // Estado do formulário
  const [grossValue, setGrossValue] = useState(0) // Valor bruto (com promoção se ativa)
  const [paymentEntries, setPaymentEntries] = useState([]) // Lista de formas de pagamento
  const [additionalCost, setAdditionalCost] = useState('')
  const [isPaid, setIsPaid] = useState(true) // True se foi pago, False se é a prazo
  const [clientName, setClientName] = useState('')
  const [clientPhone, setClientPhone] = useState('')
  const [dueDate, setDueDate] = useState(null)
  const [valueDue, setValueDue] = useState('') // Valor parcial do devedor
  
  // Carregar formas de pagamento ao abrir
  useEffect(() => {
    if (isOpen && appointment) {
      fetchPaymentMethods()
      calculateGrossValue()
      // Inicializar valueDue com o valor total quando abrir
      if (service) {
        const now = new Date()
        let value = parseFloat(service.price)
        if (service.is_promotional && service.promotion_start_date && service.promotion_end_date) {
          const startDate = new Date(service.promotion_start_date)
          const endDate = new Date(service.promotion_end_date)
          if (now >= startDate && now <= endDate && service.promotional_value) {
            value = parseFloat(service.promotional_value)
          }
        }
        setValueDue(value.toFixed(2))
      }
    }
  }, [isOpen, appointment, service])
  
  const fetchPaymentMethods = async () => {
    try {
      setIsLoadingMethods(true)
      const response = await api.get('/api/v1/admin/payment-config/methods')
      setPaymentMethods(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar formas de pagamento:', err)
      setError('Erro ao carregar formas de pagamento')
    } finally {
      setIsLoadingMethods(false)
    }
  }
  
  const calculateGrossValue = () => {
    if (!service) return
    
    // Verificar se há promoção ativa
    const now = new Date()
    let value = parseFloat(service.price)
    
    if (service.is_promotional && service.promotion_start_date && service.promotion_end_date) {
      const startDate = new Date(service.promotion_start_date)
      const endDate = new Date(service.promotion_end_date)
      
      if (now >= startDate && now <= endDate && service.promotional_value) {
        value = parseFloat(service.promotional_value)
      }
    }
    
    setGrossValue(value)
    
    // Inicializar com uma entrada de pagamento vazia
    if (paymentEntries.length === 0) {
      setPaymentEntries([{
        payment_method_id: '',
        value_paid: value.toFixed(2),
        installments: 1
      }])
    }
  }
  
  const addPaymentEntry = () => {
    setPaymentEntries([...paymentEntries, {
      payment_method_id: '',
      value_paid: '0.00',
      installments: 1
    }])
  }
  
  const removePaymentEntry = (index) => {
    setPaymentEntries(paymentEntries.filter((_, i) => i !== index))
  }
  
  const updatePaymentEntry = (index, field, value) => {
    const updated = [...paymentEntries]
    updated[index] = { ...updated[index], [field]: value }
    setPaymentEntries(updated)
  }
  
  const calculateTotalPaid = () => {
    return paymentEntries.reduce((sum, entry) => {
      return sum + parseFloat(entry.value_paid || 0)
    }, 0)
  }
  
  const getPaymentMethodName = (methodId) => {
    const method = paymentMethods.find(m => m.id === methodId)
    return method ? method.method_name : ''
  }
  
  const isCreditCard = (methodId) => {
    const method = paymentMethods.find(m => m.id === methodId)
    return method && (method.method_name.toLowerCase().includes('crédito') || 
                      method.method_name.toLowerCase().includes('credit'))
  }
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    
    // Validações para pagamento à vista
    if (isPaid) {
      const totalPaid = calculateTotalPaid()
      if (Math.abs(totalPaid - grossValue) > 0.01) {
        setError(`A soma dos pagamentos (${formatCurrency(totalPaid)}) deve ser igual ao valor total (${formatCurrency(grossValue)})`)
        return
      }
      
      if (paymentEntries.some(pe => !pe.payment_method_id || parseFloat(pe.value_paid) <= 0)) {
        setError('Preencha todas as formas de pagamento corretamente')
        return
      }
    }
    
    // Validar se há valor a receber (value_due)
    const hasValueDue = valueDue && parseFloat(valueDue) > 0
    if (hasValueDue) {
      if (!clientName.trim()) {
        setError('Nome do cliente é obrigatório quando há valor a receber')
        return
      }
      if (!dueDate) {
        setError('Data de vencimento é obrigatória quando há valor a receber')
        return
      }
    }
    
    // Validar que a soma dos pagamentos + valor a receber = valor bruto
    const totalPaid = paymentEntries.reduce((sum, pe) => sum + parseFloat(pe.value_paid || 0), 0)
    const valueDueNum = hasValueDue ? parseFloat(valueDue) : 0
    const totalCovered = totalPaid + valueDueNum
    
    if (Math.abs(totalCovered - grossValue) > 0.01) {
      setError(`A soma dos pagamentos (${totalPaid.toFixed(2)}) + valor a receber (${valueDueNum.toFixed(2)}) deve ser igual ao valor bruto (${grossValue.toFixed(2)})`)
      return
    }
    
    try {
      setIsSubmitting(true)
      
      const payload = {
        payment_entries: paymentEntries.map(pe => ({
          payment_method_id: pe.payment_method_id,
          value_paid: parseFloat(pe.value_paid),
          installments: isCreditCard(pe.payment_method_id) && pe.installments > 1 ? pe.installments : undefined
        })),
        additional_cost: additionalCost ? parseFloat(additionalCost) : null,
        is_paid: isPaid, // True se foi pago (total ou parcialmente)
        client_name: hasValueDue ? clientName.trim() : null,
        client_phone: hasValueDue ? (clientPhone.trim() || null) : null,
        due_date: hasValueDue ? dueDate.toISOString() : null,
        value_due: hasValueDue ? parseFloat(valueDue) : null // Valor a receber (pode ser parcial)
      }
      
      const response = await api.post(
        `/api/v1/admin/appointments/${appointment.id}/finalize`,
        payload
      )
      
      if (onSuccess) {
        onSuccess(response.data)
      }
      
      onClose()
    } catch (err) {
      console.error('Erro ao finalizar agendamento:', err)
      setError(err.response?.data?.detail || 'Erro ao finalizar agendamento')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  if (!isOpen || !appointment || !service) return null
  
  const totalPaid = calculateTotalPaid()
  const remaining = grossValue - totalPaid
  
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Finalizar Venda">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}
        
        {/* Valor Total */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex justify-between items-center">
            <span className="text-sm font-semibold text-gray-700">Valor Total:</span>
            <span className="text-2xl font-bold text-primary">
              {formatCurrency(grossValue)}
            </span>
          </div>
          {service.is_promotional && service.promotional_value && (
            <div className="mt-2 text-xs text-gray-600">
              <span className="line-through">{formatCurrency(parseFloat(service.price))}</span>
              <span className="ml-2 text-red-600 font-semibold">
                Promoção: {formatCurrency(parseFloat(service.promotional_value))}
              </span>
            </div>
          )}
        </div>
        
        {/* Formas de Pagamento */}
        <div>
          <div className="flex justify-between items-center mb-3">
            <label className="block text-sm font-semibold text-text">
              Formas de Pagamento
            </label>
            <button
              type="button"
              onClick={addPaymentEntry}
              className="text-sm text-primary hover:underline"
            >
              + Adicionar
            </button>
          </div>
          
          <div className="space-y-3">
            {paymentEntries.map((entry, index) => (
              <div key={index} className="border-2 border-gray-200 rounded-lg p-3 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-700">
                    Pagamento {index + 1}
                  </span>
                  {paymentEntries.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removePaymentEntry(index)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remover
                    </button>
                  )}
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">
                      Forma de Pagamento *
                    </label>
                    <select
                      value={entry.payment_method_id}
                      onChange={(e) => updatePaymentEntry(index, 'payment_method_id', e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary text-sm"
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
                  
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">
                      Valor (R$) *
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={entry.value_paid}
                      onChange={(e) => updatePaymentEntry(index, 'value_paid', e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                      disabled={isSubmitting}
                    />
                  </div>
                </div>
                
                {isCreditCard(entry.payment_method_id) && (
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">
                      Parcelas
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="12"
                      value={entry.installments}
                      onChange={(e) => updatePaymentEntry(index, 'installments', parseInt(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                      disabled={isSubmitting}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
          
          {/* Total Pago e Restante */}
          <div className="mt-3 p-3 bg-gray-50 rounded-lg">
            <div className="flex justify-between text-sm">
              <span className="font-semibold">Total Pago:</span>
              <span className="font-bold">{formatCurrency(totalPaid)}</span>
            </div>
            {remaining > 0.01 && (
              <div className="flex justify-between text-sm text-red-600 mt-1">
                <span>Restante:</span>
                <span className="font-bold">{formatCurrency(remaining)}</span>
              </div>
            )}
            {remaining < -0.01 && (
              <div className="flex justify-between text-sm text-orange-600 mt-1">
                <span>Troco:</span>
                <span className="font-bold">{formatCurrency(Math.abs(remaining))}</span>
              </div>
            )}
          </div>
        </div>
        
        {/* Custo Adicional */}
        <div>
          <label className="block text-sm font-semibold text-text mb-2">
            Custo Adicional (Opcional)
          </label>
          <Input
            type="number"
            min="0"
            step="0.01"
            value={additionalCost}
            onChange={(e) => setAdditionalCost(e.target.value)}
            placeholder="0.00"
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-500 mt-1">
            Custo adicional para controle interno (ex: material extra)
          </p>
        </div>
        
        {/* Opção de Pagamento Futuro */}
        <div className="border-t border-gray-200 pt-4 mt-4">
          <div className="flex items-center gap-2 mb-4">
            <input
              type="checkbox"
              id="is_paid"
              checked={isPaid}
              onChange={(e) => setIsPaid(e.target.checked)}
              className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
              disabled={isSubmitting}
            />
            <label htmlFor="is_paid" className="text-sm font-semibold text-text">
              Pagamento à vista (desmarque para criar conta a receber)
            </label>
          </div>
          
          {/* Campos para pagamento futuro */}
          {!isPaid && (
            <div className="space-y-4 pl-6 border-l-2 border-orange-300">
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Nome do Cliente *
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="Nome completo do cliente"
                  required={!isPaid}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={isSubmitting}
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Telefone do Cliente
                </label>
                <input
                  type="tel"
                  value={clientPhone}
                  onChange={(e) => setClientPhone(e.target.value)}
                  placeholder="5511999999999"
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={isSubmitting}
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Data de Vencimento *
                </label>
                <DatePicker
                  selected={dueDate}
                  onChange={(date) => setDueDate(date)}
                  dateFormat="dd/MM/yyyy"
                  minDate={new Date()}
                  placeholderText="Selecione a data de vencimento"
                  required={!isPaid}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                  locale={ptBR}
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Valor Devido (R$)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  max={grossValue}
                  value={valueDue}
                  onChange={(e) => setValueDue(e.target.value)}
                  placeholder={grossValue.toFixed(2)}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={isSubmitting}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Deixe vazio ou preencha com o valor total ({formatCurrency(grossValue)}) para registrar o valor completo. 
                  Ou informe um valor parcial se o cliente ficará devendo apenas parte do serviço.
                </p>
              </div>
              
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                <p className="text-sm text-orange-800">
                  ⚠️ Esta venda será registrada como conta a receber. O pagamento poderá ser registrado posteriormente na página de Devedores.
                </p>
              </div>
            </div>
          )}
        </div>
        
        {/* Botões */}
        <div className="flex gap-3 pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1"
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting || (isPaid && Math.abs(calculateTotalPaid() - grossValue) > 0.01)}
            className="flex-1"
          >
            {isSubmitting ? 'Finalizando...' : (isPaid ? 'Finalizar Venda' : 'Criar Conta a Receber')}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default CheckoutModal

