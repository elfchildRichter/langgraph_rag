from langgraph.graph import StateGraph, END, START
from src.graph.state import GraphState
from src.graph.nodes import GraphNodes
from src.graph.edges import route_question, decide_to_generate

def build_rag_graph(retriever, provider: str = "google", enable_web_search: bool = True):
    """
    建構與編譯 LangGraph Adaptive & Corrective RAG (CRAG) 工作流圖
    """
    nodes = GraphNodes(retriever=retriever, provider=provider, enable_web_search=enable_web_search)

    # 1. 初始化 StateGraph
    workflow = StateGraph(GraphState)

    # 2. 加入節點 (Nodes)
    workflow.add_node("question_router", nodes.question_router_node)
    workflow.add_node("retrieve", nodes.retrieve_node)
    workflow.add_node("grade_documents", nodes.grade_documents_node)
    workflow.add_node("web_search", nodes.web_search_node)
    workflow.add_node("generate", nodes.generate_node)
    workflow.add_node("direct_answer", nodes.direct_answer_node)

    # 3. 設定進入點與邊 (Edges & Conditional Edges)
    workflow.add_edge(START, "question_router")

    # Question Router 條件分支 -> retrieve / web_search / direct_answer
    workflow.add_conditional_edges(
        "question_router",
        route_question,
        {
            "retrieve": "retrieve",
            "web_search": "web_search",
            "direct_answer": "direct_answer"
        }
    )

    # Retrieve -> Grade Documents
    workflow.add_edge("retrieve", "grade_documents")

    # Grade Documents 條件分支 -> generate / web_search
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "web_search": "web_search",
            "generate": "generate"
        }
    )

    # Web Search -> Generate
    workflow.add_edge("web_search", "generate")

    # Generate -> END
    workflow.add_edge("generate", END)

    # Direct Answer -> END
    workflow.add_edge("direct_answer", END)

    # 4. 編譯 Workflow
    app = workflow.compile()
    return app

def run_rag_workflow(app, question: str) -> dict:
    """
    執行 LangGraph RAG 工作流並回傳最終狀態與軌跡
    """
    initial_state: GraphState = {
        "question": question,
        "generation": "",
        "web_search_needed": "No",
        "documents": [],
        "retry_count": 0,
        "route": "",
        "trace": []
    }

    final_state = app.invoke(initial_state)
    return final_state
