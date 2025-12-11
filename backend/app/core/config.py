"""
Configurações centrais da aplicação.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/agendamento_db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID: Optional[str] = None  # ID do preço do plano de assinatura (ex: 'price_1234567890')
    
    # WhatsApp (Meta Cloud API)
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # File Uploads
    UPLOAD_DIR: str = "uploads"  # Diretório para armazenar uploads
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    @classmethod
    def parse_env_var(cls, field_name: str, raw_val: str) -> any:
        """Parse CORS_ORIGINS from JSON string in .env file."""
        if field_name == 'CORS_ORIGINS':
            import json
            try:
                return json.loads(raw_val)
            except json.JSONDecodeError:
                # Fallback: split by comma if not JSON
                return [origin.strip() for origin in raw_val.split(',')]
        return cls.json_schema_serialization_defaults_required.get(field_name, raw_val)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

