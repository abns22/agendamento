import React, { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { api } from '../../utils/api'
import Footer from '../../components/Footer'

/**
 * Layout Principal do Dashboard Administrativo (Mobile-First).
 * 
 * Características:
 * - Sidebar para desktop (telas >= 640px)
 * - Bottom Nav para mobile (telas < 640px)
 * - Cabeçalho com nome do estúdio
 * - Integração com rotas protegidas
 * - Responsivo e otimizado para mobile
 */
const DashboardLayout = ({ children }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [tenantName, setTenantName] = useState('Estúdio')
  const [isLoadingTenant, setIsLoadingTenant] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Buscar dados do tenant
  useEffect(() => {
    const fetchTenantData = async () => {
      if (!user?.tenant_id) {
        setIsLoadingTenant(false)
        return
      }

      try {
        // Buscar dados do tenant atual via endpoint
        const response = await api.get('/api/v1/admin/tenant')
        const tenantData = response.data
        
        // Formatar slug como nome do estúdio
        // Ex: "estudio-bella" → "Estúdio Bella"
        if (tenantData.slug) {
          const formattedName = tenantData.slug
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ')
          setTenantName(formattedName)
        } else {
          setTenantName('Meu Estúdio')
        }
      } catch (error) {
        console.error('Erro ao buscar dados do tenant:', error)
        // Fallback: usar email ou slug do usuário
        if (user?.email) {
          const emailName = user.email.split('@')[0]
          setTenantName(emailName.charAt(0).toUpperCase() + emailName.slice(1))
        } else {
          setTenantName('Estúdio')
        }
      } finally {
        setIsLoadingTenant(false)
      }
    }

    fetchTenantData()
  }, [user])

  // Fechar sidebar ao mudar de rota (mobile)
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Verificar se rota está ativa
  const isActiveRoute = (path) => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  // Verificar se é Super Admin
  const isSuperAdmin = () => {
    try {
      const storedUser = localStorage.getItem('auth_user')
      if (storedUser) {
        const userData = JSON.parse(storedUser)
        return userData.role === 'SUPER_ADMIN'
      }
    } catch (e) {
      console.error('Erro ao verificar role:', e)
    }
    return false
  }

  // Itens de navegação baseados no role
  const baseNavItems = [
    {
      path: '/admin/dashboard',
      label: 'Dashboard',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
      mobileIcon: '🏠',
      show: true
    },
    {
      path: '/admin/agenda',
      label: 'Agenda',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      mobileIcon: '📅',
      show: !isSuperAdmin() // Mostrar para todos exceto Super Admin
    },
    {
      path: '/admin/servicos',
      label: 'Serviços',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
      ),
      mobileIcon: '⚙️',
      show: !isSuperAdmin() // Mostrar para todos exceto Super Admin
    },
    {
      path: '/admin/configuracoes',
      label: 'Configurações',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
      mobileIcon: '🔧',
      show: !isSuperAdmin() // Mostrar para todos exceto Super Admin
    },
    {
      path: '/admin/billing',
      label: 'Faturamento',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      ),
      mobileIcon: '💳',
      show: !isSuperAdmin() // Ocultar para Super Admin
    },
    {
      path: '/admin/caixa',
      label: 'Caixa',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      ),
      mobileIcon: '💰',
      show: !isSuperAdmin() // Ocultar para Super Admin
    },
    {
      path: '/admin/devedores',
      label: 'Devedores',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      mobileIcon: '💸',
      show: !isSuperAdmin() // Ocultar para Super Admin
    },
    {
      path: '/admin/super-admin',
      label: 'Criar Estúdio',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      ),
      mobileIcon: '👑',
      show: isSuperAdmin() // Mostrar apenas para Super Admin
    }
  ]

  // Filtrar itens baseado no role
  // Se `show` não estiver definido, assume `true` (mostrar por padrão)
  const navItems = baseNavItems.filter(item => item.show !== false)
  
  // Itens para o Bottom Nav (mobile) - apenas os essenciais
  // Remover Caixa e Devedores do Bottom Nav, mas manter no sidebar desktop
  const bottomNavItems = navItems.filter(item => {
    // Manter apenas Dashboard, Agenda, Serviços e Configurações no Bottom Nav
    const essentialPaths = [
      '/admin/dashboard',
      '/admin/agenda',
      '/admin/servicos',
      '/admin/configuracoes'
    ]
    return essentialPaths.includes(item.path)
  })

  return (
    <div className="min-h-screen bg-neutral-light flex flex-col">
      {/* Cabeçalho */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-40">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo e Nome do Estúdio */}
            <div className="flex items-center space-x-3">
              {/* Botão menu mobile (apenas em telas pequenas) */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="sm:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="Toggle menu"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              
              {/* Logo Synkhro */}
              <img 
                src="/logo.png" 
                alt="Synkhro" 
                className="h-10 w-auto object-contain hidden sm:block"
              />
              
              <div>
                <h1 className="text-lg font-bold text-text">
                  {isLoadingTenant ? 'Carregando...' : tenantName}
                </h1>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
            </div>

            {/* Botão Logout */}
            <button
              onClick={() => {
                logout()
                navigate('/admin/login')
              }}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-primary hover:bg-gray-50 rounded-lg transition-colors"
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar (Desktop) - Oculto em mobile */}
        <aside className="hidden sm:flex sm:flex-col sm:w-64 bg-white border-r border-gray-200">
          <nav className="flex-1 px-4 py-6 space-y-2">
            {navItems.map((item) => {
              const isActive = isActiveRoute(item.path)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <span className={isActive ? 'text-white' : 'text-gray-500'}>
                    {item.icon}
                  </span>
                  <span className="font-medium">{item.label}</span>
                </Link>
              )
            })}
          </nav>
        </aside>

        {/* Sidebar Mobile (Overlay) */}
        {sidebarOpen && (
          <>
            {/* Overlay */}
            <div
              className="fixed inset-0 bg-black bg-opacity-50 z-40 sm:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            {/* Sidebar */}
            <aside className="fixed inset-y-0 left-0 w-64 bg-white shadow-lg z-50 sm:hidden">
              <div className="flex flex-col h-full">
                <div className="flex items-center justify-between p-4 border-b border-gray-200">
                  <h2 className="text-lg font-bold text-text">Menu</h2>
                  <button
                    onClick={() => setSidebarOpen(false)}
                    className="p-2 rounded-lg text-gray-600 hover:bg-gray-100"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
                  {navItems.map((item) => {
                    const isActive = isActiveRoute(item.path)
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={() => setSidebarOpen(false)}
                        className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                          isActive
                            ? 'bg-primary text-white'
                            : 'text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        <span className={isActive ? 'text-white' : 'text-gray-500'}>
                          {item.icon}
                        </span>
                        <span className="font-medium">{item.label}</span>
                      </Link>
                    )
                  })}
                </nav>
              </div>
            </aside>
          </>
        )}

        {/* Conteúdo Principal */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 sm:p-6 lg:p-8">
            {children}
          </div>
        </main>
        
        {/* Footer */}
        <Footer />
      </div>

      {/* Barra de Navegação Inferior (Mobile) - Apenas em telas < 640px */}
      <nav className="sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-30">
        <div className="flex justify-around items-center h-16 px-2">
          {bottomNavItems.map((item) => {
            const isActive = isActiveRoute(item.path)
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
                  isActive ? 'text-primary' : 'text-gray-600'
                }`}
              >
                <span className="text-2xl mb-1">{item.mobileIcon}</span>
                <span className="text-xs font-medium">{item.label}</span>
              </Link>
            )
          })}
        </div>
      </nav>

      {/* Padding inferior para mobile (evitar sobreposição com bottom nav) */}
      <div className="sm:hidden h-16" />
    </div>
  )
}

export default DashboardLayout

