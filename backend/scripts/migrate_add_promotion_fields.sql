-- Migração: Adicionar campos de promoção ao Service
-- Data: 2024-12-07
-- Descrição: Adiciona campos para módulo de promoções nos serviços

-- ============================================
-- Adicionar campos de promoção ao Service
-- ============================================
ALTER TABLE services 
ADD COLUMN is_promotional BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Se o serviço está em promoção',
ADD COLUMN promotion_start_date DATETIME NULL COMMENT 'Data/hora de início da promoção (UTC)',
ADD COLUMN promotion_end_date DATETIME NULL COMMENT 'Data/hora de fim da promoção (UTC)',
ADD COLUMN promotional_value DECIMAL(10, 2) NULL COMMENT 'Valor promocional do serviço',
ADD COLUMN promotion_display_name VARCHAR(200) NULL COMMENT 'Nome da promoção (ex: Promoção de Natal)',
ADD COLUMN promotion_description TEXT NULL COMMENT 'Descrição/observação da promoção',
ADD COLUMN promotion_color_code VARCHAR(7) NULL COMMENT 'Código hex da cor da promoção (ex: #FF0000)';

-- Adicionar índice para melhorar performance em consultas de promoções
CREATE INDEX idx_services_is_promotional ON services(is_promotional);

