import os
import tempfile
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from src import config
from src.auth import (
    init_db, register_user, authenticate_user, create_access_token,
    decode_access_token, get_user_quota_info, check_and_consume_quota,
    get_pending_users, update_user_status, delete_user, get_all_users,
    change_user_password, reset_user_password_by_admin, update_user_role
)
from src.vectorstore import get_retriever
from src.graph import build_rag_graph, run_rag_workflow

# 啟動時初始化資料庫
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="LangGraph Adaptive RAG API",
    description="商業化 RAG 後端系統，提供身份認證、每日配額管制與自適應 RAG 問答服務",
    version="1.0.0",
    lifespan=lifespan
)

# 跨域設定 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# --- Pydantic Data Models ---
class UserRegisterRequest(BaseModel):
    username: str
    password: str

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserReviewRequest(BaseModel):
    username: str
    action: str  # "approve" 或 "reject"

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class AdminResetPasswordRequest(BaseModel):
    username: str
    new_password: str

class AdminUpdateRoleRequest(BaseModel):
    username: str
    role: str  # "admin" 或 "user"

class RAGChatRequest(BaseModel):
    question: str
    provider: str = config.DEFAULT_PROVIDER
    k: int = 3
    enable_web_search: bool = False
    file_paths: Optional[List[str]] = None

# --- Dependency: 驗證 JWT Token ---
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效或過期的認證憑證 (Token)，請重新登入",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

# --- Endpoints ---

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "LangGraph RAG Backend"}

@app.post("/api/auth/register")
def register(req: UserRegisterRequest):
    success, msg = register_user(req.username, req.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"message": msg}

@app.post("/api/auth/login")
def login(req: UserLoginRequest):
    user, msg = authenticate_user(req.username, req.password)
    if not user:
        status_code = status.HTTP_403_FORBIDDEN if ("等待" in msg or "停用" in msg) else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(
            status_code=status_code,
            detail=msg
        )
    access_token = create_access_token(data={"sub": user["username"], "user_id": user["id"], "role": user["role"]})
    quota_info = get_user_quota_info(user["id"], user["username"], user["role"])
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
        "quota": quota_info
    }

@app.get("/api/admin/users/pending")
def list_pending(current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅限管理員存取")
    pending = get_pending_users()
    return {"pending_users": pending}

@app.post("/api/admin/users/review")
def review_user_endpoint(req: UserReviewRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅限管理員存取")
    status_val = "approved" if req.action.lower() == "approve" else "rejected"
    success, msg = update_user_status(req.username, status_val)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"message": msg}

@app.delete("/api/admin/users/{username}")
def delete_user_endpoint(username: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅限管理員存取")
    success, msg = delete_user(username)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"message": msg}

@app.get("/api/user/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    username = current_user.get("sub")
    role = current_user.get("role", "user")
    quota = get_user_quota_info(user_id, username, role)
    return {
        "user_id": user_id,
        "username": username,
        "role": role,
        "quota": quota
    }

@app.get("/api/users/all")
def list_all_users_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅限管理員存取使用者列表")
    users = get_all_users()
    return {"users": users}

@app.post("/api/user/change-password")
def change_password_endpoint(req: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    username = current_user.get("sub")
    success, msg = change_user_password(username, req.old_password, req.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"message": msg}

@app.post("/api/admin/users/reset-password")
def reset_password_endpoint(req: AdminResetPasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅限管理員存取")
    success, msg = reset_user_password_by_admin(req.username, req.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"message": msg}

@app.post("/api/admin/users/role")
def update_role_endpoint(req: AdminUpdateRoleRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅限管理員存取")
    success, msg = update_user_role(req.username, req.role)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"message": msg}

@app.post("/api/rag/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    上傳自訂文件 (PDF/TXT/MD) 並儲存至伺服器
    """
    upload_dir = os.path.join(config.DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_paths = []
    for file in files:
        file_path = os.path.join(upload_dir, file.filename)
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        saved_paths.append(file_path)
        
    return {
        "message": f"成功上傳 {len(saved_paths)} 個檔案",
        "file_paths": saved_paths
    }

@app.post("/api/rag/chat")
def rag_chat(
    req: RAGChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user.get("user_id")
    username = current_user.get("sub")
    role = current_user.get("role", "user")
    
    # 1. 檢查並扣減每日配額
    allowed, quota_info = check_and_consume_quota(user_id, username, role)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"已達到今日免費提問額度上限 ({quota_info['limit']} 次)，請明日再試或聯繫管理員。"
        )
        
    # 2. 確定文件路徑
    if req.file_paths:
        active_files = req.file_paths
    else:
        upload_dir = os.path.join(config.DATA_DIR, "uploads")
        if os.path.exists(upload_dir):
            active_files = [os.path.join(upload_dir, f) for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f)) and not f.startswith(".")]
        else:
            active_files = []
            
        if not active_files and os.path.exists(config.DEFAULT_PDF_PATH):
            active_files = [config.DEFAULT_PDF_PATH]

    if not active_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="目前系統中無可用文件，請先上傳 PDF / TXT 檔案建置知識庫。"
        )
    
    # 3. 初始化 RAG 檢索器與 LangGraph 工作流
    try:
        retriever = get_retriever(active_files, provider=req.provider, k=req.k)
        graph_app = build_rag_graph(retriever=retriever, provider=req.provider, enable_web_search=req.enable_web_search)
        
        # 4. 執行問答
        result = run_rag_workflow(graph_app, req.question)
        
        # 5. 序列化參考文件
        raw_docs = result.get("documents", [])
        serializable_docs = []
        for doc in raw_docs:
            if hasattr(doc, "page_content"):
                serializable_docs.append({
                    "page_content": doc.page_content,
                    "metadata": getattr(doc, "metadata", {})
                })
            elif isinstance(doc, dict):
                serializable_docs.append(doc)
                
        return {
            "answer": result.get("generation", "無生成解答"),
            "trace": result.get("trace", []),
            "documents": serializable_docs,
            "quota": quota_info
        }
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "unauthorized" in err_msg.lower():
            detail_msg = f"Ollama 遠端認證失敗 (401 Unauthorized)。請在 .env 中填入有效的 OLLAMA_API_KEY 金鑰，或調整 OLLAMA_BASE_URL。原始錯誤: {err_msg}"
        elif "connection" in err_msg.lower() or "refused" in err_msg.lower():
            detail_msg = f"無法連線至 Ollama 伺服器 ({config.OLLAMA_BASE_URL})。請確認服務是否開啟或網址是否正確。原始錯誤: {err_msg}"
        else:
            detail_msg = f"RAG 工作流執行失敗: {err_msg}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg
        )
