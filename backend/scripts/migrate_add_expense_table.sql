-- Migração: Criar tabela de Despesas (Expenses)
-- Data: 2024-12-07
-- Descrição: Cria tabela para registro de despesas operacionais do estúdio

-- ============================================
-- Criar tabela expenses
-- ============================================
CREATE TABLE IF NOT EXISTS expenses (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    description TEXT NOT NULL COMMENT 'Descrição da despesa',
    value DECIMAL(10, 2) NOT NULL COMMENT 'Valor da despesa',
    category VARCHAR(100) NULL COMMENT 'Categoria (ex: Aluguel, Material, Salário)',
    date_time DATETIME NOT NULL COMMENT 'Data/hora da despesa (UTC)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_expenses_tenant_id (tenant_id),
    INDEX idx_expenses_date_time (date_time),
    INDEX idx_expenses_category (category),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

