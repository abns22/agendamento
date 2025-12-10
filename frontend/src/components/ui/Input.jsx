import React from 'react'

/**
 * Componente de Input reutilizável (Mobile-First).
 * 
 * Características:
 * - Largura total no mobile (w-full)
 * - Padding otimizado para toque
 * - Alto contraste
 * - Feedback visual claro (focus)
 * 
 * @param {string} type - Tipo do input (text, email, tel, time, etc.)
 * @param {string} label - Label do campo
 * @param {string} value - Valor do input
 * @param {function} onChange - Handler de mudança
 * @param {string} placeholder - Placeholder do input
 * @param {boolean} disabled - Estado desabilitado
 * @param {string} error - Mensagem de erro
 * @param {string} className - Classes CSS adicionais
 * @param {object} ...props - Outras props do input HTML
 */
const Input = ({
  type = 'text',
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
  error = null,
  className = '',
  ...props
}) => {
  const inputId = props.id || `input-${label?.toLowerCase().replace(/\s+/g, '-') || 'field'}`
  
  return (
    <div className={`space-y-2 ${className}`}>
      {label && (
        <label 
          htmlFor={inputId} 
          className="block text-sm font-semibold text-text"
        >
          {label}
        </label>
      )}
      
      <input
        id={inputId}
        type={type}
        value={value || ''}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full px-4 py-3 rounded-lg border-2 transition-all duration-200 ${
          error
            ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-primary focus:ring-primary'
        } focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-500`}
        {...props}
      />
      
      {error && (
        <p className="text-sm text-red-600 flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </p>
      )}
    </div>
  )
}

export default Input

