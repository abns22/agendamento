-- ============================================================================
-- Script SQL para deletar transações de um tenant específico
-- ============================================================================
-- 
-- IMPORTANTE: Este script deleta permanentemente transações. Use com cuidado!
-- RECOMENDAÇÃO: Faça backup do banco antes de executar!
-- 
-- ============================================================================
-- PASSO 1: Identificar o tenant_id a partir do email do usuário
-- ============================================================================
-- Execute esta query primeiro para obter o tenant_id
-- Substitua 'myrela.martins2006@icloud.com' pelo email do tenant se necessário

SELECT 
    u.id as user_id,
    u.email,
    u.tenant_id,
    t.slug as tenant_slug,
    t.id as tenant_id_exact
FROM users u
JOIN tenants t ON t.id = u.tenant_id
WHERE u.email = 'myrela.martins2006@icloud.com';

-- ============================================================================
-- PASSO 2: Listar as últimas transações do tenant
-- ============================================================================
-- Execute após obter o tenant_id do PASSO 1
-- Substitua '<tenant_id>' pelo ID retornado na coluna 'tenant_id_exact'

SELECT 
    t.id as transaction_id,
    t.date_time,
    t.gross_value,
    t.net_value,
    t.discount,
    a.customer_name,
    a.start_datetime as appointment_datetime
FROM transactions t
JOIN appointments a ON a.id = t.appointment_id
WHERE t.tenant_id = '<tenant_id>'  -- SUBSTITUIR pelo tenant_id do PASSO 1
ORDER BY t.date_time DESC
LIMIT 20;

-- ============================================================================
-- PASSO 3: Deletar transações específicas
-- ============================================================================
-- IMPORTANTE: Substitua os IDs abaixo pelos IDs das transações que deseja deletar
-- Este script deleta as transações e seus payment_entries relacionados (cascade)
-- 
-- INSTRUÇÕES:
-- 1. Copie os IDs das transações do PASSO 2
-- 2. Substitua 'id1', 'id2', 'id3' pelos IDs reais nas queries abaixo
-- 3. Substitua '<tenant_id>' pelo tenant_id do PASSO 1
-- 4. Execute as queries dentro de uma transação (BEGIN...COMMIT)

-- ATENÇÃO: Este DELETE é permanente! Faça backup antes!

BEGIN;

-- Deletar payment_entries primeiro (por segurança, mesmo com cascade)
DELETE FROM payment_entries 
WHERE transaction_id IN (
    'id1',  -- SUBSTITUIR pelo ID da primeira transação
    'id2',  -- SUBSTITUIR pelo ID da segunda transação
    'id3'   -- SUBSTITUIR pelo ID da terceira transação
);

-- Deletar as transações
DELETE FROM transactions 
WHERE id IN (
    'id1',  -- SUBSTITUIR pelo ID da primeira transação
    'id2',  -- SUBSTITUIR pelo ID da segunda transação
    'id3'   -- SUBSTITUIR pelo ID da terceira transação
)
  AND tenant_id = '<tenant_id>';  -- SUBSTITUIR pelo tenant_id do PASSO 1

-- Verificar quantas transações foram deletadas (deve retornar 0 após DELETE)
SELECT COUNT(*) as deleted_count 
FROM transactions 
WHERE id IN ('id1', 'id2', 'id3');  -- Mesmos IDs usados acima

-- Se estiver satisfeito com o resultado, execute COMMIT
-- Se algo estiver errado, execute ROLLBACK para reverter
COMMIT;
-- ROLLBACK;  -- Descomente esta linha se quiser reverter (e comente COMMIT)
