from src.graph.state import GraphState

def route_question(state: GraphState) -> str:
    """
    條件邊：根據 Question Router 的決策將流程分支轉移
    """
    route = state.get("route", "vectorstore")
    if route == "vectorstore":
        return "retrieve"
    elif route == "web_search":
        return "web_search"
    else:
        return "direct_answer"

def decide_to_generate(state: GraphState) -> str:
    """
    條件邊：評估文件相關性後，決定直接生成答案還是發起網路搜尋補強
    """
    web_search_needed = state.get("web_search_needed", "No")
    if web_search_needed == "Yes":
        return "web_search"
    else:
        return "generate"
