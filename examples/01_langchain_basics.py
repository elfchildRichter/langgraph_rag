import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. 載入 .env 檔案中的環境變數
load_dotenv(override=True)

# 驗證是否有成功讀取
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("找不到 GOOGLE_API_KEY，請檢查 .env 檔案設定！")
else:
    print("成功載入 API Key！")

# 2. 初始化 Gemini 模型
google_model = os.getenv("GOOGLE_MODEL", "gemini-3.6-flash")
model = ChatGoogleGenerativeAI(
    model=google_model,
    temperature=0.7,
)

# 3. 建立 Prompt Template
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一位專業且幽默的 Python 程式導師，請用繁體中文回答。"),
    ("user", "{question}"),
])

# 4. 初始化 Output Parser
parser = StrOutputParser()

# 5. 用 LCEL 串起來 (Prompt | Model | Parser)
chain = prompt | model | parser

# 6. 執行測試
if __name__ == "__main__":
    answer = chain.invoke({"question": "請簡單介紹什麼是 LangChain"})
    print("Gemini 的回答：\n", answer)
