/**
 * Custom hook para operações de agendamento público.
 */
import { useState } from 'react'
import { api } from '../utils/api'

/**
 * Hook para buscar serviços disponíveis de um tenant.
 */
export const useServices = (tenantSlug) => {
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchServices = async () => {
    if (!tenantSlug) {
      console.warn('⚠️ useServices: tenantSlug não fornecido')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const url = `/api/v1/booking/${tenantSlug}/services`
      console.log('📡 useServices: Fazendo requisição para:', url)
      const response = await api.get(url)
      console.log('✅ useServices: Serviços recebidos:', response.data)
      setServices(response.data || [])
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao carregar serviços'
      console.error('❌ useServices: Erro ao buscar serviços:', {
        error: err,
        status: err.response?.status,
        detail: err.response?.data?.detail,
        tenantSlug
      })
      setError(errorMessage)
      setServices([]) // Limpar serviços em caso de erro
    } finally {
      setLoading(false)
    }
  }

  return { services, loading, error, fetchServices }
}

/**
 * Hook para buscar horários disponíveis.
 */
export const useAvailableSlots = () => {
  const [slots, setSlots] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchSlots = async (tenantSlug, serviceIds, date) => {
    // serviceIds pode ser um único ID ou um array de IDs
    const ids = Array.isArray(serviceIds) ? serviceIds : [serviceIds]
    
    if (!tenantSlug || !ids || ids.length === 0 || !date) {
      console.warn('⚠️ useAvailableSlots: Parâmetros incompletos', { tenantSlug, serviceIds: ids, date })
      setSlots([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      const url = `/api/v1/booking/${tenantSlug}/slots`
      // FastAPI espera múltiplos parâmetros com o mesmo nome: service_ids=uuid1&service_ids=uuid2
      // Construir URL manualmente para evitar axios usar service_ids[]=...
      const serviceIdsParam = ids.map(id => `service_ids=${encodeURIComponent(id)}`).join('&')
      const fullUrl = `${url}?${serviceIdsParam}&date=${encodeURIComponent(date)}`
      console.log('📡 useAvailableSlots: Fazendo requisição para:', fullUrl)
      const response = await api.get(fullUrl)
      console.log('✅ useAvailableSlots: Slots recebidos:', response.data)
      setSlots(response.data?.available_slots || [])
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao carregar horários'
      console.error('❌ useAvailableSlots: Erro ao buscar horários:', {
        error: err,
        status: err.response?.status,
        detail: err.response?.data?.detail,
        tenantSlug,
        serviceIds: ids,
        date
      })
      setError(errorMessage)
      setSlots([])
    } finally {
      setLoading(false)
    }
  }

  return { slots, loading, error, fetchSlots }
}

/**
 * Hook para criar agendamento.
 */
export const useCreateAppointment = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const createAppointment = async (tenantSlug, appointmentData) => {
    if (!tenantSlug) {
      const errorMessage = 'Slug do estúdio não fornecido'
      setError(errorMessage)
      throw new Error(errorMessage)
    }

    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const url = `/api/v1/booking/${tenantSlug}/appointments`
      console.log('📡 useCreateAppointment: Criando agendamento:', url, appointmentData)
      const response = await api.post(url, appointmentData)
      console.log('✅ useCreateAppointment: Agendamento criado:', response.data)
      setSuccess(true)
      return response.data
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao criar agendamento'
      console.error('❌ useCreateAppointment: Erro ao criar agendamento:', {
        error: err,
        status: err.response?.status,
        detail: err.response?.data?.detail,
        tenantSlug,
        appointmentData
      })
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return { createAppointment, loading, error, success }
}

