-- Migração: Criar tabelas de inventário
-- Execute este script no MySQL

-- Tabela de Categorias de Produtos
CREATE TABLE IF NOT EXISTS product_categories (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    name VARCHAR(200) NOT NULL COMMENT 'Nome da categoria',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_product_categories_tenant_id (tenant_id),
    INDEX idx_product_categories_name (name),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Produtos
CREATE TABLE IF NOT EXISTS products (
    id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    category_id CHAR(36) NULL COMMENT 'ID da categoria (opcional)',
    name VARCHAR(200) NOT NULL COMMENT 'Nome do produto',
    unit_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'Custo unitário de aquisição',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_products_tenant_id (tenant_id),
    INDEX idx_products_category_id (category_id),
    INDEX idx_products_name (name),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES product_categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Entradas de Estoque
CREATE TABLE IF NOT EXISTS stock_entries (
    id CHAR(36) PRIMARY KEY,
    product_id CHAR(36) NOT NULL,
    unit_type ENUM('UNITARIO', 'PACOTE', 'CAIXA') NOT NULL DEFAULT 'UNITARIO' COMMENT 'Tipo de unidade',
    quantity INT NOT NULL DEFAULT 0 COMMENT 'Quantidade em estoque',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock_entries_product_id (product_id),
    INDEX idx_stock_entries_unit_type (unit_type),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

