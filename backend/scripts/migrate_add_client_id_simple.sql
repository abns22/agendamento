-- Migração simplificada: Adicionar coluna client_id na tabela appointments
-- Execute este script no PostgreSQL do Render

-- Passo 1: Adicionar coluna client_id (nullable para compatibilidade com dados existentes)
ALTER TABLE appointments
ADD COLUMN IF NOT EXISTS client_id VARCHAR(36) NULL;

-- Passo 2: Adicionar índice para melhor performance
CREATE INDEX IF NOT EXISTS idx_appointments_client_id ON appointments (client_id);

-- Verificar se a coluna foi criada (opcional - para confirmar)
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'appointments' AND column_name = 'client_id';

