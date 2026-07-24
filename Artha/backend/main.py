import os
import sys

# ── Exclude venv310 from uvicorn --reload watcher ──
# This prevents constant restarts when packages inside venv310 are touched.
if "--reload" in sys.argv or os.environ.get("UVICORN_RELOAD"):
    os.environ.setdefault("WATCHFILES_IGNORE_DIRS", "venv310,.venv,__pycache__,node_modules")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db

# Initialize DB on import (or use lifespan event)
init_db()

# -------- ROUTERS --------
from routers.auth_routes import router as auth_router
from routers.kyc_routes import router as kyc_router
from routers.loan_routes import router as loan_router
from routers.transaction_routes import router as transaction_router
from routers.repayment_routes import router as repayment_router
from routers.default_routes import router as default_router
from routers.audit_routes import router as audit_router
from routers import upload_routes
from admin.admin_routes import router as admin_router
from routers.borrower_router import router as borrower_router
from routers.cib_routes import router as cib_router
from routers.nchl_routes import router as nchl_router
from routers.credit_score_routes import router as credit_score_router


app = FastAPI(
    title="Artha P2P Lending Backend",
    description="P2P lending platform backend",
    version="1.0.0",
)

# -------- CORS --------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://localhost:5179",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
        "http://127.0.0.1:5178",
        "http://127.0.0.1:5179",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- REGISTER ROUTERS --------

from fastapi.staticfiles import StaticFiles
import os

app.include_router(auth_router)
app.include_router(kyc_router)
app.include_router(loan_router)
app.include_router(transaction_router)
app.include_router(repayment_router)
app.include_router(default_router)
app.include_router(audit_router)
app.include_router(upload_routes.router)
app.include_router(admin_router, prefix="/api", tags=["Admin Panel"])
app.include_router(borrower_router)
app.include_router(cib_router)
app.include_router(nchl_router)
app.include_router(credit_score_router)

# Serve uploads
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Serve generated PDFs
pdf_path = os.path.join(os.path.dirname(__file__), "generated_pdfs")
if not os.path.exists(pdf_path):
    os.makedirs(pdf_path)
app.mount("/pdfs", StaticFiles(directory=pdf_path), name="pdfs")



# -------- ROOT HEALTH CHECK --------

@app.get("/")
def root():
    return {
        "status": "running",
        "service": "Artha P2P Lending Backend"
    }
