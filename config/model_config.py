import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

model_client = OpenAIChatCompletionClient(
    model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "deepseek",
        "structured_output": True,
        "multiple_system_messages": True,
    },
)
