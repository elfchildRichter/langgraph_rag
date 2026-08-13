import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings
from src import config

def get_llm_and_embeddings(provider: str = None, temperature: float = 0):
    """
    根據指定的 provider ('google' 或 'ollama') 初始化 LLM 與 Embeddings
    """
    if not provider:
        provider = config.DEFAULT_PROVIDER
    provider = provider.lower().strip()

    if provider == "ollama":
        base_url = config.OLLAMA_BASE_URL
        api_key = config.OLLAMA_API_KEY
        llm_model = config.OLLAMA_MODEL
        embed_model = config.OLLAMA_EMBED_MODEL

        client_kwargs = {"headers": {"Authorization": f"Bearer {api_key}"}} if api_key else None

        # Ollama Cloud (api.ollama.com) 不提供 Embeddings API 服務，自動採用 Google Embeddings 作為檢索備援
        if "api.ollama.com" in base_url:
            embeddings = GoogleGenerativeAIEmbeddings(model=config.GOOGLE_EMBED_MODEL)
        else:
            embeddings = OllamaEmbeddings(
                model=embed_model,
                base_url=base_url,
                client_kwargs=client_kwargs,
            )

        llm = ChatOllama(
            model=llm_model,
            base_url=base_url,
            temperature=temperature,
            client_kwargs=client_kwargs,
        )
    else:
        google_model = config.GOOGLE_MODEL
        google_embed_model = config.GOOGLE_EMBED_MODEL

        embeddings = GoogleGenerativeAIEmbeddings(model=google_embed_model)
        llm = ChatGoogleGenerativeAI(model=google_model, temperature=temperature)

    return llm, embeddings
