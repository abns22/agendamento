"""
Aplicação principal FastAPI.
"""
import sys
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base

# Log de inicialização
print("🚀 Iniciando aplicação FastAPI...")
print(f"📦 Python version: {sys.version}")
print(f"🔧 DATABASE_URL configurada: {'Sim' if settings.DATABASE_URL else 'Não'}")

# Importar routers
print("📥 Importando routers...")
try:
    from app.api.v1.endpoints.public_booking import router as public_booking_router
    from app.api.v1.endpoints.public_tenant import router as public_tenant_router
    from app.api.v1.endpoints.admin_services import router as admin_services_router
    from app.api.v1.endpoints.admin_agenda import router as admin_agenda_router
    from app.api.v1.endpoints.admin_appointments import router as admin_appointments_router
    from app.api.v1.endpoints.admin_billing import router as admin_billing_router
    from app.api.v1.endpoints.admin_tenant import router as admin_tenant_router
    from app.api.v1.endpoints.admin_config import router as admin_config_router
    from app.api.v1.endpoints.admin_upload import router as admin_upload_router
    from app.api.v1.endpoints.admin_dashboard import router as admin_dashboard_router
    from app.api.v1.endpoints.admin_payment_config import router as admin_payment_config_router
    from app.api.v1.endpoints.admin_reports import router as admin_reports_router
    from app.api.v1.endpoints.admin_expenses import router as admin_expenses_router
    from app.api.v1.endpoints.admin_debtors import router as admin_debtors_router
    from app.api.v1.endpoints.admin_stop_times import router as admin_stop_times_router
    from app.api.v1.endpoints.admin_clients import router as admin_clients_router
    from app.api.v1.endpoints.admin_product_categories import router as admin_product_categories_router
    from app.api.v1.endpoints.admin_products import router as admin_products_router
    from app.api.v1.endpoints.admin_inventory import router as admin_inventory_router
    from app.api.v1.endpoints.auth import router as auth_router
    from app.api.v1.endpoints.webhooks import router as webhooks_router
    from app.api.v1.endpoints.super_admin import router as super_admin_router
    print("✅ Todos os routers importados com sucesso!")
except Exception as e:
    print(f"❌ ERRO ao importar routers: {e}")
    print(traceback.format_exc())
    sys.exit(1)

try:
    app = FastAPI(
    title="Sistema de Agendamento - API",
    description="API para sistema de agendamento multi-tenant para estúdios de estética",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
    print("✅ Aplicação FastAPI criada com sucesso!")
except Exception as e:
    print(f"❌ ERRO ao criar aplicação FastAPI: {e}")
    print(traceback.format_exc())
    sys.exit(1)

# CORS - Configurar para permitir requisições do frontend
# Parse CORS_ORIGINS se for string JSON do .env
print(f"🔍 CORS_ORIGINS raw: {settings.CORS_ORIGINS}")
print(f"🔍 Tipo de CORS_ORIGINS: {type(settings.CORS_ORIGINS)}")

cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    import json
    try:
        # Tentar parsear como JSON primeiro
        cors_origins = json.loads(cors_origins)
        print(f"✅ CORS_ORIGINS parseado como JSON: {cors_origins}")
    except json.JSONDecodeError:
        # Se falhar, tentar split por vírgula
        cors_origins = [origin.strip() for origin in cors_origins.split(',')]
        print(f"✅ CORS_ORIGINS parseado como CSV: {cors_origins}")
    except Exception as e:
        print(f"❌ ERRO ao parsear CORS_ORIGINS: {e}")
        # Fallback: usar lista padrão
        cors_origins = ["https://agendamento-frontend-mpzb.onrender.com"]
        print(f"⚠️ Usando CORS_ORIGINS padrão: {cors_origins}")

# Garantir que é uma lista
if not isinstance(cors_origins, list):
    cors_origins = [str(cors_origins)]

# Garantir que a URL do frontend está sempre incluída
frontend_url = "https://agendamento-frontend-mpzb.onrender.com"
if frontend_url not in cors_origins:
    cors_origins.append(frontend_url)
    print(f"➕ Adicionando URL do frontend: {frontend_url}")

# Log para debug (remover em produção)
print(f"🌐 CORS Origins finais configurados: {cors_origins}")
print(f"🌐 Tipo final: {type(cors_origins)}")
print(f"🌐 Total de origens: {len(cors_origins)}")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight por 1 hora
)
print("✅ CORS Middleware configurado com sucesso!")

