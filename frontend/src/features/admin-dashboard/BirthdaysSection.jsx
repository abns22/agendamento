import React, { useState, useEffect } from 'react'
import { Card } from '../../components/ui'
import { api } from '../../utils/api'

/**
 * Componente de Aniversariantes do Mês.
 * 
 * Exibe os clientes que fazem aniversário no mês atual.
 */
const BirthdaysSection = () => {
  const [birthdays, setBirthdays] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchBirthdays()
  }, [])

  const fetchBirthdays = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await api.get('/api/v1/admin/reports/birthdays')
      setBirthdays(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar aniversariantes:', err)
      setError('Erro ao carregar aniversariantes')
    } finally {
      setIsLoading(false)
    }
  }

  const getMonthName = () => {
    const months = [
      'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    return months[new Date().getMonth()]
  }

  const formatPhone = (phone) => {
    // Formatar telefone brasileiro: (11) 98765-4321
    if (phone.length === 11) {
      return `(${phone.slice(0, 2)}) ${phone.slice(2, 7)}-${phone.slice(7)}`
    }
    return phone
  }

  if (isLoading) {
    return (
      <div>
        <h2 className="text-xl font-semibold text-text mb-4">
          Aniversariantes do Mês
        </h2>
        <Card>
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <p className="ml-2 text-gray-600">Carregando aniversariantes...</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-text mb-4">
        🎂 Aniversariantes de {getMonthName()}
      </h2>
      
      {error && (
        <Card>
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        </Card>
      )}

      {!error && birthdays.length === 0 && (
        <Card>
          <div className="text-center py-8">
            <div className="text-4xl mb-3">🎈</div>
            <p className="text-gray-600">
              Nenhum aniversariante este mês
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Cadastre a data de nascimento dos clientes para ver os aniversários aqui
            </p>
          </div>
        </Card>
      )}

      {!error && birthdays.length > 0 && (
        <Card>
          <div className="space-y-3">
            {birthdays.map((client) => (
              <div
                key={client.id}
                className="flex items-center gap-2 sm:gap-3 p-3 bg-gradient-to-r from-pink-50 to-purple-50 rounded-lg border border-pink-200 overflow-hidden"
              >
                <div className="flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 bg-pink-200 rounded-full flex items-center justify-center text-pink-700 font-bold text-base sm:text-lg">
                  {client.day_of_month}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-text truncate">
                    {client.name}
                  </h3>
                  <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 text-xs sm:text-sm text-gray-600 mt-1">
                    {client.phone_number && (
                      <span className="flex items-center gap-1 truncate">
                        <svg className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                        </svg>
                        <span className="truncate">{formatPhone(client.phone_number)}</span>
                      </span>
                    )}
                    {client.email && (
                      <span className="flex items-center gap-1 truncate">
                        <svg className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                        <span className="truncate">{client.email}</span>
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex-shrink-0 text-lg sm:text-2xl">🎂</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

export default BirthdaysSection

