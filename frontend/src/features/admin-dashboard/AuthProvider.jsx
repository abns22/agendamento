import React, { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../../utils/api'

/**
 * Contexto de Autenticação JWT.
 * 
 * Gerencia o estado de autenticação, armazenamento do token e dados do usuário.
 */
const AuthContext = createContext(null)

/**
 * Chave para armazenar o token no localStorage
 */
const TOKEN_STORAGE_KEY = 'auth_token'
const USER_STORAGE_KEY = 'auth_user'

/**
 * Provider de Autenticação.
 * 
 * Fornece funções e estado de autenticação para toda a aplicação.
 */
export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Carregar token e usuário do localStorage na inicialização
  useEffect(() => {
    const loadAuthData = () => {
      console.log('🔍 AuthProvider: Carregando dados de autenticação...')
      try {
        const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY)
        const storedUser = localStorage.getItem(USER_STORAGE_KEY)

        console.log('📦 Dados encontrados:', { 
          hasToken: !!storedToken, 
          hasUser: !!storedUser,
          pathname: window.location.pathname
        })

        if (storedToken && storedUser) {
          console.log('✅ Token encontrado, autenticando usuário...')
          setToken(storedToken)
          setUser(JSON.parse(storedUser))
          setIsAuthenticated(true)
          
          // Configurar token no axios para requisições futuras
          api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
        } else {
          console.log('ℹ️ Nenhum token encontrado, usuário não autenticado')
        }
      } catch (error) {
        console.error('❌ Erro ao carregar dados de autenticação:', error)
        // Limpar dados corrompidos
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        localStorage.removeItem(USER_STORAGE_KEY)
      } finally {
        setIsLoading(false)
        console.log('✅ AuthProvider: Carregamento concluído')
      }
    }

    loadAuthData()
  }, [])

  /**
   * Função de login.
   * 
   * Faz POST para /api/v1/auth/login e armazena o token JWT.
   * 
   * @param {string} email - Email do usuário
   * @param {string} password - Senha do usuário
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  const login = async (email, password) => {
    try {
      setIsLoading(true)
      console.log('🔐 Iniciando login...', { email })
      console.log('🌐 URL da API:', api.defaults.baseURL)
      console.log('📡 Fazendo requisição para:', `${api.defaults.baseURL}/api/v1/auth/login`)

      // Fazer requisição de login
      const response = await api.post('/api/v1/auth/login', {
        email,
        password
      }).catch((error) => {
        console.error('❌ Erro na requisição:', error)
        console.error('❌ Detalhes do erro:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status,
          request: error.request,
          config: error.config
        })
        throw error
      })

      console.log('✅ Resposta do login recebida:', response.data)

      const { access_token, refresh_token } = response.data

      if (!access_token) {
        console.error('❌ Token não recebido na resposta:', response.data)
        throw new Error('Token não recebido do servidor')
      }

      console.log('💾 Armazenando token...')

      // Armazenar token no localStorage
      localStorage.setItem(TOKEN_STORAGE_KEY, access_token)
      
      // Armazenar refresh token (opcional, para renovação futura)
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token)
      }

      // Configurar token no axios para requisições futuras
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      console.log('👤 Buscando dados do usuário...')

      // Buscar dados do usuário
      try {
        const userResponse = await api.get('/api/v1/auth/me')
        const userData = userResponse.data

        console.log('✅ Dados do usuário recebidos:', userData)

        // Armazenar dados do usuário
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userData))

        // Atualizar estado
        setToken(access_token)
        setUser(userData)
        setIsAuthenticated(true)

        console.log('✅ Login concluído com sucesso!')
        return { success: true }
      } catch (meError) {
        console.error('❌ Erro ao buscar dados do usuário:', meError)
        // Mesmo se falhar, ainda temos o token, então podemos continuar
        // Criar objeto de usuário básico a partir do token
        const basicUser = {
          email: email,
          // Outros dados serão buscados depois
        }
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(basicUser))
        setToken(access_token)
        setUser(basicUser)
        setIsAuthenticated(true)
        console.warn('⚠️ Login concluído, mas dados do usuário não foram carregados')
        return { success: true }
      }
    } catch (error) {
      console.error('❌ Erro completo ao fazer login:', error)
      console.error('Detalhes do erro:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        request: error.request
      })
      
      let errorMessage = 'Erro ao fazer login. Tente novamente.'
      
      if (error.response) {
        // Erro da API
        console.error('Erro da API:', error.response.status, error.response.data)
        if (error.response.status === 401) {
          errorMessage = 'Email ou senha incorretos'
        } else if (error.response.status === 404) {
          errorMessage = 'Servidor não encontrado. Verifique se o backend está rodando.'
        } else if (error.response.status === 500) {
          errorMessage = 'Erro interno do servidor. Tente novamente mais tarde.'
        } else if (error.response.data?.detail) {
          errorMessage = error.response.data.detail
        }
      } else if (error.request || error.code === 'ECONNABORTED') {
        // Erro de rede ou timeout
        console.error('Erro de rede/timeout:', error)
        if (error.code === 'ECONNABORTED') {
          errorMessage = 'Timeout: O backend não está respondendo. Verifique se está rodando em http://localhost:8000'
        } else {
          errorMessage = 'Erro de conexão. Verifique se o backend está rodando em http://localhost:8000'
        }
      } else {
        // Outro erro
        console.error('Erro desconhecido:', error.message)
        errorMessage = error.message || 'Erro desconhecido ao fazer login'
      }

      return { success: false, error: errorMessage }
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Função de logout.
   * 
   * Limpa o token e dados do usuário do localStorage e estado.
   */
  const logout = () => {
    // Remover do localStorage
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
    localStorage.removeItem('refresh_token')

    // Remover token do axios
    delete api.defaults.headers.common['Authorization']

    // Limpar estado
    setToken(null)
    setUser(null)
    setIsAuthenticated(false)
  }

  /**
   * Verifica se o token está válido.
   * 
   * Faz uma requisição para /api/v1/auth/me para validar o token.
   * 
   * @returns {Promise<boolean>}
   */
  const validateToken = async () => {
    if (!token) {
      return false
    }

    try {
      const response = await api.get('/api/v1/auth/me')
      
      if (response.data) {
        // Atualizar dados do usuário
        setUser(response.data)
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(response.data))
        return true
      }
      
      return false
    } catch (error) {
      // Token inválido ou expirado
      if (error.response?.status === 401) {
        logout()
      }
      return false
    }
  }

  const value = {
    token,
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    validateToken
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Hook para usar o contexto de autenticação.
 * 
 * @returns {Object} Objeto com token, user, isLoading, isAuthenticated, login, logout, validateToken
 */
export const useAuth = () => {
  const context = useContext(AuthContext)
  
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider')
  }
  
  return context
}

export default AuthContext

