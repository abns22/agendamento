import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { Card, Modal, Button, Input } from '../../components/ui'
import { api, formatCurrency } from '../../utils/api'
import ClientQuickRegisterModal from './ClientQuickRegisterModal'
import BirthdaysSection from './BirthdaysSection'
import UpcomingAppointmentsWidget from './UpcomingAppointmentsWidget'

/**
 * Página de Dashboard Administrativo.
 * 
 * Página inicial do painel administrativo após login.
 */
const DashboardPage = () => {
  const { user } = useAuth()
  const [stats, setStats] = useState({
    appointments_today: 0,
    active_services: 0,
    pending_appointments: 0
  })
  const [summary, setSummary] = useState({
    faturamento_total: 0,
    ticket_medio: 0,
    servico_mais_procurado_id: null,
    total_descontos: 0,
    total_appointments_finalizados: 0,
    periodo_inicio: null,
    periodo_fim: null
  })
  const [mostPopularServiceName, setMostPopularServiceName] = useState(null)
  const [birthdaysCount, setBirthdaysCount] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingSummary, setIsLoadingSummary] = useState(true)
  const [error, setError] = useState(null)
  const [isClientModalOpen, setIsClientModalOpen] = useState(false)

  // Buscar estatísticas do dashboard
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const response = await api.get('/api/v1/admin/dashboard/stats')
        setStats(response.data)
      } catch (err) {
        console.error('Erro ao carregar estatísticas:', err)
        setError('Erro ao carregar estatísticas')
      } finally {
        setIsLoading(false)
      }
    }

    fetchStats()
  }, [])

  // Buscar resumo financeiro do dashboard
  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setIsLoadingSummary(true)
        const response = await api.get('/api/v1/admin/dashboard/summary')
        setSummary(response.data)
        
        // Buscar nome do serviço mais procurado se houver ID
        if (response.data.servico_mais_procurado_id) {
          try {
            const serviceResponse = await api.get(`/api/v1/admin/services/${response.data.servico_mais_procurado_id}`)
            setMostPopularServiceName(serviceResponse.data.name)
          } catch (err) {
            console.error('Erro ao buscar nome do serviço:', err)
          }
        }
      } catch (err) {
        console.error('Erro ao carregar resumo financeiro:', err)
      } finally {
        setIsLoadingSummary(false)
      }
    }

    fetchSummary()
  }, [])

  // Buscar contagem de aniversariantes
  useEffect(() => {
    const fetchBirthdaysCount = async () => {
      try {
        const response = await api.get('/api/v1/admin/reports/birthdays')
        setBirthdaysCount(response.data?.length || 0)
      } catch (err) {
        console.error('Erro ao carregar aniversariantes:', err)
      }
    }

    fetchBirthdaysCount()
  }, [])

  return (
    <div className="space-y-6">
      {/* Título da Página */}
      <div>
        <h1 className="text-2xl font-bold text-text">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Bem-vindo de volta, {user?.email || 'Usuário'}!
        </p>
      </div>

      {/* Cards de Indicadores Financeiros - Design Minimalista */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Card: Faturamento */}
        <Card className="bg-white border-gray-200 py-3 px-4">
          <div className="flex items-center gap-3">
            <div className="text-2xl">💰</div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-500 font-medium mb-0.5">Faturamento (mês)</p>
              <p className="text-lg font-semibold text-gray-800 truncate">
                {isLoadingSummary ? '...' : formatCurrency(parseFloat(summary.faturamento_total || 0))}
              </p>
            </div>
          </div>
        </Card>

        {/* Card: Agendamentos Finalizados */}
        <Card className="bg-white border-gray-200 py-3 px-4">
          <div className="flex items-center gap-3">
            <div className="text-2xl">📅</div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-500 font-medium mb-0.5">Agendamentos (mês)</p>
              <p className="text-lg font-semibold text-gray-800">
                {isLoadingSummary ? '...' : summary.total_appointments_finalizados || 0}
              </p>
            </div>
          </div>
        </Card>

        {/* Card: Ticket Médio */}
        <Card className="bg-white border-gray-200 py-3 px-4">
          <div className="flex items-center gap-3">
            <div className="text-2xl">📊</div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-500 font-medium mb-0.5">Ticket Médio</p>
              <p className="text-lg font-semibold text-gray-800 truncate">
                {isLoadingSummary ? '...' : formatCurrency(parseFloat(summary.ticket_medio || 0))}
              </p>
            </div>
          </div>
        </Card>

        {/* Card: Aniversariantes do Mês */}
        <Card className="bg-white border-gray-200 py-3 px-4">
          <div className="flex items-center gap-3">
            <div className="text-2xl">🎂</div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-500 font-medium mb-0.5">Aniversariantes</p>
              <p className="text-lg font-semibold text-gray-800">
                {birthdaysCount}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Widget de Próximos Agendamentos */}
      <UpcomingAppointmentsWidget />

      {/* Dica de Promoção (quando ticket médio estiver baixo) */}
      {!isLoadingSummary && summary.ticket_medio > 0 && summary.ticket_medio < 100 && mostPopularServiceName && (
        <Card className="bg-yellow-50 border-yellow-200">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 text-2xl">💡</div>
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900 mb-1">
                Dica de Negócio
              </h3>
              <p className="text-sm text-yellow-800">
                Que tal criar uma promoção para o serviço <strong>{mostPopularServiceName}</strong>? 
                Isso pode ajudar a aumentar seu ticket médio!
              </p>
            </div>
            <Link 
              to="/admin/servicos" 
              className="flex-shrink-0 text-yellow-700 hover:text-yellow-900 font-semibold text-sm underline"
            >
              Criar Promoção →
            </Link>
          </div>
        </Card>
      )}

      {/* Cards de Resumo Adicional */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Agendamentos Hoje</p>
              <p className="text-2xl font-bold text-text mt-1">
                {isLoading ? '...' : stats.appointments_today}
              </p>
            </div>
            <div className="text-4xl">📅</div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Serviços Ativos</p>
              <p className="text-2xl font-bold text-text mt-1">
                {isLoading ? '...' : stats.active_services}
              </p>
            </div>
            <div className="text-4xl">⚙️</div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Pendentes</p>
              <p className="text-2xl font-bold text-text mt-1">
                {isLoading ? '...' : stats.pending_appointments}
              </p>
            </div>
            <div className="text-4xl">⏳</div>
          </div>
        </Card>
      </div>

      {/* Seção de Gestão de Clientes - Card de Cadastro Rápido */}
      <div>
        <h2 className="text-xl font-semibold text-text mb-4">
          Gestão de Clientes
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Card: Cadastrar Cliente */}
          <button
            onClick={() => setIsClientModalOpen(true)}
            className="text-left"
          >
            <Card className="cursor-pointer hover:shadow-lg transition-shadow h-full">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-text mb-1">
                    Cadastrar Cliente
                  </h3>
                  <p className="text-sm text-gray-600">
                    Adicione um novo cliente ao seu cadastro
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </div>
              </div>
            </Card>
          </button>
        </div>
      </div>

      {/* Seção de Aniversariantes do Mês */}
      <BirthdaysSection />

      {/* Seção de Gestão Financeira - Cards de Acesso Rápido */}
      <div>
        <h2 className="text-xl font-semibold text-text mb-4">
          Gestão Financeira
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Card: Caixa e Relatórios */}
          <Link to="/admin/caixa" className="block">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow h-full">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 bg-primary bg-opacity-10 rounded-lg flex items-center justify-center">
                    <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-text mb-1">
                    Caixa e Relatórios
                  </h3>
                  <p className="text-sm text-gray-600">
                    Visualize faturamento diário/mensal, lucro e despesas
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Card>
          </Link>

          {/* Card: Contas a Receber */}
          <Link to="/admin/devedores" className="block">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow h-full">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 bg-orange-100 rounded-lg flex items-center justify-center">
                    <svg className="w-8 h-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-text mb-1">
                    Contas a Receber
                  </h3>
                  <p className="text-sm text-gray-600">
                    Gerencie devedores e dê baixa em pagamentos pendentes
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Card>
          </Link>

          {/* Card: Inventário */}
          <Link to="/admin/inventario" className="block">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow h-full">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 bg-purple-100 rounded-lg flex items-center justify-center">
                    <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-text mb-1">
                    Inventário
                  </h3>
                  <p className="text-sm text-gray-600">
                    Controle de produtos, estoque e custos internos
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Card>
          </Link>
        </div>
      </div>

      {/* Área de Conteúdo Principal */}
      <Card>
        <h2 className="text-xl font-semibold text-text mb-4">
          Área Administrativa
        </h2>
        <p className="text-gray-600 mb-4">
          Esta é a área administrativa do sistema. Aqui você poderá gerenciar:
        </p>
        <ul className="list-disc list-inside space-y-2 text-gray-600">
          <li>Agenda - Visualizar e gerenciar agendamentos</li>
          <li>Serviços - Criar e editar serviços oferecidos</li>
          <li>Configurações - Personalizar seu estúdio</li>
        </ul>
      </Card>

      {/* Modal de Cadastro Rápido de Cliente */}
      <ClientQuickRegisterModal
        isOpen={isClientModalOpen}
        onClose={() => setIsClientModalOpen(false)}
        onSuccess={() => {
          setIsClientModalOpen(false)
          // Recarregar aniversariantes se necessário
        }}
      />
    </div>
  )
}

export default DashboardPage

