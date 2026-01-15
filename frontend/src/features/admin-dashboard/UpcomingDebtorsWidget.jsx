import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card } from '../../components/ui'
import { api, formatCurrency } from '../../utils/api'

/**
 * Widget de Contas a Receber para o Dashboard.
 * 
 * Exibe uma lista minimalista de contas a receber vencidas e que vão vencer nos próximos 3 dias.
 */
const UpcomingDebtorsWidget = () => {
  const navigate = useNavigate()
  const [debtorsData, setDebtorsData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  // Buscar contas a receber
  useEffect(() => {
    const fetchUpcomingDebtors = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const response = await api.get('/api/v1/admin/dashboard/upcoming-debtors')
        setDebtorsData(response.data)
      } catch (err) {
        console.error('Erro ao carregar contas a receber:', err)
        setError('Erro ao carregar contas a receber')
      } finally {
        setIsLoading(false)
      }
    }

    fetchUpcomingDebtors()
  }, [])

  // Navegar para a página de devedores ou agendamento
  const handleDebtorClick = (debtor) => {
    // Se tiver appointment_id, navegar para o agendamento
    if (debtor.appointment_id) {
      navigate(`/admin/agenda?appointment_id=${debtor.appointment_id}`)
    } else {
      // Caso contrário, navegar para a página de devedores
      navigate('/admin/devedores')
    }
  }

  // Calcular total de contas
  const totalDebtors = (debtorsData?.overdue?.length || 0) + (debtorsData?.upcoming?.length || 0)

  return (
    <Card className="bg-white border-gray-200">
      <div className="p-3">
        {/* Título */}
        <h3 className="text-base font-semibold text-gray-800 mb-3">
          Contas a Receber
        </h3>

        {/* Conteúdo */}
        {isLoading ? (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
          </div>
        ) : error ? (
          <div className="text-center py-4 text-red-600 text-sm">
            {error}
          </div>
        ) : totalDebtors === 0 ? (
          <div className="text-center py-4 text-gray-500 text-sm">
            Nenhuma conta a receber vencida ou próxima.
          </div>
        ) : (
          <div className="space-y-2">
            {/* Contas Vencidas */}
            {debtorsData.overdue && debtorsData.overdue.length > 0 && (
              <div className="space-y-1.5">
                {debtorsData.overdue.map((debtor) => (
                  <button
                    key={debtor.id}
                    onClick={() => handleDebtorClick(debtor)}
                    className="w-full text-left p-2 rounded-lg border border-red-200 bg-red-50 hover:border-red-300 hover:bg-red-100 transition-all duration-200"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 text-sm truncate">
                          {debtor.client_name}
                        </p>
                        <p className="text-xs text-red-600">
                          {debtor.due_date_label}
                        </p>
                      </div>
                      <div className="flex-shrink-0">
                        <p className="text-sm font-semibold text-red-700 whitespace-nowrap">
                          {formatCurrency(parseFloat(debtor.value_due))}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Contas Próximas */}
            {debtorsData.upcoming && debtorsData.upcoming.length > 0 && (
              <div className="space-y-1.5">
                {debtorsData.upcoming.map((debtor) => (
                  <button
                    key={debtor.id}
                    onClick={() => handleDebtorClick(debtor)}
                    className="w-full text-left p-2 rounded-lg border border-orange-200 bg-orange-50 hover:border-orange-300 hover:bg-orange-100 transition-all duration-200"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 text-sm truncate">
                          {debtor.client_name}
                        </p>
                        <p className="text-xs text-orange-600">
                          {debtor.due_date_label}
                        </p>
                      </div>
                      <div className="flex-shrink-0">
                        <p className="text-sm font-semibold text-orange-700 whitespace-nowrap">
                          {formatCurrency(parseFloat(debtor.value_due))}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

export default UpcomingDebtorsWidget
