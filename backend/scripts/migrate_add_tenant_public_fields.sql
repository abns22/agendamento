-- Migração: Adicionar campos públicos ao modelo Tenant
-- Data: 2024-12-06
-- Descrição: Adiciona colunas para personalização da página pública de agendamento

-- ⚠️ ATENÇÃO: MySQL não suporta IF NOT EXISTS para ALTER TABLE
-- Se as colunas já existirem, você receberá um erro "Duplicate column name"
-- Nesse caso, ignore o erro ou use o script Python que verifica antes de adicionar

-- Adicionar coluna 'name' (Nome do estúdio)
ALTER TABLE tenants 
ADD COLUMN name VARCHAR(200) NULL 
COMMENT 'Nome do estúdio (ex: Estúdio Bella)';

-- Adicionar coluna 'logo_url' (URL da logo)
ALTER TABLE tenants 
ADD COLUMN logo_url VARCHAR(500) NULL 
COMMENT 'URL da logo do estúdio';

-- Adicionar coluna 'description' (Descrição do estúdio)
ALTER TABLE tenants 
ADD COLUMN description TEXT NULL 
COMMENT 'Breve descrição do estúdio';

-- Adicionar coluna 'address' (Endereço físico)
ALTER TABLE tenants 
ADD COLUMN address TEXT NULL 
COMMENT 'Endereço físico do estúdio';

-- Adicionar coluna 'phone_contact' (Telefone público)
ALTER TABLE tenants 
ADD COLUMN phone_contact VARCHAR(20) NULL 
COMMENT 'Número de telefone público para contato';

-- Adicionar coluna 'schedule_display_text' (Texto do horário)
ALTER TABLE tenants 
ADD COLUMN schedule_display_text VARCHAR(200) NULL 
COMMENT 'Texto amigável do horário de funcionamento (ex: Segunda a Sexta, 09:00 - 18:00)';

-- Verificar se as colunas foram adicionadas
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    CHARACTER_MAXIMUM_LENGTH, 
    IS_NULLABLE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'tenants'
  AND COLUMN_NAME IN ('name', 'logo_url', 'description', 'address', 'phone_contact', 'schedule_display_text')
ORDER BY COLUMN_NAME;

