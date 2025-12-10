-- Migration: Adicionar campo cancellation_reason à tabela appointments
-- Execute este script no MySQL

USE agendamento_db;

-- Adicionar coluna cancellation_reason
-- NOTA: Se a coluna já existir, você receberá um erro. Isso é esperado.
ALTER TABLE appointments 
ADD COLUMN cancellation_reason TEXT NULL COMMENT 'Motivo do cancelamento (quando status = CANCELED)';

