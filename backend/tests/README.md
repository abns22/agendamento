# Testes de Integração

Este diretório contém testes de integração para validar funcionalidades críticas do sistema.

## 📋 Pré-requisitos

1. Instalar dependências de teste:
```bash
pip install -r requirements.txt
```

2. Configurar banco de dados de teste (ou usar o mesmo banco de desenvolvimento):
   - As variáveis de ambiente devem estar configuradas no arquivo `.env`
   - O banco de dados deve estar acessível

## 🚀 Executando os Testes

### Executar todos os testes:
```bash
pytest
```

### Executar apenas testes de integração:
```bash
pytest tests/integration/
```

### Executar um teste específico:
```bash
pytest tests/integration/test_critical_flows.py::test_multi_tenant_isolation
```

### Executar com mais verbosidade:
```bash
pytest -v
```

### Executar com cobertura:
```bash
pytest --cov=app --cov-report=html
```

## 📝 Testes Implementados

### 1. Teste de Isolamento Multi-tenant
**Arquivo:** `test_critical_flows.py::test_multi_tenant_isolation`

**Objetivo:** Garantir que um usuário de um Tenant A nunca consiga acessar ou modificar dados pertencentes a um Tenant B.

**Cenário:**
- Cria dois tenants (A e B)
- Cria dois usuários admin (Admin A e Admin B)
- Cria um serviço no Tenant B
- Tenta acessar o serviço do Tenant B usando o token do Admin A
- Espera status HTTP 403 ou 404

### 2. Teste de Finalização de Transação
**Arquivo:** `test_critical_flows.py::test_transaction_finalization_with_promotion_and_fee`

**Objetivo:** Garantir que a lógica financeira esteja correta (promoção, custo, lucro).

**Cenário:**
- Cria um agendamento com um serviço que tenha custo fixo e esteja sob promoção ativa
- Finaliza a venda usando uma forma de pagamento com taxa (Cartão de Crédito com 5% de taxa)
- Verifica se `net_value`, `total_cost` e `total_profit` estão corretos

### 3. Teste de Relatórios do Caixa
**Arquivo:** `test_critical_flows.py::test_cash_summary_aggregation`

**Objetivo:** Garantir que o resumo financeiro agregue corretamente as transações e as despesas no período.

**Cenário:**
- Registra 2 Transações no dia de hoje
- Registra 1 Despesa no dia de hoje
- Testa a rota GET /cash-summary para o dia de hoje
- Verifica se o total do faturamento e despesas correspondem exatamente aos registros

### 4. Teste de Ordenação da Agenda
**Arquivo:** `test_critical_flows.py::test_appointment_ordering_by_start_datetime`

**Objetivo:** Garantir que a ordenação do GET /admin/appointments pela start_datetime (ASC) seja obrigatória.

**Cenário:**
- Cria 3 agendamentos no mesmo dia em horários aleatórios (15h, 9h, 17h)
- Chama a rota e garante que o primeiro agendamento na lista retornada seja o das 9h
- Verifica que a ordem está correta: 9h, 15h, 17h

## 🔧 Estrutura

```
tests/
├── __init__.py
├── conftest.py              # Fixtures compartilhadas
├── integration/
│   ├── __init__.py
│   └── test_critical_flows.py  # Testes de fluxos críticos
└── README.md
```

## 📌 Notas Importantes

1. **Isolamento de Dados:** Cada teste recebe uma sessão de banco de dados isolada. Os dados criados em um teste não afetam outros testes.

2. **Fixtures:** As fixtures em `conftest.py` criam dados de teste necessários (tenants, usuários, serviços, etc.) e são compartilhadas entre todos os testes.

3. **Tokens JWT:** Os tokens são gerados automaticamente pelas fixtures e podem ser usados para autenticação nas requisições de teste.

4. **Banco de Dados:** Por padrão, os testes usam o mesmo banco de dados configurado nas variáveis de ambiente. Para produção, considere usar um banco de dados de teste separado.

## ⚠️ Avisos

- Os testes criam dados reais no banco de dados. Certifique-se de estar usando um banco de teste ou de desenvolvimento.
- Os testes não fazem limpeza automática dos dados criados. Considere executar em um banco de dados de teste separado.

