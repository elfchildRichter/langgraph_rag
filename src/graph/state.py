from typing import List, TypedDict
from langchain_core.documents import Document

class GraphState(TypedDict):
    """
    表示 LangGraph 工作流的狀態結構

    Attributes:
        question: 使用者輸入的問題
        generation: LLM 生成的答案內容
        web_search_needed: 是否需要進行網路搜尋 ("Yes" / "No")
        documents: 檢索或搜尋到的參考文件列表 (List[Document])
        retry_count: 重試次數 (用於限制自我糾錯循環次數)
        route: 問題路由結果 ("vectorstore", "web_search", "direct")
        trace: 節點執行軌跡紀錄列表
    """
    question: str
    generation: str
    web_search_needed: str
    documents: List[Document]
    retry_count: int
    route: str
    trace: List[str]
