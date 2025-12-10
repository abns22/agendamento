-- Script para atualizar o ENUM da coluna 'role' na tabela 'users'
-- Adiciona SUPER_ADMIN e TENANT_ADMIN ao enum existente

USE agendamento_db;

-- Atualizar o enum para incluir SUPER_ADMIN e TENANT_ADMIN
-- Mantém ADMIN e STAFF para compatibilidade
ALTER TABLE users 
MODIFY COLUMN role ENUM('SUPER_ADMIN', 'TENANT_ADMIN', 'ADMIN', 'STAFF') 
NOT NULL DEFAULT 'TENANT_ADMIN';

-- Verificar se a alteração foi aplicada
DESCRIBE users;

