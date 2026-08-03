# LangChain RAG Document QA System

A **Retrieval-Augmented Generation (RAG)** document question-answering system built with **LangChain**. It seamlessly supports switching between **Google Gemini (Cloud API)** and **Ollama (Local / Self-hosted Server with API Key Authentication)**, leveraging an in-memory vector database (**ChromaDB**) for accurate PDF document retrieval and multi-language QA.

---

## 🌟 Key Features

* **Multi-Provider Support**: Switch easily between Google Gemini API and Ollama (Local or remote endpoints requiring API keys).
* **Centralized Environment Configuration (`.env`)**: Manage all LLM/Embedding model names, API keys, and endpoint URLs in one place.
* **Efficient Vector Pipeline**:
  * Document loading via `PyPDFLoader`.
  * Chunking with overlap using `RecursiveCharacterTextSplitter`.
  * Fast in-memory vector store using `ChromaDB`.
* **Strict RAG Prompting**: Forces LLMs to answer strictly based on retrieved context, effectively preventing hallucinations.
* **LCEL Architecture**: Clean, composable pipelines using LangChain Expression Language (`Prompt | Model | Parser`).

---

## 📁 Project Structure

```text
langchain_rag/
├── rag_demo.py                 # Main RAG script (PDF ingestion, vector search, CLI menu, and QA loop)
├── langchain_demo.py           # Basic LangChain LLM & Prompt Template demonstration
├── Produktinformationsblatt.pdf # Sample PDF document for testing
├── .env                        # Environment variables and model configurations
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 🛠️ Prerequisites & Installation

### 1. Install Dependencies

It is recommended to use a Python 3.10+ virtual environment:

```bash
pip install -r requirements.txt
```

**`requirements.txt` includes:**
* `langchain-core`
* `langchain-community`
* `langchain-google-genai`
* `langchain-ollama`
* `pypdf`
* `chromadb`
* `python-dotenv`

---

## ⚙️ Environment Configuration (`.env`)

Create or update the `.env` file in the root directory:

```env
# ------------------------------------------------------------------
# LLM Provider Selection: 'google' (default) or 'ollama' (local/remote)
# ------------------------------------------------------------------
LLM_PROVIDER="google"

# ------------------------------------------------------------------
# Google Gemini Settings
# ------------------------------------------------------------------
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
GOOGLE_MODEL="gemini-3.6-flash"
GOOGLE_EMBED_MODEL="models/gemini-embedding-001"

# ------------------------------------------------------------------
# Ollama Local / Remote Server Settings
# ------------------------------------------------------------------
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_API_KEY=""                # Optional: API Key if using remote/reverse-proxied Ollama server
OLLAMA_MODEL="qwen3:4b"          # Downloaded local LLM model (e.g., qwen3:4b, gemma3:4b, llama3.2)
OLLAMA_EMBED_MODEL="nomic-embed-text" # Local embedding model
```

> **💡 Ollama Usage Tip**:
> Before running with Ollama, ensure the Ollama daemon is running and required models are pulled:
> ```bash
> ollama pull qwen3:4b
> ollama pull nomic-embed-text
> ```

---

## 🚀 Getting Started

### 1. Run the RAG Document QA System (`rag_demo.py`)

Ensure a PDF file (e.g., `Produktinformationsblatt.pdf`) is placed in the project root, then execute:

```bash
python rag_demo.py
```

Upon launching, an interactive menu will prompt for provider selection:

```text
=== 請選擇模型提供者 ===
1. Google Gemini (預設)
2. Ollama (本地 / API Key 自建伺服器)
請選擇 (1/2，直接 Enter 使用預設)：
```

* Press **`1`** or **Enter**: Use Google Gemini (Cloud API).
* Press **`2`**: Use Ollama (Local / Remote Server, e.g., `qwen3:4b`).

Type your questions to interact with the PDF contents, and type `q` to exit.

---

### 2. Run Basic LangChain Demo (`langchain_demo.py`)

To test basic LLM invocation and prompt template chaining:

```bash
python langchain_demo.py
```

---

## 📝 License

This project is for educational and testing purposes.