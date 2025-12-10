-- Migração: Adicionar campos financeiros
-- Data: 2024-12-07
-- Descrição: Adiciona campos para módulo financeiro (custo fixo em serviços e configurações de pagamento)

-- ============================================
-- 1. Adicionar fixed_cost_value ao Service
-- ============================================
ALTER TABLE services 
ADD COLUMN fixed_cost_value DECIMAL(10, 2) NULL 
COMMENT 'Custo fixo do serviço (para cálculo de lucro)';

-- ============================================
-- 2. Criar tabela payment_method_configs
-- ============================================
CREATE TABLE IF NOT EXISTS payment_method_configs (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    method_name VARCHAR(100) NOT NULL COMMENT 'Nome da forma de pagamento (ex: Credit Card, Debit Card, Pix)',
    is_editable BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Se a forma de pagamento pode ser editada (False para Dinheiro e Pix)',
    max_installments INT NULL COMMENT 'Máximo de parcelas (apenas para crédito)',
    debit_tax_type VARCHAR(10) NULL COMMENT 'Tipo de taxa de débito: % ou R$',
    debit_tax_value DECIMAL(10, 2) NULL COMMENT 'Valor da taxa de débito',
    INDEX idx_payment_method_configs_tenant_id (tenant_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. Criar tabela payment_installment_configs
-- ============================================
CREATE TABLE IF NOT EXISTS payment_installment_configs (
    id CHAR(36) PRIMARY KEY,
    payment_method_id CHAR(36) NOT NULL,
    installments_count INT NOT NULL COMMENT 'Número de parcelas (2, 3, 4, etc.)',
    tax_type ENUM('%', 'R$') NOT NULL COMMENT 'Tipo de taxa: percentual ou valor fixo',
    tax_value DECIMAL(10, 2) NOT NULL COMMENT 'Valor da taxa',
    INDEX idx_payment_installment_configs_payment_method_id (payment_method_id),
    UNIQUE KEY uq_payment_method_installments (payment_method_id, installments_count),
    FOREIGN KEY (payment_method_id) REFERENCES payment_method_configs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

