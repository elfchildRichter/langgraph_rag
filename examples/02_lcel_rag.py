import os
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

load_dotenv(override=True)
PDF_PATH = "data/Produktinformationsblatt.pdf"

def get_llm_and_embeddings(provider: str):
    provider = provider.lower().strip()

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        api_key = os.getenv("OLLAMA_API_KEY", "")
        llm_model = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

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

        embeddings = GoogleGenerativeAIEmbeddings(model=google_embed_model)
        llm = ChatGoogleGenerativeAI(model=google_model, temperature=0)

    return llm, embeddings

def build_rag_chain(provider: str = None):
    if not provider:
        provider = os.getenv("LLM_PROVIDER", "google")

    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    llm, embeddings = get_llm_and_embeddings(provider)
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    template = """你是一位專業的文件問答助手。請僅根據下方提供的參考資料內容來回答使用者的問題。
如果你無法從參考資料中找到答案，請直接誠實回答「根據提供的資料，我無法回答此問題」，不要憑空猜測。

[參考資料/Context]
{context}

[使用者問題/Question]
{question}
"""
    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

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

if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"錯誤：找不到 {PDF_PATH}！")
    else:
        chain, active_provider = build_rag_chain()
        print(f"\n=== 基礎 LCEL RAG 準備就緒 ({active_provider.upper()}) ===")
        user_query = "請問這份保險產品最低承保年齡是多少？"
        print(f"問題: {user_query}")
        response = chain.invoke(user_query)
        print(f"回應:\n{response}")
