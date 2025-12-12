import React from 'react'

/**
 * Componente Footer com branding Synkhro.
 * 
 * Características:
 * - Exibe logo e texto de copyright
 * - Responsivo e mobile-first
 * - Pode ser usado em qualquer página
 */
const Footer = ({ className = '' }) => {
  return (
    <footer className={`bg-white border-t border-gray-200 py-6 ${className}`}>
      <div className="container mx-auto px-4">
        <div className="flex flex-col sm:flex-row items-center justify-center sm:justify-between gap-4">
          {/* Logo Synkhro */}
          <div className="flex items-center gap-3">
            <img 
              src="/logo.png" 
              alt="Synkhro" 
              className="h-6 w-auto object-contain opacity-80"
            />
            <span className="text-sm text-gray-600">
              Desenvolvido por <span className="font-semibold text-primary">Synkhro</span>
            </span>
          </div>
          
          {/* Copyright */}
          <p className="text-xs text-gray-500">
            © {new Date().getFullYear()} Synkhro. Todos os direitos reservados.
          </p>
        </div>
      </div>
    </footer>
  )
}

export default Footer

