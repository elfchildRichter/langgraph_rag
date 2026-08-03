import os
from dotenv import load_dotenv

# LangChain 核心與模組導入
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

# 1. 載入 .env 中的設定
load_dotenv(override=True)

PDF_PATH = "data/Produktinformationsblatt.pdf"


def get_llm_and_embeddings(provider: str):
    """
    根據指定的 provider 初始化 LLM 與 Embeddings
    支援: 'google' (Gemini) 或 'ollama' (本地 / API Key 自建伺服器)
    """
    provider = provider.lower().strip()

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        api_key = os.getenv("OLLAMA_API_KEY", "")
        llm_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

        print(f"▶ 使用 Ollama 提供者 (URL: {base_url}, LLM: {llm_model}, Embeddings: {embed_model})")
        if api_key:
            print("▶ 已啟用 Ollama API Key")

        client_kwargs = {"headers": {"Authorization": f"Bearer {api_key}"}} if api_key else None

        embeddings = OllamaEmbeddings(
            model=embed_model,
            base_url=base_url,
            client_kwargs=client_kwargs,
        )
        llm = ChatOllama(
            model=llm_model,
            base_url=base_url,
            temperature=0,
            client_kwargs=client_kwargs,
        )
    else:
        google_model = os.getenv("GOOGLE_MODEL", "gemini-3.6-flash")
        google_embed_model = os.getenv("GOOGLE_EMBED_MODEL", "models/gemini-embedding-001")

        print(f"▶ 使用 Google Gemini 提供者 (LLM: {google_model}, Embeddings: {google_embed_model})")
        embeddings = GoogleGenerativeAIEmbeddings(model=google_embed_model)
        llm = ChatGoogleGenerativeAI(model=google_model, temperature=0)

    return llm, embeddings


def build_rag_chain(provider: str = None):
    if not provider:
        provider = os.getenv("LLM_PROVIDER", "google")

    # ------------------------------------------------------------------
    # 階段一：讀取與預處理文件 (Document Ingestion & Splitting)
    # ------------------------------------------------------------------
    print("正在讀取 PDF 文件...")
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()

    print("正在切分文字塊 (Text Splitting)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)
    print(f"切分完成，共有 {len(splits)} 個文本塊。")

    # ------------------------------------------------------------------
    # 階段二：向量化與建立向量資料庫 (Embeddings & VectorStore)
    # ------------------------------------------------------------------
    llm, embeddings = get_llm_and_embeddings(provider)

    print("正在建立 Embeddings 並寫入本機向量資料庫 (ChromaDB)...")
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)

    # 將 VectorStore 轉為檢索器 (Retriever)，預設檢索最相關的前 3 個區塊 (k=3)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # ------------------------------------------------------------------
    # 階段三：建構 RAG 提示詞與 LCEL Chain
    # ------------------------------------------------------------------
    print("正在建構 RAG LCEL Chain...")

    template = """你是一位專業的文件問答助手。請僅根據下方提供的參考資料內容來回答使用者的問題。
如果你無法從參考資料中找到答案，請直接誠實回答「根據提供的資料，我無法回答此問題」，不要憑空猜測。

[參考資料/Context]
{context}

[使用者問題/Question]
{question}
"""
    prompt = ChatPromptTemplate.from_template(template)

    # 輔助函式：將檢索出來的多個 Document 物件拼接成一個大字串
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # 使用 LCEL 串聯 RAG 流程
    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain, provider


# ------------------------------------------------------------------
# 4. 執行問答
# ------------------------------------------------------------------
if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"錯誤：找不到 {PDF_PATH}，請先放入一份 PDF 檔案！")
    else:
        print("\n=== 請選擇模型提供者 ===")
        print("1. Google Gemini (預設)")
        print("2. Ollama (本地 / API Key 自建伺服器)")
        user_choice = input("請選擇 (1/2，直接 Enter 使用預設)：").strip()

        if user_choice == "2":
            chosen_provider = "ollama"
        elif user_choice == "1":
            chosen_provider = "google"
        else:
            chosen_provider = os.getenv("LLM_PROVIDER", "google")

        # 建立 RAG Chain
        chain, active_provider = build_rag_chain(provider=chosen_provider)

        print(f"\n=== RAG 系統準備就緒 ({active_provider.upper()})，輸入 'q' 離開 ===\n")
        while True:
            user_query = input("請輸入你關於 PDF 的問題：")
            if user_query.lower() == 'q':
                break

            print("\n[思考與檢索中...]")
            response = chain.invoke(user_query)
            print(f"[{active_provider.capitalize()} 回應]：\n{response}\n" + "-"*40)