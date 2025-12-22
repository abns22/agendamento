-- Migração: Adicionar campo discount (desconto) à tabela transactions
-- Data: 2025-01-XX
-- Descrição: Adiciona suporte a descontos nas transações financeiras

-- PostgreSQL
ALTER TABLE transactions 
ADD COLUMN discount DECIMAL(10, 2) NOT NULL DEFAULT 0.00;

-- Comentário
COMMENT ON COLUMN transactions.discount IS 'Valor do desconto aplicado (padrão: 0.00)';

