-- Migração: Criar tabela clients
-- Execute este script no MySQL

CREATE TABLE IF NOT EXISTS clients (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    name VARCHAR(200) NOT NULL COMMENT 'Nome completo do cliente',
    phone_number VARCHAR(20) NOT NULL COMMENT 'Número de telefone do cliente',
    email VARCHAR(200) NULL COMMENT 'Email do cliente (opcional)',
    birth_date DATE NULL COMMENT 'Data de nascimento (para aniversários)',
    INDEX idx_clients_tenant_id (tenant_id),
    INDEX idx_clients_name (name),
    INDEX idx_clients_phone_number (phone_number),
    INDEX idx_clients_birth_date (birth_date),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

