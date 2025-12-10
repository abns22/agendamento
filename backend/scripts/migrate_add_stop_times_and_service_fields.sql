-- Migração: Criar tabela stop_times e adicionar campos display_color_code e long_description ao Service
-- Execute este script no MySQL

-- 1. Adicionar campos ao Service
ALTER TABLE services 
ADD COLUMN display_color_code VARCHAR(7) NULL COMMENT 'Cor de exibição na Agenda Admin (ex: #4A90E2)' AFTER promotion_color_code,
ADD COLUMN long_description TEXT NULL COMMENT 'Descrição detalhada do serviço' AFTER display_color_code;

-- 2. Criar tabela stop_times
CREATE TABLE IF NOT EXISTS stop_times (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    day_of_week INT NOT NULL COMMENT 'Dia da semana (0=Segunda, 6=Domingo)',
    start_time TIME NOT NULL COMMENT 'Horário de início da parada (ex: 12:00)',
    end_time TIME NOT NULL COMMENT 'Horário de fim da parada (ex: 13:00)',
    description VARCHAR(200) NULL COMMENT 'Descrição opcional (ex: Almoço, Pausa)',
    INDEX idx_stop_times_tenant_id (tenant_id),
    INDEX idx_stop_times_day_of_week (day_of_week),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

