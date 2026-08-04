import os
import hashlib
from typing import List, Union
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from src.providers import get_llm_and_embeddings

def load_documents(file_path: str) -> List[Document]:
    """載入單一 PDF 或 TXT 文件"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到檔案: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in [".txt", ".md"]:
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"不支援的檔案格式: {ext}")

    return loader.load()

def load_multiple_documents(file_paths: List[str]) -> List[Document]:
    """載入多份 PDF/TXT 文件"""
    all_docs = []
    for path in file_paths:
        docs = load_documents(path)
        all_docs.extend(docs)
    return all_docs

def split_documents(docs: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """將文件切割為較小的文字區塊 (Chunks)"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(docs)

def get_files_hash(file_paths: List[str]) -> str:
    """計算多個檔案的組合 MD5 雜湊值作為獨特標示"""
    hasher = hashlib.md5()
    for path in sorted(file_paths):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
    return hasher.hexdigest()[:8]

def build_vectorstore(documents: List[Document], embeddings, collection_name: str = "langgraph_rag") -> Chroma:
    """建立內存 / 持久化 Chroma 向量資料庫"""
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name
    )
    return vectorstore

def get_retriever(file_paths: Union[str, List[str]], provider: str = "google", k: int = 3):
    """
    一步到位：載入單一/多份文件 -> 切分 -> 向量化 -> 回傳 Retriever
    """
    if isinstance(file_paths, str):
        paths = [file_paths]
    else:
        paths = file_paths

    raw_docs = load_multiple_documents(paths)
    splits = split_documents(raw_docs)
    _, embeddings = get_llm_and_embeddings(provider)
    
    file_id = get_files_hash(paths)
    collection_name = f"langgraph_rag_{provider}_{file_id}"
    
    vectorstore = build_vectorstore(splits, embeddings, collection_name=collection_name)
    return vectorstore.as_retriever(search_kwargs={"k": k})
