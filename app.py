import os
import tempfile
import streamlit as st

from src import config
from src.vectorstore import get_retriever, load_documents, split_documents, build_vectorstore
from src.providers import get_llm_and_embeddings
from src.graph import build_rag_graph, run_rag_workflow

# 1. 頁面基本設定
st.set_page_config(
    page_title="LangGraph Adaptive RAG 智能問答系統",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 自訂 CSS 美化
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #64748B;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .stChatMessage {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Sidebar 設定
with st.sidebar:
    st.title("系統控制面板")
    
    provider_choice = st.radio(
        "選擇 LLM 模型提供者",
        options=["Google Gemini", "Ollama"],
        index=0 if config.DEFAULT_PROVIDER == "google" else 1,
        help="支援 Google API 或本地 Ollama 服務"
    )
    provider_key = "google" if provider_choice == "Google Gemini" else "ollama"

    st.markdown("---")
    st.subheader("文件上傳與索引")
    
    uploaded_files = st.file_uploader("上傳自訂 PDF / TXT 檔案 (支援多選)", type=["pdf", "txt", "md"], accept_multiple_files=True)
    
    retrieval_k = st.slider("向量檢索數量 (Top-K)", min_value=1, max_value=10, value=3)
    enable_web_search = st.checkbox("啟用即時網路搜尋 (Web Search)", value=True, help="當本地文件未提及或相關度不足時，是否使用 DuckDuckGo 進行網路搜尋補強")
    show_trace = st.checkbox("顯示 LangGraph 節點執行軌跡 (Trace Log)", value=True)

    st.markdown("---")
    st.markdown("### 關於 LangGraph RAG")
    st.info("""
    **自適應與自我糾錯 RAG 流程 (CRAG)**：
    1. **Question Router**: 自動判斷問題分類
    2. **Retriever**: Chroma 向量檢索
    3. **Grade Documents**: 評估文件相關度
    4. **Web Search**: 無相關文件時自動備援搜尋 (可開關)
    5. **Generate**: 生成最終準確解答
    """)

# 4. 初始化 Session State 與向量庫/圖
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource(show_spinner=False)
def initialize_rag_system(file_paths: tuple, provider: str, k: int, enable_web_search: bool = True):
    retriever = get_retriever(list(file_paths), provider=provider, k=k)
    app = build_rag_graph(retriever=retriever, provider=provider, enable_web_search=enable_web_search)
    return app

# 處理文件路徑
active_file_paths = [config.DEFAULT_PDF_PATH]
if uploaded_files:
    temp_dir = tempfile.mkdtemp()
    active_file_paths = []
    for u_file in uploaded_files:
        p = os.path.join(temp_dir, u_file.name)
        with open(p, "wb") as f:
            f.write(u_file.getbuffer())
        active_file_paths.append(p)

display_filenames = ", ".join([os.path.basename(p) for p in active_file_paths])
active_model_name = config.GOOGLE_MODEL if provider_key == "google" else config.OLLAMA_MODEL
web_status_text = "網路搜尋：開啟" if enable_web_search else "網路搜尋：關閉"

# 5. 主畫面標頭
st.markdown('<div class="main-header">LangGraph Adaptive & Corrective RAG</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">當前載入文件 ({len(active_file_paths)} 份)：<code>{display_filenames}</code> | 模型：<b>{provider_choice} | {active_model_name}</b> | <b>{web_status_text}</b></div>', unsafe_allow_html=True)

# 載入 LangGraph App
try:
    with st.spinner("正在建立向量資料庫與 LangGraph 工作流圖..."):
        app = initialize_rag_system(tuple(active_file_paths), provider_key, retrieval_k, enable_web_search)
    st.success("RAG 系統準備就緒")
except Exception as e:
    st.error(f"系統初始化失敗: {str(e)}")
    st.stop()

# 6. 渲染聊天歷史紀錄
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "trace" in message and show_trace and message["trace"]:
            with st.expander("檢視 LangGraph 執行軌跡 (Trace)"):
                for t in message["trace"]:
                    st.text(t)
        if "docs" in message and message["docs"]:
            with st.expander("檢視參考資料來源"):
                for idx, doc in enumerate(message["docs"], 1):
                    src = doc.metadata.get("source", "未知來源")
                    st.markdown(f"**[{idx}] 來源: `{src}`**")
                    st.caption(doc.page_content[:300] + "...")

# 7. 使用者輸入區塊
if prompt := st.chat_input("請輸入您關於 PDF 或檔案的問題..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        status_box = st.status("LangGraph 工作流執行中...", expanded=True)
        
        try:
            status_box.write("▶ 開始分析問題並執行工作流...")
            result = run_rag_workflow(app, prompt)
            
            trace_logs = result.get("trace", [])
            for log_line in trace_logs:
                status_box.write(log_line)
            status_box.update(label="LangGraph 工作流執行完成", state="complete", expanded=False)

            answer = result.get("generation", "無生成結果")
            docs = result.get("documents", [])

            message_placeholder.markdown(answer)

            if docs:
                with st.expander("檢視參考資料來源"):
                    for idx, doc in enumerate(docs, 1):
                        src = doc.metadata.get("source", "未知來源")
                        st.markdown(f"**[{idx}] 來源: `{src}`**")
                        st.caption(doc.page_content[:300] + "...")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "trace": trace_logs,
                "docs": docs
            })

        except Exception as e:
            status_box.update(label="執行失敗", state="error", expanded=True)
            st.error(f"發生錯誤: {str(e)}")
