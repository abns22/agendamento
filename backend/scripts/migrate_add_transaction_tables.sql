-- Migração: Adicionar tabelas de Transaction e PaymentEntry
-- Data: 2024-12-07
-- Descrição: Cria tabelas para registro de transações no caixa

-- ============================================
-- 1. Adicionar campos de histórico ao Appointment
-- ============================================
ALTER TABLE appointments 
ADD COLUMN final_sale_value DECIMAL(10, 2) NULL COMMENT 'Valor final de venda (para histórico)',
ADD COLUMN service_cost DECIMAL(10, 2) NULL COMMENT 'Custo do serviço (para histórico)';

-- Atualizar status padrão para SCHEDULED (se necessário)
-- ALTER TABLE appointments MODIFY COLUMN status ENUM('SCHEDULED', 'PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELED') NOT NULL DEFAULT 'SCHEDULED';

-- ============================================
-- 2. Criar tabela transactions
-- ============================================
CREATE TABLE IF NOT EXISTS transactions (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    appointment_id CHAR(36) NOT NULL,
    date_time DATETIME NOT NULL COMMENT 'Data/hora da transação (UTC)',
    gross_value DECIMAL(10, 2) NOT NULL COMMENT 'Valor bruto (antes das taxas)',
    net_value DECIMAL(10, 2) NOT NULL COMMENT 'Valor líquido (após taxas)',
    total_cost DECIMAL(10, 2) NOT NULL COMMENT 'Soma dos custos fixos dos serviços',
    total_profit DECIMAL(10, 2) NOT NULL COMMENT 'Lucro (net_value - total_cost)',
    additional_cost DECIMAL(10, 2) NULL COMMENT 'Custo adicional opcional',
    INDEX idx_transactions_tenant_id (tenant_id),
    INDEX idx_transactions_appointment_id (appointment_id),
    INDEX idx_transactions_date_time (date_time),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. Criar tabela payment_entries
-- ============================================
CREATE TABLE IF NOT EXISTS payment_entries (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,
    payment_method_id CHAR(36) NOT NULL,
    value_paid DECIMAL(10, 2) NOT NULL COMMENT 'Valor parcial pago nesta forma',
    installments INT NULL COMMENT 'Número de parcelas (apenas para crédito)',
    is_bank_account BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'True se for PIX/Cartão',
    INDEX idx_payment_entries_transaction_id (transaction_id),
    INDEX idx_payment_entries_payment_method_id (payment_method_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_method_id) REFERENCES payment_method_configs(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

