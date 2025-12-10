-- Script SQL para criar o banco de dados e todas as tabelas do sistema
-- Execute este script no MySQL como root ou usuário com permissões de criação

-- Criar banco de dados
CREATE DATABASE IF NOT EXISTS agendamento_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE agendamento_db;

-- ============================================
-- TABELA: tenants
-- ============================================
CREATE TABLE IF NOT EXISTS tenants (
    id CHAR(36) PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    whatsapp_phone_id VARCHAR(50) NULL,
    notification_phone_number VARCHAR(20) NULL COMMENT 'Número do estúdio para receber notificações (formato internacional)',
    stripe_subscription_id VARCHAR(100) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    INDEX idx_tenants_slug (slug),
    INDEX idx_tenants_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TABELA: users
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('SUPER_ADMIN', 'TENANT_ADMIN', 'ADMIN', 'STAFF') NOT NULL DEFAULT 'TENANT_ADMIN',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_tenant_id (tenant_id),
    INDEX idx_users_email (email),
    INDEX idx_users_is_active (is_active),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TABELA: services
-- ============================================
CREATE TABLE IF NOT EXISTS services (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    name VARCHAR(200) NOT NULL,
    duration_minutes INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    INDEX idx_services_tenant_id (tenant_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TABELA: schedule_configs
-- ============================================
CREATE TABLE IF NOT EXISTS schedule_configs (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    day_of_week INT NOT NULL COMMENT '0=Segunda, 1=Terça, ..., 6=Domingo',
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_schedule_configs_tenant_id (tenant_id),
    UNIQUE KEY uq_tenant_day (tenant_id, day_of_week),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TABELA: appointments
-- ============================================
CREATE TABLE IF NOT EXISTS appointments (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    service_id CHAR(36) NULL COMMENT 'NULL para bloqueios manuais',
    customer_name VARCHAR(200) NULL COMMENT 'NULL para bloqueios manuais',
    customer_phone VARCHAR(20) NULL COMMENT 'NULL para bloqueios manuais',
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    status ENUM('PENDING', 'CONFIRMED', 'CANCELED', 'COMPLETED') NOT NULL DEFAULT 'PENDING',
    is_manual_block BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NULL COMMENT 'Descrição do bloqueio manual',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_appointments_tenant_id (tenant_id),
    INDEX idx_appointments_service_id (service_id),
    INDEX idx_appointments_start_datetime (start_datetime),
    INDEX idx_appointments_status (status),
    INDEX idx_appointments_is_manual_block (is_manual_block),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Verificar criação das tabelas
-- ============================================
SHOW TABLES;

-- Verificar estrutura das tabelas
DESCRIBE tenants;
DESCRIBE users;
DESCRIBE services;
DESCRIBE schedule_configs;
DESCRIBE appointments;

