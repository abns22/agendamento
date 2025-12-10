"""
Script SIMPLES para criar Super Admin - Gera apenas o hash da senha.

Use este script se o script principal não funcionar.
Ele apenas gera o hash da senha para você inserir manualmente no banco.
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import get_password_hash
import uuid

def main():
    print("=" * 60)
    print("GERADOR DE HASH PARA SUPER ADMIN")
    print("=" * 60)
    print()
    print("Este script gera o hash da senha para você inserir")
    print("manualmente no banco de dados via MySQL Workbench.")
    print()
    
    email = input("Email do Super Admin: ").strip()
    if not email:
        print("❌ Email é obrigatório!")
        return
    
    password = input("Senha do Super Admin (mínimo 8 caracteres): ").strip()
    if len(password) < 8:
        print("❌ Senha deve ter no mínimo 8 caracteres!")
        return
    
    print()
    print("Gerando hash da senha...")
    
    try:
        password_hash = get_password_hash(password)
    except Exception as e:
        print(f"❌ Erro ao gerar hash: {str(e)}")
        print()
        print("Tentando método alternativo...")
        # Método alternativo usando bcrypt diretamente
        try:
            import bcrypt
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            print("✅ Hash gerado com método alternativo")
        except ImportError:
            print("❌ bcrypt não disponível. Instale: pip install bcrypt")
            return
        except Exception as e2:
            print(f"❌ Erro no método alternativo: {str(e2)}")
            return
    
    print()
    print("=" * 60)
    print("SQL PARA CRIAR SUPER ADMIN")
    print("=" * 60)
    print()
    print("Execute este SQL no MySQL Workbench:")
    print()
    print("-- 1. Criar tenant para super admin (se não existir)")
    print("INSERT INTO tenants (id, slug, is_active)")
    print("VALUES (")
    print(f"  '{str(uuid.uuid4())}',")
    print("  'super-admin',")
    print("  true")
    print(")")
    print("ON DUPLICATE KEY UPDATE slug = slug;")
    print()
    print("-- 2. Criar usuário super admin")
    print("INSERT INTO users (id, tenant_id, email, password_hash, role, is_active)")
    print("VALUES (")
    print(f"  '{str(uuid.uuid4())}',")
    print("  (SELECT id FROM tenants WHERE slug = 'super-admin' LIMIT 1),")
    print(f"  '{email}',")
    print(f"  '{password_hash}',")
    print("  'SUPER_ADMIN',")
    print("  true")
    print(");")
    print()
    print("=" * 60)
    print()
    print("✅ SQL gerado com sucesso!")
    print("   Copie e cole no MySQL Workbench para executar.")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

