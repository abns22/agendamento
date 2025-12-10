"""
Script auxiliar para gerar hash de senha.

Útil para criar usuários manualmente no banco de dados.

Uso:
    python scripts/generate_password_hash.py
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import get_password_hash


def main():
    print("=" * 60)
    print("GERADOR DE HASH DE SENHA")
    print("=" * 60)
    print()
    
    password = input("Digite a senha para gerar o hash: ").strip()
    
    if not password:
        print("❌ Senha não pode estar vazia!")
        return
    
    if len(password) < 8:
        print("⚠️  Aviso: Senha com menos de 8 caracteres")
        response = input("Deseja continuar mesmo assim? (s/N): ").strip().lower()
        if response != 's':
            print("❌ Operação cancelada")
            return
    
    print()
    print("Gerando hash...")
    
    password_hash = get_password_hash(password)
    
    print()
    print("=" * 60)
    print("HASH GERADO")
    print("=" * 60)
    print()
    print("Senha original:", password)
    print()
    print("Hash (use este valor no banco de dados):")
    print(password_hash)
    print()
    print("=" * 60)
    print()
    print("Exemplo de SQL para criar usuário:")
    print("-" * 60)
    print(f"INSERT INTO users (id, tenant_id, email, password_hash, role, is_active)")
    print(f"VALUES (")
    print(f"  UUID(),")
    print(f"  'tenant-id-aqui',")
    print(f"  'email@example.com',")
    print(f"  '{password_hash}',")
    print(f"  'SUPER_ADMIN',")
    print(f"  true")
    print(f");")
    print("-" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

