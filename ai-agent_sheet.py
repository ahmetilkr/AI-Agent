import asyncio
from google.genai import types
# Agent Development Kit (ADK)
from google.adk.agents import Agent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool, FunctionTool, google_search

# Data / Tool
import pandas as pd

# Google Sheets API
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Secrets / Environment
import os
from dotenv import load_dotenv



# .env dosyasını oku
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    print("✅ Google API Key başarıyla yüklendi.")
else:
    print("❌ Google API Key bulunamadı. Lütfen .env dosyasını kontrol edin.")

# Bu ayar Gemini’yi doğru modda kullanmak için
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")


SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEETS_RANGE = os.getenv("SHEETS_RANGE")

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def load_sales_data_from_sheets() -> dict:
    """
    Google Sheets API üzerinden satış verisini okur
    ve LLM'in analiz etmesi için CSV formatında döner.
    Dönüş:
        {"csv_data": "..."} formatında string
    """
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )

    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEETS_RANGE
    ).execute()

    values = result.get("values", [])

    if not values:
        raise ValueError("Sheet aralığında veri bulunamadı.")

    header = values[0]
    rows = values[1:]

    df = pd.DataFrame(rows, columns=header)

    # Satış kolonu gibi sayısal kolonları numeriğe çevir
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass

    csv_text = df.to_csv(index=False)
    return {"csv_data": csv_text}


sales_report_agent = Agent(
    name="SalesReportAgent",
    model="gemini-3.5-flash-lite",
    instruction="""
    Sen bir veri analisti AI agentsın.
    Tool'dan gelen satış verisini analiz ederek aşağıdaki çıktıları üret:

    - Ortalama günlük satış
    - En yüksek satış günü
    - En düşük satış günü
    - Genel trend (artış/azalış)
    - Önemli notlar

    Cevabı Türkçe ve madde madde yaz.
    """,
    tools=[load_sales_data_from_sheets],
    output_key="sales_report",
)

print("🤖 Ajan başarıyla oluşturuldu.")


root_agent = SequentialAgent(
    name="BlogPipeline",
    sub_agents=[sales_report_agent],
)

print("✅ Sequential Agent created.")


runner = InMemoryRunner(agent=root_agent,app_name="agents")
response = asyncio.run(
    runner.run_debug("Haftalık satış verisini analiz et.", quiet=True)
)
print(response)



