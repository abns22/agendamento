import React from 'react'
import { Link } from 'react-router-dom'

/**
 * Página inicial do sistema.
 * 
 * Pode ser uma landing page ou redirecionamento direto para agendamento.
 */
const Home = () => {
  // Por enquanto, vamos criar uma página simples que direciona para o agendamento
  // Você pode personalizar isso depois com informações do estúdio
  
  return (
    <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-text mb-4">
          Synkhro
        </h1>
        <p className="text-gray-600 mb-6">
          Agende seu horário de forma rápida e fácil
        </p>
      </div>

      <div className="w-full max-w-sm space-y-4">
        {/* Card de Agendamento */}
        <Link
          to="/booking/estudio-bella"
          className="block bg-primary text-white rounded-lg p-6 text-center hover:bg-primary-dark transition-colors shadow-md"
        >
          <div className="mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold mb-2">Fazer Agendamento</h2>
          <p className="text-sm opacity-90">
            Clique aqui para agendar seu horário
          </p>
        </Link>

        {/* Informações adicionais (opcional) */}
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">
            Horário de funcionamento: Segunda a Sexta, 09:00 - 18:00
          </p>
        </div>
      </div>
    </div>
  )
}

export default Home

