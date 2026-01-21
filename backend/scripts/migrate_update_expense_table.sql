-- Migração: Atualizar tabela de Despesas (Expenses)
-- Data: 2024-12-XX
-- Descrição: Atualiza tabela expenses com novos campos: item_name, payment_method, payment_date
--            Renomeia 'value' para 'amount' e remove 'updated_at'
-- Banco: PostgreSQL

-- ============================================
-- Backup de dados existentes (opcional)
-- ============================================
-- CREATE TABLE expenses_backup AS SELECT * FROM expenses;

-- ============================================
-- Criar tipo ENUM para payment_method (se não existir)
-- ============================================
DO $$ BEGIN
    CREATE TYPE payment_method_enum AS ENUM('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'PIX', 'BANK_TRANSFER');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================
-- Adicionar novos campos
-- ============================================

-- Adicionar item_name (opcional)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'expenses' AND column_name = 'item_name'
    ) THEN
        ALTER TABLE expenses ADD COLUMN item_name VARCHAR(200) NULL;
        COMMENT ON COLUMN expenses.item_name IS 'Nome do item comprado (opcional)';
    END IF;
END $$;

-- Adicionar payment_method (ENUM)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'expenses' AND column_name = 'payment_method'
    ) THEN
        ALTER TABLE expenses ADD COLUMN payment_method payment_method_enum NOT NULL DEFAULT 'CASH';
        COMMENT ON COLUMN expenses.payment_method IS 'Método de pagamento';
    END IF;
END $$;

-- Adicionar payment_date
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'expenses' AND column_name = 'payment_date'
    ) THEN
        ALTER TABLE expenses ADD COLUMN payment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
        COMMENT ON COLUMN expenses.payment_date IS 'Data em que o dinheiro saiu do caixa';
        
        -- Se houver dados, copiar date_time para payment_date
        UPDATE expenses 
        SET payment_date = date_time 
        WHERE payment_date IS NULL OR payment_date = '1970-01-01 00:00:00'::timestamp;
    END IF;
END $$;

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_expenses_payment_method ON expenses(payment_method);
CREATE INDEX IF NOT EXISTS idx_expenses_payment_date ON expenses(payment_date);

-- ============================================
-- Renomear colunas
-- ============================================

-- Renomear 'value' para 'amount' (se 'value' existir e 'amount' não existir)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'expenses' AND column_name = 'value'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'expenses' AND column_name = 'amount'
    ) THEN
        ALTER TABLE expenses RENAME COLUMN value TO amount;
        COMMENT ON COLUMN expenses.amount IS 'Valor da despesa';
    END IF;
END $$;

-- ============================================
-- Remover coluna updated_at (se não for necessária)
-- ============================================
-- DO $$ 
-- BEGIN
--     IF EXISTS (
--         SELECT 1 FROM information_schema.columns 
--         WHERE table_name = 'expenses' AND column_name = 'updated_at'
--     ) THEN
--         ALTER TABLE expenses DROP COLUMN updated_at;
--     END IF;
-- END $$;

-- ============================================
-- Remover índice antigo de date_time se não for mais usado (opcional)
-- ============================================
-- DROP INDEX IF EXISTS idx_expenses_date_time;

-- ============================================
-- Verificar estrutura final
-- ============================================
-- \d expenses;
