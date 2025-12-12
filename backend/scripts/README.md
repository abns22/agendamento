# Scripts SQL - Synkhro

## 📋 Scripts Disponíveis

### 1. `create_database.sql`
Cria apenas o banco de dados e todas as tabelas (sem dados de teste).

**Uso:**
```bash
mysql -u root -p < create_database.sql
```

Ou no MySQL:
```sql
SOURCE create_database.sql;
```

### 2. `create_database_and_data.sql`
Cria o banco, tabelas E insere dados de teste (tenant, serviços, horários).

**Uso:**
```bash
mysql -u root -p < create_database_and_data.sql
```

Ou no MySQL:
```sql
SOURCE create_database_and_data.sql;
```

### 3. `create_test_data_mysql.sql`
Apenas insere dados de teste (requer que as tabelas já existam).

**Uso:**
```bash
mysql -u root -p agendamento_db < create_test_data_mysql.sql
```

## 🔧 Configuração do .env

Após criar o banco, configure o `backend/.env`:

```env
DATABASE_URL=mysql+aiomysql://root:sua_senha@localhost:3306/agendamento_db
```

**Nota**: Se o MySQL não tiver senha, use:
```env
DATABASE_URL=mysql+aiomysql://root:@localhost:3306/agendamento_db
```

## ✅ Verificar Instalação

Após executar os scripts, verifique:

```sql
USE agendamento_db;
SHOW TABLES;
SELECT * FROM tenants;
SELECT * FROM services;
SELECT * FROM schedule_configs;
```

## 📝 Estrutura das Tabelas

- **tenants**: Empresas/estúdios
- **users**: Usuários/administradores
- **services**: Serviços oferecidos
- **schedule_configs**: Horários de funcionamento
- **appointments**: Agendamentos e bloqueios

