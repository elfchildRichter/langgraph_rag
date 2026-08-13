import os
import sys
from src import config, get_retriever, build_rag_graph, run_rag_workflow

def main():
    print("=" * 60)
    print("LangGraph Adaptive & Corrective RAG (CRAG) 互動終端系統")
    print("=" * 60)

    pdf_path = config.DEFAULT_PDF_PATH
    if not os.path.exists(pdf_path):
        print(f"錯誤：找不到預設檔案 {pdf_path}，請確認檔案放置於 data/ 目錄下。")
        sys.exit(1)

    print("\n=== 請選擇 LLM 模型提供者 ===")
    print("1. Ollama (遠端 / 本地預設)")
    print("2. Google Gemini")
    choice = input("請選擇 (1/2，按下 Enter 使用預設 1): ").strip()

    if choice == "2":
        chosen_provider = "google"
    else:
        chosen_provider = "ollama"

    web_choice = input("\n是否啟用「即時網路搜尋 (Web Search)」備援？(y/n，按下 Enter 預設啟用 y): ").strip().lower()
    enable_web_search = False if web_choice == "n" else True
    web_status = "開啟" if enable_web_search else "關閉"

    print(f"\n▶ 正在載入文件 {pdf_path} 並建構 ChromaDB 向量庫...")
    try:
        retriever = get_retriever(pdf_path, provider=chosen_provider, k=3)
        print("▶ 向量庫就緒！正在建構 LangGraph 工作流圖...")
        app = build_rag_graph(retriever=retriever, provider=chosen_provider, enable_web_search=enable_web_search)
        chosen_model = config.OLLAMA_MODEL if chosen_provider == "ollama" else config.GOOGLE_MODEL
        print(f"LangGraph RAG 系統初始化完成！(模型: {chosen_provider.capitalize()} | {chosen_model} | 網路搜尋: {web_status})\n")
    except Exception as e:
        print(f"初始化失敗: {str(e)}")
        sys.exit(1)

    print("提示：輸入 'q' 離開程式，輸入問題開始問答。\n" + "-" * 60)

    while True:
        try:
            query = input("\n請輸入您的問題：").strip()
            if not query:
                continue
            if query.lower() == 'q':
                print("感謝使用 LangGraph RAG 系統，再見！")
                break

            print("\n[LangGraph 狀態圖開始執行...]")
            result = run_rag_workflow(app, query)

            print("\n--- LangGraph 執行節點軌跡 (Node Traces) ---")
            for trace_log in result.get("trace", []):
                print(trace_log)

            print("\n--- 系統最終解答 (Final Answer) ---")
            print(result.get("generation", "無生成結果"))

            docs = result.get("documents", [])
            if docs:
                print(f"\n--- 參考資料來源 (共 {len(docs)} 個區塊) ---")
                for i, doc in enumerate(docs, 1):
                    src = doc.metadata.get("source", "未知來源")
                    snippet = doc.page_content[:150].replace('\n', ' ')
                    print(f"  [{i}] 來源: {src} | 預覽: {snippet}...")

            print("-" * 60)

        except KeyboardInterrupt:
            print("\n程式已終止。")
            break
        except Exception as e:
            print(f"\n執行過程遭遇錯誤: {str(e)}")

if __name__ == "__main__":
    main()
