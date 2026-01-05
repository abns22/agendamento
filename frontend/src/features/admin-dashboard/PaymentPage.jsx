import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../utils/api'
import { Card, Button } from '../../components/ui'

/**
 * Página de Pagamento Obrigatório.
 * 
 * Exibida quando o tenant está com assinatura pendente ou expirada.
 * Permite que o usuário realize o pagamento via Stripe Checkout.
 */
const PaymentPage = () => {
  const navigate = useNavigate()
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)

  const handlePayNow = async () => {
    try {
      setIsProcessing(true)
      setError(null)

      // Chamar endpoint para criar checkout session
      const response = await api.post('/api/v1/admin/billing/create-checkout-session', {
        success_url: `${window.location.origin}/admin/billing/success`,
        cancel_url: `${window.location.origin}/admin/pagamento`
      })

      // Redirecionar para a URL do Stripe Checkout
      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url
      } else {
        throw new Error('URL de checkout não recebida')
      }
    } catch (err) {
      console.error('Erro ao criar checkout session:', err)
      setError(
        err.response?.data?.detail || 
        'Erro ao iniciar processo de pagamento. Tente novamente.'
      )
      setIsProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/10 via-white to-primary/5 flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-6 sm:p-8 text-center">
        {/* Ícone de alerta */}
        <div className="mb-6 flex justify-center">
          <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center">
            <svg 
              className="w-12 h-12 text-yellow-600" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
              />
            </svg>
          </div>
        </div>

        {/* Título */}
        <h1 className="text-2xl sm:text-3xl font-bold text-text mb-4">
          Assinatura Pendente
        </h1>

        {/* Mensagem */}
        <p className="text-gray-600 mb-8 text-base sm:text-lg leading-relaxed">
          Sua assinatura está pendente ou expirou. Para continuar utilizando o Synkhro, 
          realize o pagamento da mensalidade.
        </p>

        {/* Mensagem de erro */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Botão de pagamento */}
        <Button
          onClick={handlePayNow}
          disabled={isProcessing}
          variant="primary"
          className="w-full py-3 text-lg font-semibold"
        >
          {isProcessing ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processando...
            </>
          ) : (
            '💳 Pagar Agora'
          )}
        </Button>

        {/* Informação adicional */}
        <p className="mt-6 text-sm text-gray-500">
          Você será redirecionado para uma página segura do Stripe para realizar o pagamento.
        </p>
      </Card>
    </div>
  )
}

export default PaymentPage

