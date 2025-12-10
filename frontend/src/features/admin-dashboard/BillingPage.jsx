import React, { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { Card, Button } from '../../components/ui'

/**
 * Página de Gerenciamento de Faturamento (Stripe).
 * 
 * Funcionalidades:
 * - Exibir status da assinatura
 * - Criar checkout session (se inativo)
 * - Gerenciar assinatura via portal (se ativo)
 */
const BillingPage = () => {
  const [status, setStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)

  // Carregar status da assinatura
  useEffect(() => {
    fetchBillingStatus()
  }, [])

  const fetchBillingStatus = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await api.get('/api/v1/admin/billing/status')
      setStatus(response.data)
    } catch (err) {
      console.error('Erro ao carregar status da assinatura:', err)
      setError('Erro ao carregar status da assinatura. Tente novamente.')
    } finally {
      setIsLoading(false)
    }
  }

  // Criar checkout session e redirecionar
  const handleSubscribe = async () => {
    try {
      setIsProcessing(true)
      setError(null)

      const response = await api.post('/api/v1/admin/billing/create-checkout-session', {
        success_url: `${window.location.origin}/admin/billing/success`,
        cancel_url: `${window.location.origin}/admin/billing`
      })

      // Redirecionar para o checkout do Stripe
      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url
      } else {
        throw new Error('URL de checkout não recebida')
      }
    } catch (err) {
      console.error('Erro ao criar checkout session:', err)
      setError(
        err.response?.data?.detail || 
        'Erro ao iniciar processo de assinatura. Tente novamente.'
      )
      setIsProcessing(false)
    }
  }

  // Abrir portal de billing
  const handleManageSubscription = async () => {
    try {
      setIsProcessing(true)
      setError(null)

      const response = await api.post('/api/v1/admin/billing/manage-subscription', {
        return_url: `${window.location.origin}/admin/billing`
      })

      // Redirecionar para o portal do Stripe
      if (response.data.portal_url) {
        window.location.href = response.data.portal_url
      } else {
        throw new Error('URL do portal não recebida')
      }
    } catch (err) {
      console.error('Erro ao abrir portal de billing:', err)
      setError(
        err.response?.data?.detail || 
        'Erro ao abrir portal de gerenciamento. Tente novamente.'
      )
      setIsProcessing(false)
    }
  }

  // Formatar data de expiração
  const formatExpirationDate = (timestamp) => {
    if (!timestamp) return null
    const date = new Date(timestamp * 1000)
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  // Traduzir status do Stripe
  const translateStatus = (stripeStatus) => {
    const translations = {
      'active': 'Ativa',
      'trialing': 'Período de Teste',
      'past_due': 'Pagamento Atrasado',
      'canceled': 'Cancelada',
      'unpaid': 'Não Paga',
      'incomplete': 'Incompleta',
      'incomplete_expired': 'Incompleta Expirada'
    }
    return translations[stripeStatus] || stripeStatus
  }

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-2xl font-bold text-text">Faturamento</h1>
        <p className="text-gray-600 mt-1">
          Gerencie sua assinatura e método de pagamento
        </p>
      </div>

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
          <p className="text-gray-600">Carregando status da assinatura...</p>
        </div>
      )}

      {/* Status da Assinatura */}
      {!isLoading && status && (
        <Card>
          <div className="text-center py-8">
            {/* Ícone e Status */}
            <div className="mb-6">
              {status.is_active ? (
                <>
                  <div className="text-6xl mb-4">✅</div>
                  <h2 className="text-2xl font-bold text-green-600 mb-2">
                    Assinatura Ativa
                  </h2>
                  <p className="text-gray-600">
                    Sua conta está ativa e funcionando normalmente
                  </p>
                </>
              ) : (
                <>
                  <div className="text-6xl mb-4">❌</div>
                  <h2 className="text-2xl font-bold text-red-600 mb-2">
                    Assinatura Inativa
                  </h2>
                  <p className="text-gray-600">
                    Sua conta está inativa. Assine para ativar todos os recursos.
                  </p>
                </>
              )}
            </div>

            {/* Informações Adicionais */}
            {status.has_subscription && status.subscription_status && (
              <div className="mt-6 pt-6 border-t border-gray-200 space-y-2">
                <div className="flex items-center justify-center gap-2">
                  <span className="text-sm font-semibold text-gray-600">Status:</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    status.subscription_status === 'active' || status.subscription_status === 'trialing'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {translateStatus(status.subscription_status)}
                  </span>
                </div>
                
                {status.current_period_end && (
                  <div className="text-sm text-gray-600">
                    <span className="font-semibold">Próxima cobrança:</span>{' '}
                    {formatExpirationDate(status.current_period_end)}
                  </div>
                )}
              </div>
            )}

            {/* Botões de Ação */}
            <div className="mt-8 space-y-3">
              {!status.is_active ? (
                <Button
                  variant="primary"
                  onClick={handleSubscribe}
                  disabled={isProcessing}
                  className="w-full"
                >
                  {isProcessing ? 'Processando...' : 'Assinar e Ativar Conta'}
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  onClick={handleManageSubscription}
                  disabled={isProcessing}
                  className="w-full"
                >
                  {isProcessing ? 'Abrindo...' : 'Gerenciar Pagamento/Assinatura'}
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Informações Adicionais */}
      {!isLoading && status && (
        <Card>
          <h3 className="text-lg font-semibold text-text mb-4">
            Informações da Assinatura
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Possui Assinatura:</span>
              <span className="font-medium">
                {status.has_subscription ? 'Sim' : 'Não'}
              </span>
            </div>
            
            {status.subscription_id && (
              <div className="flex justify-between">
                <span className="text-gray-600">ID da Assinatura:</span>
                <span className="font-mono text-xs">
                  {status.subscription_id.substring(0, 12)}...
                </span>
              </div>
            )}
            
            {status.subscription_status && (
              <div className="flex justify-between">
                <span className="text-gray-600">Status no Stripe:</span>
                <span className="font-medium">
                  {translateStatus(status.subscription_status)}
                </span>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Ajuda */}
      <Card>
        <h3 className="text-lg font-semibold text-text mb-3">
          Precisa de Ajuda?
        </h3>
        <div className="space-y-2 text-sm text-gray-600">
          <p>
            <strong>Assinar:</strong> Clique em "Assinar e Ativar Conta" para iniciar sua assinatura mensal.
            Você será redirecionado para o Stripe para inserir seus dados de pagamento.
          </p>
          <p>
            <strong>Gerenciar:</strong> Clique em "Gerenciar Pagamento/Assinatura" para atualizar seu método
            de pagamento, ver histórico de faturas ou cancelar sua assinatura.
          </p>
        </div>
      </Card>
    </div>
  )
}

export default BillingPage

