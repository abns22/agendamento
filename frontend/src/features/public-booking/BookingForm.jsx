import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateAppointment } from '../../hooks/usePublicBooking'
import { format } from 'date-fns'

/**
 * Schema de validação para o formulário de agendamento.
 */
const bookingSchema = z.object({
  customer_name: z
    .string()
    .min(2, 'Nome deve ter pelo menos 2 caracteres')
    .max(200, 'Nome muito longo'),
  customer_phone: z
    .string()
    .min(10, 'Telefone inválido')
    .regex(/^[\d\s\(\)\-\+]+$/, 'Telefone deve conter apenas números'),
})

/**
 * Componente de formulário para criação de agendamento.
 * 
 * Formulário simples com Nome e WhatsApp que faz POST para criar agendamento.
 */
const BookingForm = ({ 
  tenantSlug, 
  serviceIds = [], // Array de IDs de serviços
  selectedDateTime, 
  onSuccess,
  onBack 
}) => {
  const { createAppointment, loading, error } = useCreateAppointment()
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(bookingSchema),
  })

  const onSubmit = async (data) => {
    if (!selectedDateTime || !serviceIds || serviceIds.length === 0) {
      return
    }

    try {
      // IMPORTANTE: Os horários do backend são horários locais (não UTC)
      // O tenant configura os horários de funcionamento como horários locais
      // Portanto, o selectedDateTime já está no timezone local
      // Precisamos converter para UTC antes de enviar ao backend
      
      // Obter componentes locais da data selecionada
      const year = selectedDateTime.getFullYear()
      const month = selectedDateTime.getMonth()
      const day = selectedDateTime.getDate()
      const hours = selectedDateTime.getHours()
      const minutes = selectedDateTime.getMinutes()
      
      // Criar data em UTC a partir do horário local
      // O backend espera receber em UTC, então convertemos o horário local para UTC
      const utcDate = new Date(Date.UTC(year, month, day, hours, minutes, 0, 0))
      const startDatetime = utcDate.toISOString()

      const appointmentData = {
        service_ids: serviceIds, // Array de IDs de serviços
        customer_name: data.customer_name,
        customer_phone: data.customer_phone.replace(/\D/g, ''), // Remove caracteres não numéricos
        start_datetime: startDatetime,
      }

      await createAppointment(tenantSlug, appointmentData)
      
      if (onSuccess) {
        onSuccess()
      }
    } catch (err) {
      // Erro já é tratado pelo hook
      console.error('Erro ao criar agendamento:', err)
    }
  }

  if (!selectedDateTime) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800 text-sm">
            Por favor, selecione uma data e horário primeiro.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-6">
      <h2 className="text-xl font-bold text-text mb-4">Seus dados</h2>

      {/* Resumo da seleção */}
      <div className="bg-neutral-light rounded-lg p-4 mb-6">
        <p className="text-sm text-gray-600 mb-2">Resumo do agendamento:</p>
        <p className="font-semibold text-text">
          {format(selectedDateTime, "dd/MM/yyyy 'às' HH:mm")}
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Campo Nome */}
        <div>
          <label htmlFor="customer_name" className="block text-sm font-semibold text-gray-700 mb-2">
            Nome completo *
          </label>
          <input
            id="customer_name"
            type="text"
            {...register('customer_name')}
            className={`input ${errors.customer_name ? 'border-red-500' : ''}`}
            placeholder="Seu nome completo"
            disabled={loading}
          />
          {errors.customer_name && (
            <p className="mt-1 text-sm text-red-600">{errors.customer_name.message}</p>
          )}
        </div>

        {/* Campo WhatsApp */}
        <div>
          <label htmlFor="customer_phone" className="block text-sm font-semibold text-gray-700 mb-2">
            WhatsApp *
          </label>
          <input
            id="customer_phone"
            type="tel"
            {...register('customer_phone')}
            className={`input ${errors.customer_phone ? 'border-red-500' : ''}`}
            placeholder="(11) 98765-4321"
            disabled={loading}
          />
          {errors.customer_phone && (
            <p className="mt-1 text-sm text-red-600">{errors.customer_phone.message}</p>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Enviaremos a confirmação por WhatsApp
          </p>
        </div>

        {/* Mensagem de erro */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {/* Botões */}
        <div className="flex gap-3 pt-4">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="btn-secondary flex-1"
              disabled={loading}
            >
              Voltar
            </button>
          )}
          <button
            type="submit"
            className="btn-primary flex-1"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Agendando...
              </span>
            ) : (
              'Confirmar Agendamento'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default BookingForm

