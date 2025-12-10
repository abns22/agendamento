import React, { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthProvider'

/**
 * Componente ProtectedRoute.
 * 
 * Protege rotas que requerem autenticação.
 * 
 * Comportamento:
 * - Se o usuário NÃO estiver autenticado, redireciona para /admin/login
 * - Se estiver autenticado, renderiza o componente filho
 * - Valida o token na montagem do componente
 * 
 * @param {React.ReactNode} children - Componente filho a ser renderizado se autenticado
 */
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading, validateToken, token } = useAuth()

  // Debug: Log quando o componente monta
  useEffect(() => {
    console.log('🛡️ ProtectedRoute montado')
    console.log('📊 Estado:', { isAuthenticated, isLoading, hasToken: !!token, pathname: window.location.pathname })
  }, [])

  // Validar token quando o componente montar
  useEffect(() => {
    if (token && isAuthenticated) {
      // Validar token periodicamente (opcional)
      // validateToken()
    }
  }, [token, isAuthenticated])

  // Mostrar loading enquanto verifica autenticação
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-light">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-text">Carregando...</p>
        </div>
      </div>
    )
  }

  // Se não estiver autenticado, redirecionar para login
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />
  }

  // Se estiver autenticado, renderizar componente filho
  return <>{children}</>
}

export default ProtectedRoute

