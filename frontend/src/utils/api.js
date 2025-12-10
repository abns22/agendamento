/**
 * Configuração e utilitários para chamadas de API.
 */
import axios from 'axios'

// URL base da API (ajustar conforme ambiente)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

console.log('🔧 Configuração da API:', {
  VITE_API_URL: import.meta.env.VITE_API_URL,
  API_BASE_URL: API_BASE_URL,
  env: import.meta.env
})

// Instância do axios configurada
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 segundos de timeout (aumentado para debug)
})

// Interceptor para adicionar token JWT em todas as requisições
api.interceptors.request.use(
  (config) => {
    // Buscar token do localStorage
    const token = localStorage.getItem('auth_token')
    
    if (token) {
      // Adicionar token no header Authorization
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Se for FormData, remover Content-Type para o browser definir automaticamente
    // (incluindo o boundary necessário para multipart/form-data)
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor para tratar erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Se receber 401 (Unauthorized), token pode estar inválido ou expirado
    if (error.response?.status === 401) {
      // Remover token inválido
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      localStorage.removeItem('refresh_token')
      
      // Redirecionar para login se não estiver na página de login
      // Usar window.location apenas se necessário (evitar loop)
      const currentPath = window.location.pathname
      if (currentPath !== '/admin/login' && !currentPath.startsWith('/admin/login')) {
        // Usar replace para evitar adicionar ao histórico
        window.location.replace('/admin/login')
      }
    }
    
    return Promise.reject(error)
  }
)

/**
 * Formata valor monetário para exibição.
 */
export const formatCurrency = (value) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

/**
 * Formata duração em minutos para texto legível.
 */
export const formatDuration = (minutes) => {
  if (minutes < 60) {
    return `${minutes} min`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) {
    return `${hours}h`
  }
  return `${hours}h ${mins}min`
}

