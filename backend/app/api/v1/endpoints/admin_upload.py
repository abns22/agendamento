"""
Endpoints para upload de arquivos (logos, etc).
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import uuid
import shutil
import logging
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user, get_current_active_tenant
from app.core.config import settings
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter(prefix="/admin/upload", tags=["Admin - Upload"])

logger = logging.getLogger(__name__)

# Criar diretório de uploads se não existir
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOGO_DIR = UPLOAD_DIR / "logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)


def get_file_extension(content_type: str) -> str:
    """Retorna a extensão do arquivo baseado no content-type."""
    extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp"
    }
    return extensions.get(content_type, ".jpg")


@router.post(
    "/logo",
    summary="Upload de logo do tenant",
    description="Faz upload da logo do estúdio e retorna a URL para salvar no tenant."
)
async def upload_logo(
    file: UploadFile = File(..., description="Arquivo de imagem (JPEG, PNG, GIF, WebP)"),
    current_user: User = Depends(get_current_admin_user),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Faz upload da logo do tenant.
    
    Validações:
    - Tipo de arquivo: apenas imagens (JPEG, PNG, GIF, WebP)
    - Tamanho máximo: 5MB
    - Gera nome único para evitar conflitos
    
    Args:
        file: Arquivo de imagem a ser enviado
        current_user: Usuário autenticado
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        dict: URL da logo salva (relativa ou absoluta)
        
    Raises:
        HTTPException 400: Se o arquivo for inválido
        HTTPException 500: Erro ao salvar arquivo
    """
    try:
        # Validar tipo de arquivo
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de arquivo não permitido. Use: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
            )
        
        # Ler conteúdo do arquivo
        contents = await file.read()
        
        # Validar tamanho
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo muito grande. Tamanho máximo: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
            )
        
        # Gerar nome único para o arquivo
        file_extension = get_file_extension(file.content_type)
        unique_filename = f"{tenant.id}_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = LOGO_DIR / unique_filename
        
        # Salvar arquivo
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Gerar URL relativa (será servida pelo endpoint /admin/upload/logo/{filename})
        logo_url = f"/api/v1/admin/upload/logo/{unique_filename}"
        
        logger.info(
            f"Logo uploadada por {current_user.email} para tenant {tenant.slug}: {unique_filename}"
        )
        
        return {
            "logo_url": logo_url,
            "filename": unique_filename,
            "size": len(contents),
            "content_type": file.content_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer upload de logo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer upload: {str(e)}"
        )


@router.get(
    "/logo/{filename}",
    summary="Obter logo do tenant",
    description="Retorna o arquivo de logo pelo nome do arquivo."
)
async def get_logo(
    filename: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna o arquivo de logo.
    
    Args:
        filename: Nome do arquivo da logo
        db: Sessão do banco de dados
        
    Returns:
        FileResponse: Arquivo de imagem
        
    Raises:
        HTTPException 404: Se o arquivo não existir
    """
    file_path = LOGO_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Logo não encontrada"
        )
    
    # Determinar content-type pela extensão
    content_type = "image/jpeg"  # padrão
    if filename.endswith(".png"):
        content_type = "image/png"
    elif filename.endswith(".gif"):
        content_type = "image/gif"
    elif filename.endswith(".webp"):
        content_type = "image/webp"
    
    return FileResponse(
        file_path,
        media_type=content_type,
        filename=filename
    )

