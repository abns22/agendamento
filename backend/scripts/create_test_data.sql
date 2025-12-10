-- Script SQL para criar dados de teste
-- Execute este script no PostgreSQL após criar o banco de dados

-- Criar Tenant de teste
INSERT INTO tenants (id, slug, is_active, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'estudio-bella',
  true,
  NOW(),
  NOW()
)
ON CONFLICT (slug) DO NOTHING;

-- Criar Serviços de teste
INSERT INTO services (id, tenant_id, name, duration_minutes, price)
SELECT
  gen_random_uuid(),
  t.id,
  'Corte de Cabelo',
  45,
  50.00
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT DO NOTHING;

INSERT INTO services (id, tenant_id, name, duration_minutes, price)
SELECT
  gen_random_uuid(),
  t.id,
  'Manicure',
  60,
  35.00
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT DO NOTHING;

-- Criar Configuração de Horário (Segunda a Sexta: 09:00 - 18:00)
INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
SELECT
  gen_random_uuid(),
  t.id,
  0, -- Segunda
  '09:00',
  '18:00',
  false
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT (tenant_id, day_of_week) DO NOTHING;

INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
SELECT
  gen_random_uuid(),
  t.id,
  1, -- Terça
  '09:00',
  '18:00',
  false
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT (tenant_id, day_of_week) DO NOTHING;

INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
SELECT
  gen_random_uuid(),
  t.id,
  2, -- Quarta
  '09:00',
  '18:00',
  false
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT (tenant_id, day_of_week) DO NOTHING;

INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
SELECT
  gen_random_uuid(),
  t.id,
  3, -- Quinta
  '09:00',
  '18:00',
  false
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT (tenant_id, day_of_week) DO NOTHING;

INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
SELECT
  gen_random_uuid(),
  t.id,
  4, -- Sexta
  '09:00',
  '18:00',
  false
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT (tenant_id, day_of_week) DO NOTHING;

-- Sábado e Domingo fechados
INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
SELECT
  gen_random_uuid(),
  t.id,
  5, -- Sábado
  '09:00',
  '18:00',
  true
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT (tenant_id, day_of_week) DO NOTHING;

INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
SELECT
  gen_random_uuid(),
  t.id,
  6, -- Domingo
  '09:00',
  '18:00',
  true
FROM tenants t
WHERE t.slug = 'estudio-bella'
ON CONFLICT (tenant_id, day_of_week) DO NOTHING;

-- Verificar dados criados
SELECT 'Tenant criado:' as info, slug, is_active FROM tenants WHERE slug = 'estudio-bella';
SELECT 'Serviços criados:' as info, COUNT(*) as total FROM services WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'estudio-bella');
SELECT 'Configurações criadas:' as info, COUNT(*) as total FROM schedule_configs WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'estudio-bella');