# Exception handler global para garantir CORS em erros
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler global para garantir que erros sempre retornem headers CORS."""
    import traceback
    print(f"❌ ERRO não tratado: {exc}")
    print(traceback.format_exc())
    
    # Retornar resposta JSON com headers CORS
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno do servidor: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handler para erros de validação com CORS."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Registrar routers
print("🔗 Registrando routers...")
try:
    app.include_router(
        public_booking_router,
        prefix="/api/v1"
    )

    app.include_router(
        public_tenant_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_services_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_agenda_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_appointments_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_billing_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_tenant_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_config_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_upload_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_dashboard_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_payment_config_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_reports_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_expenses_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_debtors_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_stop_times_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_clients_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_product_categories_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_products_router,
        prefix="/api/v1"
    )

    app.include_router(
        admin_inventory_router,
        prefix="/api/v1"
    )

    app.include_router(
        auth_router,
        prefix="/api/v1"
    )

    app.include_router(
        webhooks_router,
        prefix="/api/v1"
    )

    app.include_router(
        super_admin_router,
        prefix="/api/v1"
    )
    print("✅ Todos os routers registrados com sucesso!")
    print(f"📋 Total de rotas registradas: {len(app.routes)}")
except Exception as e:
    print(f"❌ ERRO ao registrar routers: {e}")
    print(traceback.format_exc())
    sys.exit(1)


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "message": "Sistema de Agendamento API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.on_event("startup")
async def startup_event():
    """Evento de inicialização: cria as tabelas do banco de dados se não existirem."""
    print("🔧 Inicializando banco de dados...")
    try:
        # Importar engine e Base novamente para garantir que estão disponíveis
        from app.core.database import engine, Base
        
        # Importar todos os modelos para garantir que estão registrados no Base.metadata
        from app.models import (
            Tenant, User, Service, ScheduleConfig, StopTime, Appointment,
            PaymentMethodConfig, PaymentInstallmentConfig, Transaction,
            PaymentEntry, Expense, Debtor, Client, ProductCategory, Product,
            StockEntry
        )
        
        # Criar todas as tabelas
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Tabelas do banco de dados verificadas/criadas com sucesso!")
    except Exception as e:
        print(f"❌ ERRO ao inicializar banco de dados: {e}")
        import traceback
        print(traceback.format_exc())
        # Não fazer raise para não impedir o servidor de iniciar
        # Mas logar o erro para diagnóstico


@app.post("/create-super-admin")
async def create_super_admin_endpoint():
    """
    Endpoint temporário para criar o primeiro Super Admin.
    ATENÇÃO: Remover este endpoint após criar o super admin por segurança!
    """
    from app.core.database import get_db
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole
    from app.models.tenant import Tenant
    from sqlalchemy import select
    
    # Dados do Super Admin
    email = "alfredo_gi@hotmail.com"
    password = "12031994@lF"
    
    async for db in get_db():
        try:
            # Verificar se o email já existe
            existing_user = await db.execute(
                select(User).where(User.email == email)
            )
            if existing_user.scalar_one_or_none():
                return {
                    "success": False,
                    "message": f"Email '{email}' já está em uso!"
                }
            
            # Buscar ou criar tenant para o super admin
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.slug == "super-admin")
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                tenant = Tenant(
                    slug="super-admin",
                    is_active=True
                )
                db.add(tenant)
                await db.flush()
            
            # Gerar hash da senha
            password_hash = get_password_hash(password)
            
            # Criar usuário Super Admin
            super_admin = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=password_hash,
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            
            db.add(super_admin)
            await db.commit()
            await db.refresh(super_admin)
            await db.refresh(tenant)
            
            return {
                "success": True,
                "message": "Super Admin criado com sucesso!",
                "data": {
                    "id": super_admin.id,
                    "email": super_admin.email,
                    "role": super_admin.role.value,
                    "tenant_id": super_admin.tenant_id,
                    "tenant_slug": tenant.slug
                }
            }
        except Exception as e:
            await db.rollback()
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ ERRO ao criar Super Admin: {e}")
            print(error_trace)
            return {
                "success": False,
                "message": f"Erro ao criar Super Admin: {str(e)}",
                "error": error_trace
            }
        finally:
            break  # Sair do loop async for


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

