-- Migração: Adicionar suporte a múltiplos serviços por agendamento
-- 
-- Esta migração:
-- 1. Cria a tabela intermediária appointment_services para relação Many-to-Many
-- 2. Adiciona coluna total_value ao appointments para histórico de preços
-- 3. Migra dados existentes (se houver service_id, cria registro na tabela intermediária)
-- 4. Mantém service_id para compatibilidade com bloqueios (nullable)

-- Passo 1: Criar tabela intermediária appointment_services
CREATE TABLE IF NOT EXISTS appointment_services (
    id VARCHAR(36) PRIMARY KEY,
    appointment_id VARCHAR(36) NOT NULL,
    service_id VARCHAR(36) NOT NULL,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
);

-- Criar índices separadamente (sintaxe PostgreSQL)
CREATE INDEX IF NOT EXISTS idx_appointment_services_appointment_id ON appointment_services(appointment_id);
CREATE INDEX IF NOT EXISTS idx_appointment_services_service_id ON appointment_services(service_id);

-- Passo 2: Adicionar coluna total_value ao appointments (se não existir)
-- PostgreSQL
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'appointments' 
        AND column_name = 'total_value'
    ) THEN
        ALTER TABLE appointments 
        ADD COLUMN total_value DECIMAL(10, 2) NULL;
    END IF;
END $$;

-- Passo 3: Migrar dados existentes
-- Se um appointment tiver service_id, criar registro na tabela intermediária
-- Apenas se o appointment não for um bloqueio manual (service_id IS NOT NULL)
-- Nota: Esta migração requer que a extensão uuid-ossp esteja habilitada, ou use gen_random_uuid()
-- Se não disponível, você pode executar manualmente inserindo UUIDs gerados por aplicação externa
INSERT INTO appointment_services (id, appointment_id, service_id)
SELECT 
    gen_random_uuid()::text AS id,
    a.id AS appointment_id,
    a.service_id AS service_id
FROM appointments a
WHERE a.service_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 
      FROM appointment_services ap 
      WHERE ap.appointment_id = a.id AND ap.service_id = a.service_id
  );

-- Nota: service_id no appointments é mantido para compatibilidade com bloqueios e código legado
-- Mas o uso preferencial deve ser através da relação Many-to-Many (appointment_services)

