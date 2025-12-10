import React from 'react'

/**
 * Componente de Pílula de Horário (Mobile-First).
 * 
 * Características:
 * - Exibe um slot de horário (ex: "14:30")
 * - Estilizado como pílula
 * - Feedback visual claro (hover/clique)
 * - Grid responsivo (3-4 colunas no mobile)
 * 
 * @param {string} time - Horário no formato "HH:MM"
 * @param {boolean} selected - Estado selecionado
 * @param {boolean} disabled - Estado desabilitado
 * @param {function} onClick - Handler de clique
 * @param {string} className - Classes CSS adicionais
 */
const TimePill = ({
  time,
  selected = false,
  disabled = false,
  onClick,
  className = '',
  ...props
}) => {
  const baseStyles = 'px-4 py-2.5 text-sm font-semibold rounded-full transition-all duration-200 active:scale-95 focus:outline-none focus:ring-2 focus:ring-offset-1'
  
  // Estados
  let stateStyles = ''
  if (disabled) {
    stateStyles = 'bg-gray-100 text-gray-400 cursor-not-allowed'
  } else if (selected) {
    stateStyles = 'bg-primary text-white shadow-md hover:bg-opacity-90 focus:ring-primary'
  } else {
    stateStyles = 'bg-white text-text border-2 border-gray-300 hover:border-primary hover:text-primary hover:bg-primary/5 focus:ring-primary'
  }
  
  const combinedClassName = `${baseStyles} ${stateStyles} ${className}`.trim()
  
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={combinedClassName}
      {...props}
    >
      {time}
    </button>
  )
}

/**
 * Container de Grid para múltiplas pílulas de horário.
 * 
 * Características:
 * - Grid responsivo (3 colunas no mobile, 4 em telas maiores)
 * - Gap otimizado para mobile
 * 
 * @param {React.ReactNode} children - TimePill components
 * @param {string} className - Classes CSS adicionais
 */
export const TimePillGrid = ({ children, className = '', ...props }) => {
  const baseStyles = 'grid grid-cols-3 sm:grid-cols-4 gap-2 sm:gap-3 w-full'
  
  const combinedClassName = `${baseStyles} ${className}`.trim()
  
  return (
    <div className={combinedClassName} {...props}>
      {children}
    </div>
  )
}

export default TimePill

