import React, { useState, useEffect } from 'react'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { useAvailableSlots } from '../../hooks/usePublicBooking'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { TimePill, TimePillGrid } from '../../components/ui'

/**
 * Componente para seleção de data e horário.
 * 
 * Exibe um seletor de data e lista de horários disponíveis como "pílulas" clicáveis.
 */
const TimeSlotPicker = ({ tenantSlug, serviceIds, onSelectDateTime, selectedDate, selectedTime }) => {
  const [selectedDateState, setSelectedDateState] = useState(selectedDate || null)
  const { slots, loading, error, fetchSlots } = useAvailableSlots()

  // Buscar slots quando data ou serviços mudarem
  useEffect(() => {
    if (tenantSlug && serviceIds && serviceIds.length > 0 && selectedDateState) {
      const dateStr = format(selectedDateState, 'yyyy-MM-dd')
      fetchSlots(tenantSlug, serviceIds, dateStr)
    }
  }, [tenantSlug, serviceIds, selectedDateState, fetchSlots])

  // Filtrar datas passadas e definir data mínima (hoje)
  const minDate = new Date()
  minDate.setHours(0, 0, 0, 0)

  const handleDateChange = (date) => {
    setSelectedDateState(date)
    // Limpar horário selecionado ao mudar data
    if (onSelectDateTime) {
      onSelectDateTime(date, null)
    }
  }

  const handleTimeSelect = (time) => {
    if (onSelectDateTime && selectedDateState) {
      onSelectDateTime(selectedDateState, time)
    }
  }

  // Combinar data e hora selecionados
  // IMPORTANTE: Os horários do backend são horários locais (não UTC)
  // O tenant configura os horários de funcionamento como horários locais
  // Portanto, não precisamos converter, apenas exibir diretamente
  const getSelectedDateTime = () => {
    if (!selectedDateState || !selectedTime) return null
    
    const [hours, minutes] = selectedTime.split(':')
    // Criar datetime no timezone local
    const dateTime = new Date(selectedDateState)
    dateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0)
    return dateTime
  }

  return (
    <div className="p-4 space-y-6">
      <h2 className="text-xl font-bold text-text mb-4">Selecione data e horário</h2>

      {/* Seletor de Data */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Data
        </label>
        <div className="relative">
          <DatePicker
            selected={selectedDateState}
            onChange={handleDateChange}
            minDate={minDate}
            dateFormat="dd/MM/yyyy"
            locale={ptBR}
            placeholderText="Selecione uma data"
            className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            calendarClassName="react-datepicker-custom"
          />
        </div>
      </div>

      {/* Lista de Horários Disponíveis */}
      {selectedDateState && (
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-3">
            Horário disponível
          </label>
          
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          {!loading && !error && slots.length === 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800 text-sm">
                Não há horários disponíveis para esta data.
              </p>
            </div>
          )}

          {!loading && slots.length > 0 && (
            <TimePillGrid>
              {slots.map((slot) => (
                <TimePill
                  key={slot}
                  time={slot}
                  selected={selectedTime === slot}
                  onClick={() => handleTimeSelect(slot)}
                />
              ))}
            </TimePillGrid>
          )}
        </div>
      )}

      {/* Preview da seleção */}
      {selectedDateState && selectedTime && (
        <div className="mt-4 p-4 bg-primary bg-opacity-5 rounded-lg border border-primary">
          <p className="text-sm text-gray-600 mb-1">Selecionado:</p>
          <p className="font-semibold text-text">
            {format(selectedDateState, "EEEE, dd 'de' MMMM 'de' yyyy", { locale: ptBR })} às {selectedTime}
          </p>
        </div>
      )}
    </div>
  )
}

export default TimeSlotPicker

