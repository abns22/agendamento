-- Migração: Adicionar campos de assinatura à tabela tenants
-- Execute este script no banco de dados para adicionar os novos campos

-- Adicionar stripe_customer_id
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100) NULL;

-- Adicionar índice para stripe_customer_id
CREATE INDEX IF NOT EXISTS idx_tenants_stripe_customer_id ON tenants (stripe_customer_id);

-- Adicionar subscription_status com valor padrão 'pending'
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) NOT NULL DEFAULT 'pending';

-- Adicionar índice para subscription_status
CREATE INDEX IF NOT EXISTS idx_tenants_subscription_status ON tenants (subscription_status);

-- Adicionar current_period_end
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMP WITHOUT TIME ZONE NULL;

-- Adicionar trial_ends_at
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP WITHOUT TIME ZONE NULL;

-- Atualizar tenants existentes que têm stripe_subscription_id mas não têm subscription_status definido
-- Se já têm subscription_id, assumir que estão ativos (será atualizado pelo webhook)
UPDATE tenants
SET subscription_status = 'active'
WHERE stripe_subscription_id IS NOT NULL 
  AND subscription_status = 'pending';

