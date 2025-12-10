import React, { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { Card, Button, Input } from '../../components/ui'

/**
 * Seção de Configuração de Formas de Pagamento.
 * 
 * Permite configurar:
 * - Taxa de Cartão de Débito (% ou R$)
 * - Tabela de taxas de parcelamento para Cartão de Crédito
 */
const PaymentConfigSection = () => {
  const [paymentMethods, setPaymentMethods] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  
  // Estados para Cartão de Débito
  const [debitMethod, setDebitMethod] = useState(null)
  const [debitTaxType, setDebitTaxType] = useState('%')
  const [debitTaxValue, setDebitTaxValue] = useState('')
  
  // Estados para Cartão de Crédito
  const [creditMethod, setCreditMethod] = useState(null)
  const [installments, setInstallments] = useState([])
  const [editingInstallment, setEditingInstallment] = useState(null) // ID da parcela sendo editada
  const [newInstallment, setNewInstallment] = useState({
    installments_count: '',
    tax_type: '%',
    tax_value: ''
  })
  
  // Carregar formas de pagamento ao montar
  useEffect(() => {
    fetchPaymentMethods()
  }, [])
  
  const fetchPaymentMethods = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await api.get('/api/v1/admin/payment-config/methods')
      const methods = response.data
      
      setPaymentMethods(methods)
      
      // Encontrar Cartão de Débito e Crédito
      const debit = methods.find(m => 
        m.method_name.toLowerCase().includes('débito') || 
        m.method_name.toLowerCase().includes('debit')
      )
      const credit = methods.find(m => 
        m.method_name.toLowerCase().includes('crédito') || 
        m.method_name.toLowerCase().includes('credit')
      )
      
      if (debit) {
        setDebitMethod(debit)
        setDebitTaxType(debit.debit_tax_type || '%')
        setDebitTaxValue(debit.debit_tax_value || '')
      }
      
      if (credit) {
        setCreditMethod(credit)
        setInstallments(credit.installments || [])
      }
      
      // Se não existirem, criar padrões
      if (!debit) {
        await createDefaultPaymentMethod('Cartão de Débito', false, null, '%', null)
      }
      if (!credit) {
        await createDefaultPaymentMethod('Cartão de Crédito', true, 12, null, null)
      }
      
    } catch (err) {
      console.error('Erro ao carregar formas de pagamento:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar configurações de pagamento')
    } finally {
      setIsLoading(false)
    }
  }
  
  const createDefaultPaymentMethod = async (name, editable, maxInstallments, taxType, taxValue) => {
    try {
      const response = await api.post('/api/v1/admin/payment-config/methods', {
        method_name: name,
        is_editable: editable,
        max_installments: maxInstallments,
        debit_tax_type: taxType,
        debit_tax_value: taxValue
      })
      
      if (name.includes('Débito') || name.includes('Debit')) {
        setDebitMethod(response.data)
      } else if (name.includes('Crédito') || name.includes('Credit')) {
        setCreditMethod(response.data)
        setInstallments([])
      }
      
      // Recarregar lista
      await fetchPaymentMethods()
    } catch (err) {
      console.error('Erro ao criar forma de pagamento padrão:', err)
    }
  }
  
  const handleSaveDebit = async () => {
    if (!debitMethod) return
    
    try {
      setIsSaving(true)
      setError(null)
      
      await api.put(`/api/v1/admin/payment-config/methods/${debitMethod.id}`, {
        debit_tax_type: debitTaxType,
        debit_tax_value: debitTaxValue ? parseFloat(debitTaxValue) : null
      })
      
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      
      // Recarregar
      await fetchPaymentMethods()
    } catch (err) {
      console.error('Erro ao salvar configuração de débito:', err)
      setError(err.response?.data?.detail || 'Erro ao salvar configuração')
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleAddInstallment = async () => {
    if (!creditMethod || !newInstallment.installments_count || !newInstallment.tax_value) {
      setError('Preencha todos os campos')
      return
    }
    
    try {
      setIsSaving(true)
      setError(null)
      
      await api.post(`/api/v1/admin/payment-config/methods/${creditMethod.id}/installments`, {
        payment_method_id: creditMethod.id,
        installments_count: parseInt(newInstallment.installments_count),
        tax_type: newInstallment.tax_type,
        tax_value: parseFloat(newInstallment.tax_value)
      })
      
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      
      // Limpar formulário
      setNewInstallment({
        installments_count: '',
        tax_type: '%',
        tax_value: ''
      })
      
      // Recarregar
      await fetchPaymentMethods()
    } catch (err) {
      console.error('Erro ao adicionar parcela:', err)
      setError(err.response?.data?.detail || 'Erro ao adicionar configuração de parcela')
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleEditInstallment = (installment) => {
    setEditingInstallment(installment.id)
    setNewInstallment({
      installments_count: installment.installments_count.toString(),
      tax_type: installment.tax_type,
      tax_value: installment.tax_value.toString()
    })
  }

  const handleCancelEdit = () => {
    setEditingInstallment(null)
    setNewInstallment({
      installments_count: '',
      tax_type: '%',
      tax_value: ''
    })
  }

  const handleUpdateInstallment = async () => {
    if (!creditMethod || !editingInstallment || !newInstallment.installments_count || !newInstallment.tax_value) {
      setError('Preencha todos os campos')
      return
    }
    
    try {
      setIsSaving(true)
      setError(null)
      
      await api.put(`/api/v1/admin/payment-config/installments/${editingInstallment}`, {
        tax_type: newInstallment.tax_type,
        tax_value: parseFloat(newInstallment.tax_value)
      })
      
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      
      // Limpar formulário
      setEditingInstallment(null)
      setNewInstallment({
        installments_count: '',
        tax_type: '%',
        tax_value: ''
      })
      
      // Recarregar
      await fetchPaymentMethods()
    } catch (err) {
      console.error('Erro ao atualizar parcela:', err)
      setError(err.response?.data?.detail || 'Erro ao atualizar configuração de parcela')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteInstallment = async (installmentId) => {
    if (!confirm('Deseja realmente remover esta configuração de parcela?')) {
      return
    }
    
    try {
      setIsSaving(true)
      setError(null)
      
      await api.delete(`/api/v1/admin/payment-config/installments/${installmentId}`)
      
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      
      // Recarregar
      await fetchPaymentMethods()
    } catch (err) {
      console.error('Erro ao remover parcela:', err)
      setError(err.response?.data?.detail || 'Erro ao remover configuração')
    } finally {
      setIsSaving(false)
    }
  }
  
  if (isLoading) {
    return (
      <div className="border-t border-gray-200 pt-6 mt-6">
        <h3 className="text-lg font-semibold text-text mb-4">💰 Configurações Financeiras</h3>
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="ml-2 text-text">Carregando...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="border-t border-gray-200 pt-6 mt-6">
      <h3 className="text-lg font-semibold text-text mb-4">💰 Configurações Financeiras</h3>
      
      {/* Mensagens de feedback */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          <span>{error}</span>
        </div>
      )}
      
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4">
          <span>✅ Configuração salva com sucesso!</span>
        </div>
      )}
      
      {/* Configuração de Cartão de Débito */}
      {debitMethod && (
        <Card className="p-6 mb-6">
          <h4 className="text-md font-semibold text-text mb-4">💳 Cartão de Débito</h4>
          
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-semibold text-text mb-2">
                Tipo de Taxa
              </label>
              <select
                value={debitTaxType}
                onChange={(e) => setDebitTaxType(e.target.value)}
                disabled={isSaving}
                className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="%">Percentual (%)</option>
                <option value="R$">Valor Fixo (R$)</option>
              </select>
            </div>
            
            <div>
              <Input
                type="number"
                label="Valor da Taxa"
                value={debitTaxValue}
                onChange={(e) => setDebitTaxValue(e.target.value)}
                placeholder={debitTaxType === '%' ? 'Ex: 2.5' : 'Ex: 1.50'}
                disabled={isSaving}
                step="0.01"
                min="0"
              />
            </div>
            
            <div className="flex items-end">
              <Button
                type="button"
                variant="primary"
                onClick={handleSaveDebit}
                disabled={isSaving}
                className="w-full"
              >
                {isSaving ? 'Salvando...' : 'Salvar'}
              </Button>
            </div>
          </div>
          
          <p className="text-xs text-gray-500 mt-2">
            {debitTaxType === '%' 
              ? 'Taxa será calculada como percentual sobre o valor do serviço.'
              : 'Taxa será adicionada como valor fixo ao valor do serviço.'}
          </p>

          {/* Exibir configuração salva do Cartão de Débito */}
          {debitMethod.debit_tax_type && debitMethod.debit_tax_value && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h5 className="text-sm font-semibold text-text mb-3">📋 Configuração Atual</h5>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      <span className="font-medium">Tipo:</span> {debitMethod.debit_tax_type === '%' ? 'Percentual (%)' : 'Valor Fixo (R$)'}
                    </p>
                    <p className="text-sm text-gray-700 mt-1">
                      <span className="font-medium">Taxa:</span>{' '}
                      {debitMethod.debit_tax_type === '%' 
                        ? `${parseFloat(debitMethod.debit_tax_value).toFixed(2)}%`
                        : `R$ ${parseFloat(debitMethod.debit_tax_value).toFixed(2)}`}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Card>
      )}
      
      {/* Configuração de Cartão de Crédito */}
      {creditMethod && (
        <Card className="p-4 sm:p-6">
          <h4 className="text-md font-semibold text-text mb-4">💳 Cartão de Crédito - Taxas de Parcelamento</h4>
          
          {/* Lista de configurações salvas */}
          {installments.length > 0 && (
            <div className="mb-6 overflow-x-hidden">
              <h5 className="text-sm font-semibold text-text mb-3">📋 Configurações Salvas</h5>
              <div className="space-y-3">
                {installments.map((inst) => (
                  editingInstallment === inst.id ? (
                    // Modo de edição
                    <div key={inst.id} className="bg-blue-50 border-2 border-blue-300 rounded-lg p-3 sm:p-4">
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-text mb-1">
                            Parcelas
                          </label>
                          <div className="px-3 py-2 bg-gray-100 rounded-lg text-sm">
                            {inst.installments_count}x
                          </div>
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-text mb-1">
                            Tipo de Taxa
                          </label>
                          <select
                            value={newInstallment.tax_type}
                            onChange={(e) => setNewInstallment({...newInstallment, tax_type: e.target.value})}
                            disabled={isSaving}
                            className="w-full px-3 py-2 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                          >
                            <option value="%">Percentual (%)</option>
                            <option value="R$">Valor Fixo (R$)</option>
                          </select>
                        </div>
                        <div>
                          <Input
                            type="number"
                            label="Valor da Taxa"
                            value={newInstallment.tax_value}
                            onChange={(e) => setNewInstallment({...newInstallment, tax_value: e.target.value})}
                            placeholder={newInstallment.tax_type === '%' ? 'Ex: 2.5' : 'Ex: 1.50'}
                            disabled={isSaving}
                            step="0.01"
                            min="0"
                          />
                        </div>
                        <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-1">
                          <Button
                            type="button"
                            variant="primary"
                            onClick={handleUpdateInstallment}
                            disabled={isSaving || !newInstallment.tax_value}
                            className="flex-1"
                          >
                            {isSaving ? 'Salvando...' : 'Salvar'}
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={handleCancelEdit}
                            disabled={isSaving}
                            className="flex-1"
                          >
                            Cancelar
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    // Modo de visualização
                    <div key={inst.id} className="bg-gray-50 border border-gray-200 rounded-lg p-3 sm:p-4">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                            <div className="flex-shrink-0">
                              <span className="text-xs text-gray-500 block">Parcelas:</span>
                              <p className="text-sm font-semibold text-text">{inst.installments_count}x</p>
                            </div>
                            <div className="flex-shrink-0">
                              <span className="text-xs text-gray-500 block">Tipo:</span>
                              <p className="text-sm font-semibold text-text">{inst.tax_type === '%' ? 'Percentual (%)' : 'Valor Fixo (R$)'}</p>
                            </div>
                            <div className="flex-shrink-0">
                              <span className="text-xs text-gray-500 block">Taxa:</span>
                              <p className="text-sm font-semibold text-text">
                                {inst.tax_type === '%' 
                                  ? `${parseFloat(inst.tax_value).toFixed(2)}%` 
                                  : `R$ ${parseFloat(inst.tax_value).toFixed(2)}`}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            type="button"
                            onClick={() => handleEditInstallment(inst)}
                            disabled={isSaving}
                            className="px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 rounded-lg transition-colors whitespace-nowrap"
                          >
                            ✏️ Editar
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteInstallment(inst.id)}
                            disabled={isSaving}
                            className="px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors whitespace-nowrap"
                          >
                            🗑️ Excluir
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                ))}
              </div>
            </div>
          )}
          
          {/* Formulário para adicionar nova parcela */}
          <div className="border-t border-gray-200 pt-4">
            <h5 className="text-sm font-semibold text-text mb-3">
              {editingInstallment ? '✏️ Editando Configuração' : '➕ Adicionar Nova Configuração de Parcela'}
            </h5>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <Input
                  type="number"
                  label="Número de Parcelas"
                  value={newInstallment.installments_count}
                  onChange={(e) => setNewInstallment({...newInstallment, installments_count: e.target.value})}
                  placeholder="Ex: 3"
                  disabled={isSaving || editingInstallment !== null}
                  min="2"
                  max="12"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Tipo de Taxa
                </label>
                <select
                  value={newInstallment.tax_type}
                  onChange={(e) => setNewInstallment({...newInstallment, tax_type: e.target.value})}
                  disabled={isSaving}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="%">Percentual (%)</option>
                  <option value="R$">Valor Fixo (R$)</option>
                </select>
              </div>
              
              <div>
                <Input
                  type="number"
                  label="Valor da Taxa"
                  value={newInstallment.tax_value}
                  onChange={(e) => setNewInstallment({...newInstallment, tax_value: e.target.value})}
                  placeholder={newInstallment.tax_type === '%' ? 'Ex: 2.5' : 'Ex: 1.50'}
                  disabled={isSaving}
                  step="0.01"
                  min="0"
                />
              </div>
              
              <div className="flex items-end sm:col-span-2 lg:col-span-1">
                {editingInstallment ? (
                  <div className="w-full flex gap-2">
                    <Button
                      type="button"
                      variant="primary"
                      onClick={handleUpdateInstallment}
                      disabled={isSaving || !newInstallment.tax_value}
                      className="flex-1"
                    >
                      {isSaving ? 'Salvando...' : 'Salvar'}
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={handleCancelEdit}
                      disabled={isSaving}
                      className="flex-1"
                    >
                      Cancelar
                    </Button>
                  </div>
                ) : (
                  <Button
                    type="button"
                    variant="primary"
                    onClick={handleAddInstallment}
                    disabled={isSaving || !newInstallment.installments_count || !newInstallment.tax_value}
                    className="w-full"
                  >
                    Adicionar
                  </Button>
                )}
              </div>
            </div>
            
            <p className="text-xs text-gray-500 mt-2">
              {editingInstallment 
                ? 'Edite os valores da taxa. O número de parcelas não pode ser alterado.'
                : 'Configure as taxas para diferentes números de parcelas. Ex: 2x com 2%, 3x com 3%, etc.'}
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}

export default PaymentConfigSection

