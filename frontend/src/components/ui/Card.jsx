import React from 'react'

/**
 * Componente de Card reutilizável (Mobile-First).
 * 
 * Características:
 * - Largura total no mobile (w-full)
 * - Sombra sutil
 * - Padding otimizado
 * - Bordas arredondadas
 * 
 * @param {React.ReactNode} children - Conteúdo do card
 * @param {string} className - Classes CSS adicionais
 */
const Card = ({ children, className = '', ...props }) => {
  const baseStyles = 'w-full bg-white rounded-xl shadow-sm border border-gray-100 p-4 sm:p-6'
  
  const combinedClassName = `${baseStyles} ${className}`.trim()
  
  return (
    <div className={combinedClassName} {...props}>
      {children}
    </div>
  )
}

export default Card

