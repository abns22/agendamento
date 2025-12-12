import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { LoginCard } from '../../components/ui'

/**
 * Página de Login para Administradores.
 * 
 * Características:
 * - Usa LoginCard component
 * - Integra com AuthContext
 * - Redireciona para dashboard em caso de sucesso
 * - Redireciona para dashboard se já estiver autenticado
 * - Feedback visual de erros e loading
 */
const LoginPage = () => {
  const navigate = useNavigate()
  const { login, isLoading, isAuthenticated } = useAuth()
  const [error, setError] = useState(null)

  // Debug: Log quando o componente monta
  useEffect(() => {
    console.log('🔐 LoginPage montado')
    console.log('📊 Estado:', { isAuthenticated, isLoading, pathname: window.location.pathname })
  }, [])

  // Se já estiver autenticado, redirecionar baseado no role
  useEffect(() => {
    console.log('🔄 Verificando autenticação...', { isAuthenticated, isLoading })
    if (isAuthenticated && !isLoading) {
      // Verificar role do usuário
      const storedUser = localStorage.getItem('auth_user')
      if (storedUser) {
        try {
          const userData = JSON.parse(storedUser)
          if (userData.role === 'SUPER_ADMIN') {
            console.log('👑 Super Admin detectado, redirecionando para página exclusiva...')
            navigate('/admin/super-admin', { replace: true })
          } else {
            console.log('✅ Usuário já autenticado, redirecionando para dashboard...')
            navigate('/admin/dashboard', { replace: true })
          }
        } catch (e) {
          console.error('Erro ao parsear dados do usuário:', e)
          navigate('/admin/dashboard', { replace: true })
        }
      } else {
        navigate('/admin/dashboard', { replace: true })
      }
    }
  }, [isAuthenticated, isLoading, navigate])

  /**
   * Handler de submit do formulário de login.
   * 
   * @param {Object} credentials - { email, password }
   */
  const handleLogin = async (credentials) => {
    setError(null)

    const result = await login(credentials.email, credentials.password)

    if (result.success) {
      // Verificar role e redirecionar adequadamente
      const storedUser = localStorage.getItem('auth_user')
      if (storedUser) {
        try {
          const userData = JSON.parse(storedUser)
          if (userData.role === 'SUPER_ADMIN') {
            navigate('/admin/super-admin', { replace: true })
          } else {
            navigate('/admin/dashboard', { replace: true })
          }
        } catch (e) {
          navigate('/admin/dashboard', { replace: true })
        }
      } else {
        navigate('/admin/dashboard', { replace: true })
      }
    } else {
      // Exibir erro
      setError(result.error || 'Erro ao fazer login')
    }
  }

  // Mostrar loading enquanto verifica autenticação
  if (isLoading && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-light">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-text">Verificando autenticação...</p>
        </div>
      </div>
    )
  }

  // Se já estiver autenticado, não renderizar (será redirecionado)
  if (isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-light p-4">
      <div className="w-full max-w-md">
        {/* Logo Synkhro */}
        <div className="text-center mb-6">
          <img 
            src="/logo.png" 
            alt="Synkhro Logo" 
            className="h-20 mx-auto mb-4 object-contain"
          />
          <p className="text-gray-600 text-sm">
            Área Administrativa
          </p>
        </div>
        
        <LoginCard
          onSubmit={handleLogin}
          isLoading={isLoading}
          error={error}
        />
      </div>
    </div>
  )
}

export default LoginPage

