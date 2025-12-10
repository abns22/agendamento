# Script PowerShell para Configurar Git e GitHub
# Execute: .\configurar-git.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuração do Git para GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se Git está instalado
$gitPath = Get-Command git -ErrorAction SilentlyContinue

if (-not $gitPath) {
    Write-Host "❌ Git não encontrado no PATH!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Tentando encontrar Git em locais comuns..." -ForegroundColor Yellow
    
    $possiblePaths = @(
        "C:\Program Files\Git\bin\git.exe",
        "C:\Program Files (x86)\Git\bin\git.exe",
        "$env:LOCALAPPDATA\Programs\Git\bin\git.exe"
    )
    
    $foundGit = $null
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $foundGit = $path
            Write-Host "✅ Git encontrado em: $path" -ForegroundColor Green
            break
        }
    }
    
    if (-not $foundGit) {
        Write-Host "❌ Git não encontrado. Por favor, instale o Git primeiro." -ForegroundColor Red
        Write-Host "Download: https://git-scm.com/download/win" -ForegroundColor Yellow
        exit 1
    }
    
    # Adicionar ao PATH temporariamente
    $env:Path += ";$(Split-Path $foundGit -Parent)"
    Write-Host "✅ Git adicionado ao PATH desta sessão" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ Git está disponível!" -ForegroundColor Green
Write-Host "Versão: $(git --version)" -ForegroundColor Cyan
Write-Host ""

# Verificar se já é um repositório Git
if (Test-Path .git) {
    Write-Host "⚠️  Repositório Git já inicializado" -ForegroundColor Yellow
    $continue = Read-Host "Deseja continuar mesmo assim? (s/n)"
    if ($continue -ne "s" -and $continue -ne "S") {
        exit 0
    }
} else {
    Write-Host "Inicializando repositório Git..." -ForegroundColor Cyan
    git init
    Write-Host "✅ Repositório inicializado" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuração do Git (Nome e Email)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$currentName = git config --global user.name
$currentEmail = git config --global user.email

if ($currentName) {
    Write-Host "Nome atual: $currentName" -ForegroundColor Cyan
}
if ($currentEmail) {
    Write-Host "Email atual: $currentEmail" -ForegroundColor Cyan
}

Write-Host ""
$configure = Read-Host "Deseja configurar/alterar nome e email? (s/n)"

if ($configure -eq "s" -or $configure -eq "S") {
    $name = Read-Host "Digite seu nome completo"
    $email = Read-Host "Digite seu email do GitHub"
    
    git config --global user.name "$name"
    git config --global user.email "$email"
    
    Write-Host "✅ Configuração salva!" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Adicionar Arquivos ao Git" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verificando .gitignore..." -ForegroundColor Cyan
if (Test-Path .gitignore) {
    Write-Host "✅ .gitignore encontrado" -ForegroundColor Green
} else {
    Write-Host "⚠️  .gitignore não encontrado!" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Adicionando arquivos ao staging..." -ForegroundColor Cyan
git add .

Write-Host ""
Write-Host "Status dos arquivos:" -ForegroundColor Cyan
git status --short | Select-Object -First 20

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configurar Remote do GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$repoName = Read-Host "Digite o nome do repositório no GitHub (ex: sistema-agendamento-horario)"

# Verificar se remote já existe
$remoteExists = git remote get-url origin -ErrorAction SilentlyContinue

if ($remoteExists) {
    Write-Host "⚠️  Remote 'origin' já configurado: $remoteExists" -ForegroundColor Yellow
    $change = Read-Host "Deseja alterar? (s/n)"
    if ($change -eq "s" -or $change -eq "S") {
        git remote set-url origin "https://github.com/abns22/$repoName.git"
        Write-Host "✅ Remote atualizado!" -ForegroundColor Green
    }
} else {
    git remote add origin "https://github.com/abns22/$repoName.git"
    Write-Host "✅ Remote adicionado!" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Próximos Passos" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Crie o repositório no GitHub:" -ForegroundColor Yellow
Write-Host "   https://github.com/new" -ForegroundColor White
Write-Host "   Nome: $repoName" -ForegroundColor White
Write-Host ""
Write-Host "2. Faça o commit inicial:" -ForegroundColor Yellow
Write-Host "   git commit -m 'Initial commit: Sistema de Agendamento Multi-Tenant'" -ForegroundColor White
Write-Host ""
Write-Host "3. Renomeie a branch para main:" -ForegroundColor Yellow
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host ""
Write-Host "4. Faça o push:" -ForegroundColor Yellow
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host "   (Use seu Personal Access Token como senha)" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ Configuração concluída!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green


