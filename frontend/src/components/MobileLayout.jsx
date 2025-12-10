import React from 'react'

/**
 * Layout base otimizado para dispositivos móveis.
 * 
 * Características:
 * - Largura máxima de 420px (mobile-first)
 * - Centralizado em telas maiores
 * - Área de conteúdo principal
 * - Barra de navegação inferior (estrutura)
 */
const MobileLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-neutral-light flex flex-col items-center">
      {/* Container principal com largura máxima para mobile */}
      <div className="w-full max-w-[420px] bg-white min-h-screen flex flex-col shadow-lg">
        
        {/* Área de conteúdo principal */}
        <main className="flex-1 overflow-y-auto">
          {children || (
            <div className="p-6">
              <h1 className="text-2xl font-bold text-text mb-4">
                Sistema de Agendamento
              </h1>
              <p className="text-gray-600">
                Conteúdo principal da aplicação será renderizado aqui.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default MobileLayout


