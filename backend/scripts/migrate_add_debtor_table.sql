-- Migração: Criar tabela de Devedores (Debtors) e adicionar campo is_paid ao Transaction
-- Data: 2024-12-07
-- Descrição: Cria tabela para gestão de contas a receber e adiciona campo de controle de pagamento

-- ============================================
-- 1. Adicionar campo is_paid ao Transaction
-- ============================================
ALTER TABLE transactions 
ADD COLUMN is_paid BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'True se foi pago, False se é a prazo (pagamento futuro)',
ADD INDEX idx_transactions_is_paid (is_paid);

-- ============================================
-- 2. Criar tabela debtors
-- ============================================
CREATE TABLE IF NOT EXISTS debtors (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,
    client_name VARCHAR(200) NOT NULL COMMENT 'Nome do cliente devedor',
    client_phone VARCHAR(20) NULL COMMENT 'Telefone do cliente',
    due_date DATETIME NOT NULL COMMENT 'Data de vencimento (UTC)',
    value_due DECIMAL(10, 2) NOT NULL COMMENT 'Valor devido (net_value da transaction)',
    status ENUM('PENDING', 'PAID') NOT NULL DEFAULT 'PENDING' COMMENT 'Status do devedor',
    paid_at DATETIME NULL COMMENT 'Data/hora do pagamento (quando status = PAID)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_debtors_transaction_id (transaction_id),
    INDEX idx_debtors_due_date (due_date),
    INDEX idx_debtors_status (status),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

