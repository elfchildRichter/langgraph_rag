from typing import Dict, Any, List
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_community.tools import DuckDuckGoSearchRun

from src.graph.state import GraphState
from src.providers import get_llm_and_embeddings

def format_docs(docs: List[Document]) -> str:
    """將多個 Document 物件格式化為乾淨的文字區塊」"""
    if not docs:
        return "無參考資料。"
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "未知來源")
        formatted.append(f"[文件 {i} - 來源: {source}]\n{doc.page_content}")
    return "\n\n".join(formatted)


class GraphNodes:
    def __init__(self, retriever, provider: str = "google", enable_web_search: bool = True):
        self.retriever = retriever
        self.provider = provider
        self.enable_web_search = enable_web_search
        self.llm, _ = get_llm_and_embeddings(provider=provider, temperature=0)
        self.search_tool = DuckDuckGoSearchRun() if enable_web_search else None

    def question_router_node(self, state: GraphState) -> Dict[str, Any]:
        """
        問題路由節點：分析使用者問題類型，決定走向向量庫、網路搜尋或直接回答
        """
        question = state["question"]
        trace = list(state.get("trace", []))
        trace.append("[節點: Question Router] 分析問題領域...")

        if not self.enable_web_search:
            system_prompt = """你是一位高智商的問題路由專家。
根據使用者的問題內容，將問題分類至以下兩種路徑之一：
1. "vectorstore": 問題與上傳的文件資料、產品規格、數據、說明書或具體檔案內容相關。
2. "direct": 一般問候、聊天、極簡單常識或不需資料檢索即可回答的問題。

請僅回傳 JSON 格式，包含 "datasource" 欄位，例如：{"datasource": "vectorstore"}
"""
        else:
            system_prompt = """你是一位高智商的問題路由專家。
根據使用者的問題內容，將問題分類至以下三種路徑之一：
1. "vectorstore": 問題與上傳的文件資料、產品規格、數據、說明書或具體檔案內容相關。
2. "web_search": 問題涉及最新即時新聞、近期時事、未知實體或外部網際網路資訊。
3. "direct": 一般問候、聊天、極簡單常識或不需資料檢索即可回答的問題。

請僅回傳 JSON 格式，包含 "datasource" 欄位，例如：{"datasource": "vectorstore"}
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke({"question": question})
            route = result.get("datasource", "vectorstore")
        except Exception:
            route = "vectorstore"

        if not self.enable_web_search and route == "web_search":
            route = "vectorstore"

        trace.append(f"  └─ 路由決策: {route.upper()}")
        return {"route": route, "trace": trace}

    def retrieve_node(self, state: GraphState) -> Dict[str, Any]:
        """
        向量庫檢索節點：根據問題自 ChromaDB 檢索最相關文件區塊
        """
        question = state["question"]
        trace = list(state.get("trace", []))
        trace.append(f"[節點: Retrieve] 正在向量資料庫檢索問題: '{question}'...")

        documents = self.retriever.invoke(question)
        trace.append(f"  └─ 成功檢索到 {len(documents)} 個文件區塊")

        return {"documents": documents, "trace": trace}

    def grade_documents_node(self, state: GraphState) -> Dict[str, Any]:
        """
        文件相關性評估節點：一次性打包評估檢索出的所有文件相關性 (Batch CRAG)
        """
        question = state["question"]
        documents = state["documents"]
        trace = list(state.get("trace", []))
        trace.append(f"[節點: Grade Documents] 評估 {len(documents)} 份文件的相關性...")

        if not documents:
            if self.enable_web_search:
                trace.append("  └─ 評估結果: 無檢索文件，觸發 Web Search 備援機制")
                return {"documents": [], "web_search_needed": "Yes", "trace": trace}
            else:
                trace.append("  └─ 評估結果: 無檢索文件 (即時網路搜尋已停用，直接進行生成)")
                return {"documents": [], "web_search_needed": "No", "trace": trace}

        # 將所有檢索區塊打包單次送交 LLM
        formatted_context = format_docs(documents)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位嚴謹的文件相關性審查專家。
請評估提供的參考文件內容是否包含有助於回答使用者問題的關鍵資訊。
如果參考資料包含與問題相關的內容，請回傳 {{"relevant": "yes"}}；否則回傳 {{"relevant": "no"}}。
請僅回傳 JSON 格式。"""),
            ("human", "參考文件:\n{context}\n\n使用者問題: {question}")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        try:
            res = chain.invoke({"context": formatted_context, "question": question})
            is_relevant = res.get("relevant", "yes").lower() == "yes"
        except Exception:
            is_relevant = True

        if not is_relevant:
            if self.enable_web_search:
                web_search_needed = "Yes"
                trace.append("  └─ 評估結果: 檢索文件與問題無關，觸發 Web Search 備援機制")
            else:
                web_search_needed = "No"
                trace.append("  └─ 評估結果: 檢索文件與問題無關 (即時網路搜尋已停用，直接進行生成)")
        else:
            web_search_needed = "No"
            trace.append(f"  └─ 評估結果: 確認包含 {len(documents)} 份有效參考文件")

        return {
            "documents": documents,
            "web_search_needed": web_search_needed,
            "trace": trace
        }

    def web_search_node(self, state: GraphState) -> Dict[str, Any]:
        """
        網路搜尋節點：使用 DuckDuckGo 進行最新外部資訊檢索補強
        """
        question = state["question"]
        documents = list(state.get("documents", []))
        trace = list(state.get("trace", []))
        trace.append(f"[節點: Web Search] 執行 DuckDuckGo 即時網路搜尋: '{question}'...")

        if not self.enable_web_search or not self.search_tool:
            trace.append("  └─ 即時網路搜尋已停用，跳過搜尋")
            return {"documents": documents, "web_search_needed": "No", "trace": trace}

        try:
            search_results = self.search_tool.run(question)
            web_doc = Document(
                page_content=search_results,
                metadata={"source": "DuckDuckGo Web Search"}
            )
            documents.append(web_doc)
            trace.append("  └─ 網路搜尋成功取得最新參考資訊")
        except Exception as e:
            trace.append(f"  └─ 網路搜尋執行遭遇錯誤: {str(e)}")

        return {"documents": documents, "web_search_needed": "No", "trace": trace}

    def generate_node(self, state: GraphState) -> Dict[str, Any]:
        """
        RAG 回答生成節點：結合參考資料與問題，生成專業解答
        """
        question = state["question"]
        documents = state.get("documents", [])
        trace = list(state.get("trace", []))
        trace.append("[節點: Generate] 使用 LLM 根據參考資料生成回答...")

        context_str = format_docs(documents)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位專業且誠實的問答助手。
請僅根據下方提供的參考資料內容來回答使用者的問題。
回答時請保持語氣專業、簡潔且明確。
如果參考資料不足以回答問題，請誠實說明，切勿憑空捏造。

[參考資料/Context]
{context}"""),
            ("human", "{question}")
        ])

        chain = prompt | self.llm | StrOutputParser()
        generation = chain.invoke({"context": context_str, "question": question})

        trace.append("  └─ 成功生成解答內容")
        return {"generation": generation, "trace": trace}

    def direct_answer_node(self, state: GraphState) -> Dict[str, Any]:
        """
        直接回答節點：處理常識性或問候問題，無需檢索 Context
        """
        question = state["question"]
        trace = list(state.get("trace", []))
        trace.append("[節點: Direct Answer] 直接由 LLM 進行對話回答...")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一位親切專業的 AI 助手。請直接回答使用者的問題。"),
            ("human", "{question}")
        ])

        chain = prompt | self.llm | StrOutputParser()
        generation = chain.invoke({"question": question})

        trace.append("  └─ 直接回答完成")
        return {"generation": generation, "trace": trace}
