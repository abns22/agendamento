# Componentes UI (Mobile-First)

Componentes reutilizáveis otimizados para dispositivos móveis.

## Componentes Disponíveis

### Button

Botão reutilizável com variantes primária e secundária.

```jsx
import { Button } from '@/components/ui'

// Botão primário (padrão)
<Button onClick={handleClick}>Clique aqui</Button>

// Botão secundário
<Button variant="secondary" onClick={handleClick}>Cancelar</Button>

// Botão de submit
<Button type="submit" variant="primary">Enviar</Button>

// Botão desabilitado
<Button disabled={isLoading}>Carregando...</Button>
```

**Props:**
- `variant`: `'primary'` | `'secondary'` (padrão: `'primary'`)
- `type`: `'button'` | `'submit'` | `'reset'` (padrão: `'button'`)
- `disabled`: `boolean` (padrão: `false`)
- `onClick`: `function`
- `className`: `string` (classes CSS adicionais)

**Características Mobile-First:**
- Largura total (`w-full`) no mobile
- Padding otimizado (`py-4 px-6`)
- Alto contraste
- Feedback visual (hover/active)

---

### Card

Container de card com sombra e bordas arredondadas.

```jsx
import { Card } from '@/components/ui'

<Card>
  <h3>Título</h3>
  <p>Conteúdo do card</p>
</Card>
```

**Props:**
- `children`: `React.ReactNode`
- `className`: `string` (classes CSS adicionais)

**Características Mobile-First:**
- Largura total (`w-full`) no mobile
- Sombra sutil
- Padding otimizado (`p-4` no mobile, `p-6` em telas maiores)
- Bordas arredondadas (`rounded-xl`)

---

### TimePill

Pílula de horário para exibir slots de tempo.

```jsx
import { TimePill, TimePillGrid } from '@/components/ui'

// Pílula individual
<TimePill 
  time="14:30" 
  selected={isSelected}
  onClick={handleClick}
/>

// Grid de pílulas (3 colunas no mobile, 4 em telas maiores)
<TimePillGrid>
  <TimePill time="09:00" onClick={() => selectTime('09:00')} />
  <TimePill time="10:00" onClick={() => selectTime('10:00')} />
  <TimePill time="11:00" onClick={() => selectTime('11:00')} />
  <TimePill time="14:00" selected={selectedTime === '14:00'} onClick={() => selectTime('14:00')} />
</TimePillGrid>
```

**Props (TimePill):**
- `time`: `string` (formato "HH:MM")
- `selected`: `boolean` (padrão: `false`)
- `disabled`: `boolean` (padrão: `false`)
- `onClick`: `function`
- `className`: `string` (classes CSS adicionais)

**Props (TimePillGrid):**
- `children`: `React.ReactNode` (TimePill components)
- `className`: `string` (classes CSS adicionais)

**Características Mobile-First:**
- Grid responsivo (3 colunas no mobile, 4 em telas maiores)
- Feedback visual claro (hover/clique)
- Estados: normal, selecionado, desabilitado

---

### LoginCard

Formulário de login completo usando Card como container.

```jsx
import { LoginCard } from '@/components/ui'

<LoginCard
  onSubmit={async ({ email, password }) => {
    // Fazer login
    await login(email, password)
  }}
  isLoading={isLoading}
  error={errorMessage}
/>
```

**Props:**
- `onSubmit`: `function({ email, password })` - Handler de submit
- `isLoading`: `boolean` (padrão: `false`)
- `error`: `string` | `null` - Mensagem de erro externa
- `className`: `string` (classes CSS adicionais)

**Características Mobile-First:**
- Usa Card como container
- Campos de email e senha
- Validação básica (email format, campos obrigatórios)
- Feedback visual (erros, loading)
- Botão de submit usando Button component

---

## Exemplo Completo

```jsx
import React, { useState } from 'react'
import { Button, Card, TimePill, TimePillGrid, LoginCard } from '@/components/ui'

function MyComponent() {
  const [selectedTime, setSelectedTime] = useState(null)
  
  const handleLogin = async ({ email, password }) => {
    // Fazer login
    console.log('Login:', email, password)
  }
  
  return (
    <div className="p-4 space-y-6">
      {/* Login Card */}
      <LoginCard
        onSubmit={handleLogin}
        isLoading={false}
      />
      
      {/* Card com conteúdo */}
      <Card>
        <h2 className="text-xl font-bold mb-4">Selecione um horário</h2>
        
        <TimePillGrid>
          <TimePill 
            time="09:00" 
            selected={selectedTime === '09:00'}
            onClick={() => setSelectedTime('09:00')}
          />
          <TimePill 
            time="10:00" 
            selected={selectedTime === '10:00'}
            onClick={() => setSelectedTime('10:00')}
          />
          <TimePill 
            time="11:00" 
            selected={selectedTime === '11:00'}
            onClick={() => setSelectedTime('11:00')}
          />
        </TimePillGrid>
        
        <div className="mt-6">
          <Button onClick={() => console.log('Confirmar')}>
            Confirmar Agendamento
          </Button>
        </div>
      </Card>
    </div>
  )
}
```

---

## Design Mobile-First

Todos os componentes seguem os princípios Mobile-First:

1. **Largura Total**: Componentes ocupam 100% da largura no mobile
2. **Padding Otimizado**: Espaçamento adequado para toque (`py-4`, `px-6`)
3. **Alto Contraste**: Cores com boa legibilidade
4. **Feedback Visual**: Estados hover/active claros
5. **Responsivo**: Adapta-se a telas maiores usando `sm:`, `md:`, etc.

---

## Paleta de Cores

Os componentes usam as cores definidas em `tailwind.config.js`:

- **Primary**: `#004B6B`
- **Success**: `#2ECC71`
- **Highlight**: `#F39C12`
- **Neutral Light**: `#F4F4F4`
- **Neutral Dark**: `#2C3E50`
- **Text**: `#333333`

