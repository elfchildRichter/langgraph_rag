import os
import requests
import streamlit as st

# --- 1. 頁面基本設定 ---
st.set_page_config(
    page_title="LangGraph Adaptive RAG 系統",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# 專業藍色科技風格 CSS 樣式系統 (Enterprise Blue Design System)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .block-container {
        padding-top: 3rem;
        padding-bottom: 2rem;
    }

    /* 主頁面背景質感與氛圍光 */
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 15% 15%, rgba(219, 234, 254, 0.45) 0%, rgba(239, 246, 255, 0.7) 35%, rgba(248, 250, 252, 1) 85%) !important;
    }

    /* 側邊欄專屬優雅質感 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 100%) !important;
        border-right: 1px solid #DBEAFE !important;
    }

    /* 藍色系專業漸層主標題 */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        line-height: 1.35;
        padding-top: 4px;
        padding-bottom: 4px;
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #0284C7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
    }
    
    /* 無外框精緻副標題 (加大字體) */
    .sub-header {
        font-size: 1.15rem;
        font-weight: 600;
        color: #475569;
        margin-top: -0.1rem;
        margin-bottom: 1.1rem;
        letter-spacing: 0.015em;
    }

    /* 當前檔案與模型狀態標籤列 */
    .doc-status-bar {
        font-size: 0.9rem;
        color: #1E3A8A;
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        padding: 6px 14px;
        margin-bottom: 1.2rem;
        display: inline-block;
    }

    /* 頂部頁籤 (Tabs) 高級藍色風格 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        padding: 0px 22px;
        font-weight: 600;
        font-size: 0.92rem;
        color: #64748B;
        border: none;
        transition: all 0.2s ease-in-out;
    }

    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #2563EB !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15), 0 1px 3px rgba(0,0,0,0.05) !important;
    }

    /* 藍色卡片容器 */
    .quota-card {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 1px solid #BFDBFE;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.06);
    }
    .quota-title {
        font-size: 0.8rem;
        color: #1E40AF;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .quota-number {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-top: 2px;
    }

    /* 狀態 Badge 樣式 */
    .badge-admin {
        background: linear-gradient(135deg, #1E40AF 0%, #2563EB 100%);
        color: #FFFFFF;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        box-shadow: 0 2px 4px rgba(30, 64, 175, 0.2);
    }
    .badge-user {
        background: linear-gradient(135deg, #0284C7 0%, #38BDF8 100%);
        color: #FFFFFF;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-approved {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        color: #FFFFFF;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-pending {
        background: linear-gradient(135deg, #D97706 0%, #F59E0B 100%);
        color: #FFFFFF;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-rejected {
        background: linear-gradient(135deg, #4B5563 0%, #6B7280 100%);
        color: #FFFFFF;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .user-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }

    /* 按鈕微調 */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Session State 初始化 ---
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = "user"
if "quota" not in st.session_state:
    st.session_state.quota = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_file_paths" not in st.session_state:
    st.session_state.uploaded_file_paths = []
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0
if "vector_index_status" not in st.session_state:
    st.session_state.vector_index_status = None

# --- 3. 工具函式 ---
def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

def refresh_user_profile():
    if not st.session_state.access_token:
        return
    try:
        res = requests.get(f"{BACKEND_URL}/api/user/me", headers=get_auth_headers(), timeout=5)
        if res.status_code == 200:
            data = res.json()
            st.session_state.username = data.get("username")
            st.session_state.role = data.get("role")
            st.session_state.quota = data.get("quota")
        else:
            st.session_state.access_token = None
    except Exception:
        pass

# --- 4. 認證畫面 (未登入) ---
if not st.session_state.access_token:
    _, col_center, _ = st.columns([1, 1.8, 1])
    with col_center:
        st.markdown('''
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <div class="main-header">🤖 企業級 LangGraph 自適應知識庫系統 (Alpha)</div>
            <div class="sub-header">Enterprise Adaptive & Corrective RAG AI Workspace</div>
        </div>
        ''', unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔐 帳號登入", "📝 註冊新帳號"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("帳號 (Username)")
                password = st.text_input("密碼 (Password)", type="password")
                submit = st.form_submit_button("登入系統", type="primary", use_container_width=True)

                if submit:
                    if not username or not password:
                        st.warning("請填寫帳號與密碼")
                    else:
                        try:
                            res = requests.post(
                                f"{BACKEND_URL}/api/auth/login",
                                json={"username": username, "password": password},
                                timeout=5
                            )
                            if res.status_code == 200:
                                data = res.json()
                                st.session_state.access_token = data.get("access_token")
                                st.session_state.username = data.get("username")
                                st.session_state.role = data.get("role")
                                st.session_state.quota = data.get("quota")
                                st.success(f"歡迎回來，{st.session_state.username}！")
                                st.rerun()
                            else:
                                detail = res.json().get("detail", "登入失敗")
                                st.error(f"❌ {detail}")
                        except Exception as e:
                            st.error(f"連線失敗: {str(e)}")

        with tab_register:
            st.caption("💡 新註冊帳號預設需經管理員核准後方可登入使用。")
            with st.form("register_form"):
                reg_user = st.text_input("新帳號名稱")
                reg_pass = st.text_input("設定密碼", type="password")
                reg_pass_confirm = st.text_input("確認密碼", type="password")
                if st.form_submit_button("完成註冊", type="secondary", use_container_width=True):
                    if not reg_user or not reg_pass:
                        st.warning("請完整填寫欄位")
                    elif reg_pass != reg_pass_confirm:
                        st.error("兩次輸入的密碼不一致")
                    else:
                        try:
                            res = requests.post(
                                f"{BACKEND_URL}/api/auth/register",
                                json={"username": reg_user, "password": reg_pass},
                                timeout=5
                            )
                            if res.status_code == 200:
                                msg = res.json().get("message", "註冊成功！帳號待審核中。")
                                st.info(f"📝 {msg}")
                            else:
                                detail = res.json().get("detail", "註冊失敗")
                                st.error(detail)
                        except Exception as e:
                            st.error(f"連線失敗: {str(e)}")
    st.stop()

# --- 5. 主系統介面 (已登入狀態) ---
refresh_user_profile()

# 簡潔側邊欄 (Sidebar)
with st.sidebar:
    role_badge = f'<span class="badge-admin">ADMIN</span>' if st.session_state.role == 'admin' else f'<span class="badge-user">USER</span>'
    st.markdown(f"### 👤 {st.session_state.username} {role_badge}", unsafe_allow_html=True)
    
    # 顯示配額資訊
    quota = st.session_state.quota or {}
    if quota.get("is_unlimited"):
        st.markdown("""
        <div class="quota-card">
            <div class="quota-title">每日提問額度</div>
            <div class="quota-number">♾️ 無限制</div>
            <small style="color: #94A3B8;">尊榮管理員全功能權限</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        rem = quota.get("remaining", 0)
        lim = quota.get("limit", 20)
        used = quota.get("used", 0)
        pct = min(1.0, max(0.0, used / lim if lim > 0 else 0))
        st.markdown(f"""
        <div class="quota-card">
            <div class="quota-title">今日剩餘提問次數</div>
            <div class="quota-number">{rem} <span style="font-size: 1rem; color: #94A3B8;">/ {lim} 次</span></div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(pct)

    if st.button("🚪 登出系統", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.username = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.subheader("⚙️ 系統模型與檢視設定")
    
    default_provider_env = os.getenv("LLM_PROVIDER", "ollama").lower()
    default_index = 0 if default_provider_env == "ollama" else 1
    provider_choice = st.radio(
        "LLM 模型提供者",
        options=["Ollama", "Google Gemini"],
        index=default_index,
        help="支援 Cloud API 或 Local / 遠端服務"
    )
    provider_key = "ollama" if provider_choice == "Ollama" else "google"

    retrieval_k = st.slider("向量檢索數量 (Top-K)", min_value=1, max_value=10, value=3)
    enable_web_search = st.checkbox("啟用網路搜尋 (DuckDuckGo Search)", value=False)
    show_trace = st.checkbox("顯示 LangGraph 節點 Trace", value=True)

# --- 6. 頂部頁面導覽頁籤 (Top Page Navigation Tabs) ---
if st.session_state.role == "admin":
    tab_chat, tab_account, tab_admin = st.tabs(["💬 RAG 智能問答", "🔑 個人帳號設定", "👥 統一用戶管理 (Admin)"])
else:
    tab_chat, tab_account = st.tabs(["💬 RAG 智能問答", "🔑 個人帳號設定"])
    tab_admin = None

# --- TAB 1: 💬 RAG 智能問答 ---
with tab_chat:
    st.markdown('<div class="main-header">🤖 企業級 LangGraph 自適應知識庫 (Alpha)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enterprise Adaptive & Corrective RAG AI Workspace</div>', unsafe_allow_html=True)
    
    if st.session_state.uploaded_file_paths:
        file_names = [os.path.basename(p) for p in st.session_state.uploaded_file_paths]
        file_info_text = ", ".join(file_names)
    else:
        file_info_text = "尚無選擇文件（請於下方上傳 PDF/TXT 檔案）"

    active_model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b") if provider_key == "ollama" else os.getenv("GOOGLE_MODEL", "gemini-3.6-flash")
    st.markdown(f'<div class="doc-status-bar">當前文件：<b>{file_info_text}</b> | 提供者：<b>{provider_choice}</b> | 模型：<b><code>{active_model_name}</code></b></div>', unsafe_allow_html=True)

    if st.session_state.vector_index_status:
        st.success(st.session_state.vector_index_status)

    # 文件上傳與向量庫區塊 (直接在智能問答頁面展示)
    st.markdown("##### 📂 上傳與切換自訂知識庫文件 (PDF / TXT / MD)")
    c_up1, c_up2 = st.columns([3, 1])
    with c_up1:
        uploaded_files = st.file_uploader(
            "選擇 PDF / TXT / MD 檔案",
            type=["pdf", "txt", "md"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.file_uploader_key}"
        )
    with c_up2:
        btn_build = st.button("🚀 建立向量索引", use_container_width=True)
        if st.session_state.uploaded_file_paths or st.session_state.messages:
            if st.button("🗑️ 清空文件與討論串", use_container_width=True):
                st.session_state.uploaded_file_paths = []
                st.session_state.messages = []
                st.session_state.vector_index_status = None
                st.session_state.file_uploader_key += 1
                st.toast("已清空所有上傳文件與對話紀錄", icon="🧹")
                st.rerun()

    if btn_build:
        if uploaded_files:
            with st.spinner("上傳檔案至後端伺服器並建置向量庫索引..."):
                try:
                    files_payload = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
                    res = requests.post(
                        f"{BACKEND_URL}/api/rag/upload",
                        headers=get_auth_headers(),
                        files=files_payload,
                        timeout=30
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.uploaded_file_paths = data.get("file_paths", [])
                        names_str = ", ".join([f.name for f in uploaded_files])
                        st.session_state.vector_index_status = f"✅ 向量索引建置成功！當前已載入知識庫：{names_str}"
                        st.toast("🎉 向量索引建置成功！", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.json().get("detail", "上傳失敗"))
                except Exception as e:
                    st.error(f"上傳發生錯誤: {str(e)}")
        else:
            st.info("請先選擇要上傳的檔案")

    # 渲染歷史訊息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("web_search_used"):
                st.info("🌐 **提示：本回覆已包含來自網路搜尋 (DuckDuckGo Search) 的即時資料**")
            if "trace" in message and show_trace and message["trace"]:
                with st.expander("檢視 LangGraph 執行軌跡 (Trace)"):
                    for t in message["trace"]:
                        st.text(t)
            if "docs" in message and message["docs"]:
                with st.expander("檢視參考資料來源"):
                    for idx, doc in enumerate(message["docs"], 1):
                        src = doc.get("metadata", {}).get("source", "未知來源")
                        st.markdown(f"**[{idx}] 來源: `{src}`**")
                        st.caption(doc.get("page_content", "")[:300] + "...")

    # 使用者輸入
    if prompt := st.chat_input("請輸入您的問題..."):
        quota = st.session_state.quota or {}
        if not quota.get("is_unlimited") and quota.get("remaining", 0) <= 0:
            st.error("❌ 您已達到今日免費提問額度上限 (20 次)，請明日再試或聯絡管理員。")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                status_box = st.status("呼叫獨立後端 REST API 執行 LangGraph 工作流...", expanded=True)
                
                try:
                    status_box.write("▶ 傳送請求至後端伺服器 (包含認證 Bearer Token)...")
                    payload = {
                        "question": prompt,
                        "provider": provider_key,
                        "k": retrieval_k,
                        "enable_web_search": enable_web_search,
                        "file_paths": st.session_state.uploaded_file_paths if st.session_state.uploaded_file_paths else None
                    }
                    
                    res = requests.post(
                        f"{BACKEND_URL}/api/rag/chat",
                        headers=get_auth_headers(),
                        json=payload,
                        timeout=120
                    )
                    
                    if res.status_code == 200:
                        data = res.json()
                        answer = data.get("answer", "無解答")
                        trace_logs = data.get("trace", [])
                        docs = data.get("documents", [])
                        new_quota = data.get("quota")
                        
                        if new_quota:
                            st.session_state.quota = new_quota

                        for log_line in trace_logs:
                            status_box.write(log_line)
                        status_box.update(label="後端 LangGraph 工作流執行完成", state="complete", expanded=False)

                        message_placeholder.markdown(answer)

                        # 判斷是否使用網路搜尋
                        has_web_search = enable_web_search or any("web_search" in str(t).lower() for t in trace_logs)
                        if has_web_search:
                            st.info("🌐 **提示：本回覆已包含來自網路搜尋 (DuckDuckGo Search) 的即時資料**")

                        if docs:
                            with st.expander("檢視參考資料來源"):
                                for idx, doc in enumerate(docs, 1):
                                    src = doc.get("metadata", {}).get("source", "未知來源")
                                    st.markdown(f"**[{idx}] 來源: `{src}`**")
                                    st.caption(doc.get("page_content", "")[:300] + "...")

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "trace": trace_logs,
                            "docs": docs,
                            "web_search_used": has_web_search
                        })
                    else:
                        detail = res.json().get("detail", "執行失敗")
                        status_box.update(label="後端執行發生錯誤", state="error", expanded=True)
                        st.error(f"發生錯誤 ({res.status_code}): {detail}")
                except Exception as e:
                    status_box.update(label="連線失敗", state="error", expanded=True)
                    st.error(f"連線後端 REST API 失敗: {str(e)}")

# --- TAB 2: 🔑 個人帳號設定 ---
with tab_account:
    st.markdown('<div class="main-header">🔑 個人帳號與安全設定</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Personal Account Profile & Security Management</div>', unsafe_allow_html=True)

    st.subheader("👤 個人帳號基本資料")
    c1, c2, c3 = st.columns(3)
    c1.metric("當前帳號", st.session_state.username)
    c2.metric("角色權限", "管理員 (Admin)" if st.session_state.role == "admin" else "一般使用者 (User)")
    q_rem = "♾️ 無限制" if (st.session_state.quota or {}).get("is_unlimited") else f"{(st.session_state.quota or {}).get('remaining', 0)} 次"
    c3.metric("今日剩餘提問次數", q_rem)

    st.markdown("---")
    st.subheader("🔑 變更個人密碼")
    with st.form("personal_change_pw_form"):
        old_p = st.text_input("輸入舊密碼", type="password")
        new_p = st.text_input("輸入新密碼 (至少 4 個字元)", type="password")
        confirm_p = st.text_input("再次確認新密碼", type="password")
        btn_pw = st.form_submit_button("確認更新密碼", type="primary")

        if btn_pw:
            if not old_p or not new_p:
                st.warning("請填寫完整密碼欄位")
            elif new_p != confirm_p:
                st.error("新密碼與確認密碼不一致")
            elif len(new_p) < 4:
                st.error("新密碼長度至少需 4 個字元")
            else:
                try:
                    res_pw = requests.post(
                        f"{BACKEND_URL}/api/user/change-password",
                        headers=get_auth_headers(),
                        json={"old_password": old_p, "new_password": new_p},
                        timeout=5
                    )
                    if res_pw.status_code == 200:
                        st.success("🎉 密碼已成功變更！請記住您的新密碼。")
                    else:
                        st.error(res_pw.json().get("detail", "變更密碼失敗"))
                except Exception as e:
                    st.error(f"連線失敗: {str(e)}")

# --- TAB 3: 👥 統一用戶管理 (Admin Only) ---
if tab_admin and st.session_state.role == "admin":
    with tab_admin:
        st.markdown('<div class="main-header">👥 統一使用者管理面板</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Unified User Access Control & Admin Governance Panel</div>', unsafe_allow_html=True)

        try:
            res_all = requests.get(f"{BACKEND_URL}/api/users/all", headers=get_auth_headers(), timeout=5)
            if res_all.status_code == 200:
                all_users = res_all.json().get("users", [])
                
                # 統計指標
                total_cnt = len(all_users)
                pending_cnt = sum(1 for u in all_users if u.get("status") == "pending")
                approved_cnt = sum(1 for u in all_users if u.get("status") == "approved")

                m1, m2, m3 = st.columns(3)
                m1.metric("總使用者數量", f"{total_cnt} 人")
                m2.metric("已核准帳號", f"{approved_cnt} 人")
                m3.metric("⏳ 待審核帳號", f"{pending_cnt} 人", delta_color="inverse")

                st.markdown("---")

                if not all_users:
                    st.info("目前資料庫中無任何使用者資料。")
                else:
                    for u in all_users:
                        u_name = u["username"]
                        u_role = u["role"]
                        u_status = u.get("status", "approved")
                        u_time = u.get("created_at", "")[:19]

                        # Status badge styling
                        if u_status == "approved":
                            status_html = '<span class="badge-approved">✅ 已核准</span>'
                        elif u_status == "pending":
                            status_html = '<span class="badge-pending">⏳ 待審核</span>'
                        else:
                            status_html = '<span class="badge-rejected">❌ 已拒絕</span>'

                        role_html = '<span class="badge-admin">👑 管理員</span>' if u_role == "admin" else '<span class="badge-user">👤 一般用戶</span>'

                        with st.container():
                            st.markdown(f"""
                            <div class="user-card">
                                <div><b>帳號</b>: <code>{u_name}</code> | <b>權限</b>: {role_html} | <b>狀態</b>: {status_html} | <small style="color:#64748B;">註冊時間: {u_time}</small></div>
                            </div>
                            """, unsafe_allow_html=True)

                            # 操作按鈕列
                            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 1.2])

                            # 1. 審核狀態操作
                            with btn_col1:
                                if u_status != "approved":
                                    if st.button("✅ 核准", key=f"app_btn_{u_name}", use_container_width=True):
                                        r = requests.post(f"{BACKEND_URL}/api/admin/users/review", headers=get_auth_headers(), json={"username": u_name, "action": "approve"})
                                        if r.status_code == 200:
                                            st.success(f"已核准 {u_name}")
                                            st.rerun()
                                        else:
                                            st.error(r.json().get("detail", "操作失敗"))
                                else:
                                    if st.button("❌ 拒絕", key=f"rej_btn_{u_name}", use_container_width=True):
                                        r = requests.post(f"{BACKEND_URL}/api/admin/users/review", headers=get_auth_headers(), json={"username": u_name, "action": "reject"})
                                        if r.status_code == 200:
                                            st.warning(f"已拒絕 {u_name}")
                                            st.rerun()
                                        else:
                                            st.error(r.json().get("detail", "操作失敗"))

                            # 2. 角色權限操作
                            with btn_col2:
                                if u_role == "user":
                                    if st.button("👑 升為管理員", key=f"role_up_{u_name}", use_container_width=True):
                                        r = requests.post(f"{BACKEND_URL}/api/admin/users/role", headers=get_auth_headers(), json={"username": u_name, "role": "admin"})
                                        if r.status_code == 200:
                                            st.success(f"已將 {u_name} 設為管理員")
                                            st.rerun()
                                        else:
                                            st.error(r.json().get("detail", "操作失敗"))
                                else:
                                    if u_name != "admin": # 保護主管理員
                                        if st.button("👤 降為一般用戶", key=f"role_down_{u_name}", use_container_width=True):
                                            r = requests.post(f"{BACKEND_URL}/api/admin/users/role", headers=get_auth_headers(), json={"username": u_name, "role": "user"})
                                            if r.status_code == 200:
                                                st.info(f"已將 {u_name} 降為一般用戶")
                                                st.rerun()
                                            else:
                                                st.error(r.json().get("detail", "操作失敗"))

                            # 3. 重置密碼操作 (Expander)
                            with btn_col3:
                                with st.popover("🔑 重置密碼"):
                                    st.write(f"重置 `{u_name}` 的密碼：")
                                    admin_new_pw = st.text_input("輸入新密碼", type="password", key=f"new_pw_input_{u_name}")
                                    if st.button("送出重置", key=f"submit_reset_{u_name}"):
                                        if not admin_new_pw or len(admin_new_pw) < 4:
                                            st.error("密碼長度至少 4 個字元")
                                        else:
                                            r = requests.post(f"{BACKEND_URL}/api/admin/users/reset-password", headers=get_auth_headers(), json={"username": u_name, "new_password": admin_new_pw})
                                            if r.status_code == 200:
                                                st.success(f"已重置 {u_name} 的密碼！")
                                            else:
                                                st.error(r.json().get("detail", "重置失敗"))

                            # 4. 刪除帳號操作
                            with btn_col4:
                                if st.button("🗑️ 刪除帳號", key=f"del_btn_{u_name}", use_container_width=True):
                                    r = requests.delete(f"{BACKEND_URL}/api/admin/users/{u_name}", headers=get_auth_headers())
                                    if r.status_code == 200:
                                        st.success(f"已刪除 {u_name}")
                                        st.rerun()
                                    else:
                                        st.error(r.json().get("detail", "刪除失敗"))
                        st.markdown("<hr style='margin: 8px 0; border-top: 1px dashed #CBD5E1;'>", unsafe_allow_html=True)
            else:
                st.error("無法取得使用者清單資料")
        except Exception as e:
            st.error(f"載入使用者清單發生錯誤: {str(e)}")
