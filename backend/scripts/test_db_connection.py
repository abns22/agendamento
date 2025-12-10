"""
Script para testar conexão com o banco de dados MySQL.

Execute este script para verificar se o banco está acessível e funcionando.
"""
import asyncio
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Garantir que o .env seja carregado do diretório backend
os.chdir(backend_dir)

# Forçar recarregamento do .env
from dotenv import load_dotenv
load_dotenv(backend_dir / '.env')

from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text


async def test_connection():
    """Testa a conexão com o banco de dados."""
    print("=" * 60)
    print("🔍 Teste de Conexão com Banco de Dados")
    print("=" * 60)
    print()
    
    # Mostrar configuração
    print("📋 Configuração:")
    print(f"   DATABASE_URL: {settings.DATABASE_URL}")
    print()
    
    # Ocultar senha na exibição
    db_url_display = settings.DATABASE_URL
    if '@' in db_url_display:
        parts = db_url_display.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split('://')[1] if '://' in parts[0] else parts[0]
            if ':' in user_pass:
                user, _ = user_pass.split(':', 1)
                db_url_display = db_url_display.replace(user_pass, f"{user}:***")
    print(f"   (URL com senha oculta: {db_url_display})")
    print()
    
    try:
        print("🔄 Tentando conectar ao banco de dados...")
        
        # Testar conexão
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                print("✅ Conexão estabelecida com sucesso!")
                print()
                
                # Testar versão do MySQL
                print("📊 Informações do Banco:")
                try:
                    version_result = await conn.execute(text("SELECT VERSION()"))
                    version = version_result.fetchone()[0]
                    print(f"   Versão MySQL: {version}")
                except Exception as e:
                    print(f"   ⚠️ Não foi possível obter versão: {e}")
                
                # Testar banco atual
                try:
                    db_result = await conn.execute(text("SELECT DATABASE()"))
                    current_db = db_result.fetchone()[0]
                    print(f"   Banco atual: {current_db}")
                except Exception as e:
                    print(f"   ⚠️ Não foi possível obter banco atual: {e}")
                
                # Testar se o banco agendamento_db existe
                try:
                    db_check = await conn.execute(
                        text("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'agendamento_db'")
                    )
                    db_exists = db_check.fetchone()
                    if db_exists:
                        print("   ✅ Banco 'agendamento_db' existe")
                    else:
                        print("   ❌ Banco 'agendamento_db' NÃO existe")
                        print("   💡 Execute: CREATE DATABASE agendamento_db;")
                except Exception as e:
                    print(f"   ⚠️ Não foi possível verificar banco: {e}")
                
                print()
                print("=" * 60)
                print("✅ Teste concluído com sucesso!")
                print("=" * 60)
                return True
            else:
                print("❌ Conexão estabelecida, mas teste falhou")
                return False
                
    except Exception as e:
        print()
        print("❌ Erro ao conectar ao banco de dados:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        print()
        
        # Diagnóstico de erros comuns
        error_msg = str(e).lower()
        
        if "access denied" in error_msg or "1045" in error_msg:
            print("💡 Problema: Credenciais incorretas")
            print("   Verifique usuário e senha no arquivo .env")
            print("   Exemplo: DATABASE_URL=mysql+aiomysql://usuario:senha@localhost:3306/agendamento_db")
        elif "can't connect" in error_msg or "2003" in error_msg or "10061" in error_msg:
            print("💡 Problema: MySQL não está rodando ou não está acessível")
            print("   Verifique se o MySQL está rodando:")
            print("   1. Abra o MySQL Workbench")
            print("   2. Ou execute: net start MySQL (Windows)")
            print("   3. Ou verifique os serviços do Windows")
        elif "unknown database" in error_msg or "1049" in error_msg:
            print("💡 Problema: Banco de dados não existe")
            print("   Execute: CREATE DATABASE agendamento_db;")
        elif "connection refused" in error_msg:
            print("💡 Problema: Porta incorreta ou MySQL não está escutando")
            print("   Verifique se a porta no .env está correta (padrão: 3306)")
        
        print()
        print("=" * 60)
        print("❌ Teste falhou")
        print("=" * 60)
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(test_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Teste cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        sys.exit(1)

