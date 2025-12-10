"""
Utilitários de segurança: hash de senha, JWT tokens, etc.
"""
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Configurar CryptContext com bcrypt
# Usar configuração compatível com versões mais recentes do bcrypt
try:
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
        bcrypt__rounds=12,
    )
except Exception as e:
    logger.warning(f"Erro ao configurar CryptContext: {e}, usando configuração padrão")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha plain corresponde ao hash."""
    try:
        # Limitar senha a 72 bytes (limite do bcrypt)
        if len(plain_password.encode('utf-8')) > 72:
            logger.warning("Senha muito longa, truncando para 72 bytes")
            plain_password = plain_password[:72]
        
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, Exception) as e:
        logger.error(f"Erro ao verificar senha: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """Gera o hash bcrypt da senha."""
    # Limitar senha a 72 bytes (limite do bcrypt)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        logger.warning(f"Senha muito longa ({len(password_bytes)} bytes), truncando para 72 bytes")
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um JWT token de acesso."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Cria um JWT refresh token (válido por 7 dias)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decodifica e valida um JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Payload do token decodificado
        
    Raises:
        JWTError: Se o token for inválido ou expirado
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise

