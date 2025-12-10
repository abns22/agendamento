-- Script de migração: Adicionar campo notification_phone_number à tabela tenants
-- Execute este script se a tabela já existe mas não tem este campo

USE agendamento_db;

-- Adicionar coluna notification_phone_number (se não existir)
ALTER TABLE tenants 
ADD COLUMN IF NOT EXISTS notification_phone_number VARCHAR(20) NULL 
COMMENT 'Número do estúdio para receber notificações (formato internacional)'
AFTER whatsapp_phone_id;

-- Verificar se a coluna foi adicionada
DESCRIBE tenants;

