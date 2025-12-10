import React, { useState } from 'react'
import Card from './Card'
import Button from './Button'

/**
 * Componente de Formulário de Login (Mobile-First).
 * 
 * Características:
 * - Usa Card.jsx como container
 * - Campos de email e senha
 * - Botão de submit
 * - Validação básica
 * - Feedback visual
 * 
 * @param {function} onSubmit - Handler de submit (recebe { email, password })
 * @param {boolean} isLoading - Estado de carregamento
 * @param {string} error - Mensagem de erro
 * @param {string} className - Classes CSS adicionais
 */
const LoginCard = ({
  onSubmit,
  isLoading = false,
  error = null,
  className = '',
  ...props
}) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState('')
  
  const handleSubmit = (e) => {
    e.preventDefault()
    setLocalError('')
    
    // Validação básica
    if (!email.trim()) {
      setLocalError('Email é obrigatório')
      return
    }
    
    if (!password.trim()) {
      setLocalError('Senha é obrigatória')
      return
    }
    
    // Validação de email básica
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      setLocalError('Email inválido')
      return
    }
    
    // Chamar handler externo
    if (onSubmit) {
      onSubmit({ email, password })
    }
  }
  
  const displayError = error || localError
  
  return (
    <Card className={className} {...props}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Título */}
        <h2 className="text-2xl font-bold text-text mb-6 text-center">
          Entrar
        </h2>
        
        {/* Mensagem de erro */}
        {displayError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {displayError}
          </div>
        )}
        
        {/* Campo Email */}
        <div className="space-y-2">
          <label htmlFor="email" className="block text-sm font-semibold text-text">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu@email.com"
            disabled={isLoading}
            className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
            autoComplete="email"
          />
        </div>
        
        {/* Campo Senha */}
        <div className="space-y-2">
          <label htmlFor="password" className="block text-sm font-semibold text-text">
            Senha
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            disabled={isLoading}
            className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
            autoComplete="current-password"
          />
        </div>
        
        {/* Botão Submit */}
        <div className="pt-2">
          <Button
            type="submit"
            variant="primary"
            disabled={isLoading}
          >
            {isLoading ? 'Entrando...' : 'Entrar'}
          </Button>
        </div>
      </form>
    </Card>
  )
}

export default LoginCard

