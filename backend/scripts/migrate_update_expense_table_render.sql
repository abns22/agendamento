-- ============================================
-- COMANDOS PARA EXECUTAR NO POSTGRESQL DO RENDER
-- ============================================
-- Execute cada bloco de comandos separadamente no psql
-- Ou copie e cole tudo de uma vez

-- ============================================
-- 1. Criar tipo ENUM para payment_method (se não existir)
-- ============================================
DO $$ BEGIN
    CREATE TYPE payment_method_enum AS ENUM('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'PIX', 'BANK_TRANSFER');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================
-- 2. Adicionar coluna item_name (se não existir)
-- ============================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'expenses' 
          AND column_name = 'item_name'
    ) THEN
        ALTER TABLE expenses ADD COLUMN item_name VARCHAR(200) NULL;
        COMMENT ON COLUMN expenses.item_name IS 'Nome do item comprado (opcional)';
    END IF;
END $$;

-- ============================================
-- 3. Adicionar coluna payment_method (se não existir)
-- ============================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'expenses' 
          AND column_name = 'payment_method'
    ) THEN
        ALTER TABLE expenses ADD COLUMN payment_method payment_method_enum NOT NULL DEFAULT 'CASH';
        COMMENT ON COLUMN expenses.payment_method IS 'Método de pagamento';
    END IF;
END $$;

-- ============================================
-- 4. Adicionar coluna payment_date (se não existir)
-- ============================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'expenses' 
          AND column_name = 'payment_date'
    ) THEN
        ALTER TABLE expenses ADD COLUMN payment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
        COMMENT ON COLUMN expenses.payment_date IS 'Data em que o dinheiro saiu do caixa';
        
        -- Migrar dados: copiar date_time para payment_date se houver
        UPDATE expenses 
        SET payment_date = date_time 
        WHERE payment_date IS NULL 
           OR payment_date = '1970-01-01 00:00:00'::timestamp
           OR (date_time IS NOT NULL AND payment_date < date_time);
    END IF;
END $$;

-- ============================================
-- 5. Renomear coluna 'value' para 'amount' (se necessário)
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'expenses' 
          AND column_name = 'value'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'expenses' 
          AND column_name = 'amount'
    ) THEN
        ALTER TABLE expenses RENAME COLUMN value TO amount;
        COMMENT ON COLUMN expenses.amount IS 'Valor da despesa';
    END IF;
END $$;

-- ============================================
-- 6. Criar índices (se não existirem)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_expenses_payment_method ON expenses(payment_method);
CREATE INDEX IF NOT EXISTS idx_expenses_payment_date ON expenses(payment_date);

-- ============================================
-- 7. Verificar estrutura final (opcional)
-- ============================================
-- Execute este comando para ver a estrutura da tabela:
-- \d expenses

-- Ou para ver apenas as colunas:
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'expenses'
ORDER BY ordinal_position;
