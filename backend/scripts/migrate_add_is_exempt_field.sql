-- Migração: Adicionar campo is_exempt à tabela tenants
-- Execute este script no banco de dados para adicionar o campo de isenção de pagamento

-- Adicionar is_exempt com valor padrão FALSE
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS is_exempt BOOLEAN NOT NULL DEFAULT FALSE;

-- Adicionar índice para performance
CREATE INDEX IF NOT EXISTS idx_tenants_is_exempt ON tenants (is_exempt);

-- Comentário explicativo
COMMENT ON COLUMN tenants.is_exempt IS 'Se True, tenant está isento de pagamento e tem acesso total ao sistema independente do status da assinatura';

