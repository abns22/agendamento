-- Migração: Adicionar coluna client_id na tabela appointments
-- Esta migração adiciona a FK para a tabela clients mantendo os campos originais como fallback

-- Passo 1: Adicionar coluna client_id (nullable por enquanto para compatibilidade com dados existentes)
ALTER TABLE appointments
ADD COLUMN IF NOT EXISTS client_id VARCHAR(36) NULL;

-- Passo 2: Adicionar índice para melhor performance
CREATE INDEX IF NOT EXISTS idx_appointments_client_id ON appointments (client_id);

-- Passo 3: Adicionar Foreign Key constraint
-- NOTA: Esta FK pode falhar se houver appointments com client_id já preenchido e client não existir
-- Execute apenas se tiver certeza que os dados estão consistentes
-- ALTER TABLE appointments
-- ADD CONSTRAINT fk_appointments_client_id 
-- FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL;

-- Passo 4 (OPCIONAL): Migrar dados existentes
-- Se você quiser migrar automaticamente os appointments existentes para clientes:
-- Este script cria clientes a partir de customer_name e customer_phone existentes
-- e vincula os appointments. Execute apenas se desejar migração automática.

-- IMPORTANTE: Descomente o bloco abaixo apenas se quiser fazer migração automática dos dados
-- 
-- DO $$
-- DECLARE
--     rec RECORD;
--     new_client_id VARCHAR(36);
-- BEGIN
--     -- Iterar sobre appointments que não têm client_id mas têm customer_name e customer_phone
--     FOR rec IN 
--         SELECT DISTINCT 
--             tenant_id, 
--             customer_name, 
--             customer_phone 
--         FROM appointments 
--         WHERE client_id IS NULL 
--           AND customer_name IS NOT NULL 
--           AND customer_phone IS NOT NULL
--           AND is_manual_block = FALSE
--     LOOP
--         -- Verificar se já existe cliente com este telefone no tenant
--         SELECT id INTO new_client_id
--         FROM clients
--         WHERE tenant_id = rec.tenant_id 
--           AND phone_number = rec.customer_phone
--         LIMIT 1;
--         
--         -- Se não existir, criar novo cliente
--         IF new_client_id IS NULL THEN
--             new_client_id := gen_random_uuid()::VARCHAR;
--             INSERT INTO clients (id, tenant_id, name, phone_number)
--             VALUES (new_client_id, rec.tenant_id, rec.customer_name, rec.customer_phone);
--         END IF;
--         
--         -- Atualizar appointments com este client_id
--         UPDATE appointments
--         SET client_id = new_client_id
--         WHERE tenant_id = rec.tenant_id
--           AND customer_name = rec.customer_name
--           AND customer_phone = rec.customer_phone
--           AND client_id IS NULL
--           AND is_manual_block = FALSE;
--     END LOOP;
-- END $$;

-- Comentário final: Os campos customer_name e customer_phone continuam disponíveis como fallback
-- para histórico e compatibilidade com bloqueios manuais (is_manual_block = TRUE)

