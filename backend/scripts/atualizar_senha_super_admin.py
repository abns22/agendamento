"""
Script para atualizar a senha do Super Admin no banco de dados.

Use este script se o hash da senha estiver corrompido ou incompatível.
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

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy import select


async def atualizar_senha():
    """Atualiza a senha do Super Admin."""
    print("=" * 60)
    print("🔐 Atualizar Senha do Super Admin")
    print("=" * 60)
    print()
    
    # Solicitar email
    email = input("Digite o email do Super Admin: ").strip()
    if not email:
        print("❌ Email não pode estar vazio")
        return False
    
    # Solicitar nova senha
    senha = input("Digite a nova senha: ").strip()
    if not senha:
        print("❌ Senha não pode estar vazia")
        return False
    
    if len(senha) < 8:
        print("⚠️ Aviso: Senha deve ter no mínimo 8 caracteres")
        confirmar = input("Continuar mesmo assim? (s/N): ").strip().lower()
        if confirmar != 's':
            return False
    
    try:
        async with AsyncSessionLocal() as db:
            # Buscar usuário
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ Usuário com email '{email}' não encontrado")
                return False
            
            print(f"✅ Usuário encontrado: {user.email} (Role: {user.role.value})")
            print()
            print("🔄 Gerando novo hash da senha...")
            
            # Limitar senha a 72 bytes (limite do bcrypt)
            senha_bytes = senha.encode('utf-8')
            if len(senha_bytes) > 72:
                print(f"⚠️ Aviso: Senha tem {len(senha_bytes)} bytes, truncando para 72 bytes")
                senha = senha_bytes[:72].decode('utf-8', errors='ignore')
            
            # Gerar novo hash
            novo_hash = get_password_hash(senha)
            
            # Atualizar senha
            user.password_hash = novo_hash
            await db.commit()
            await db.refresh(user)
            
            print("✅ Senha atualizada com sucesso!")
            print()
            print("=" * 60)
            print("✅ Operação concluída!")
            print("=" * 60)
            return True
            
    except Exception as e:
        print()
        print(f"❌ Erro ao atualizar senha: {str(e)}")
        print()
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(atualizar_senha())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        sys.exit(1)

