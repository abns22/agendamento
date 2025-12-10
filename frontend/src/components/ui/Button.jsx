import React from 'react'

/**
 * Componente de Botão reutilizável (Mobile-First).
 * 
 * Características:
 * - Largura total no mobile (w-full)
 * - Botões grandes com padding otimizado
 * - Alto contraste
 * - Feedback visual claro (hover/active)
 * 
 * @param {string} variant - 'primary' | 'secondary'
 * @param {string} type - 'button' | 'submit' | 'reset'
 * @param {boolean} disabled - Estado desabilitado
 * @param {function} onClick - Handler de clique
 * @param {React.ReactNode} children - Conteúdo do botão
 * @param {string} className - Classes CSS adicionais
 */
const Button = ({
  variant = 'primary',
  type = 'button',
  disabled = false,
  onClick,
  children,
  className = '',
  ...props
}) => {
  // Estilos base (Mobile-First)
  const baseStyles = 'w-full px-6 py-4 text-base font-semibold rounded-xl transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2'
  
  // Variantes
  const variants = {
    primary: 'bg-primary text-white hover:bg-opacity-90 focus:ring-primary shadow-md hover:shadow-lg',
    secondary: 'bg-neutral-light text-text border-2 border-gray-300 hover:bg-gray-50 focus:ring-primary shadow-sm hover:shadow-md'
  }
  
  const combinedClassName = `${baseStyles} ${variants[variant]} ${className}`.trim()
  
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={combinedClassName}
      {...props}
    >
      {children}
    </button>
  )
}

export default Button

