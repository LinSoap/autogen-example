from autogen_agentchat.agents import (
    AssistantAgent,
)
from config.model_config import model_client
from src.db_manager import DuckDBManager


def query_data_with_duckdb(query: str) -> str:
    """
    Execute a DuckDB query on the registered DataFrame.
    Returns DataFrame results or error message as a string.
    """
    try:
        result = DuckDBManager.query(query)
        return result.to_string()
    except Exception as e:
        return f"Query failed: {str(e)}"


def task_done(result: str) -> str:
    """
    标记任务已完成的工具函数。
    用于在对话中明确表示任务已结束，并返回最终结果摘要。
    """
    return result


def get_assistant_agent(question: str, data_info: str) -> AssistantAgent:
    agent = AssistantAgent(
        name="excel_analysis_agent",
        model_client=model_client,
        # model_client_stream=True,
        tools=[query_data_with_duckdb, task_done],
        # reflect_on_tool_use=True,
        system_message=f"""
        以下是用户的问题:
        <question>
            {question}
        </question>
        你只有在完成用户目标后，得出具体的分析结论,这个结论要包含用户的问题以及具体的数据分析结果，使用task_done工具。
        如果查询结果为0或为空，你需要进一步的了解数据表结果和内容，判断是否需要进一步的查询。
        你是一个数据分析专家，擅长使用DuckDB进行数据分析。
        你会接收到一个DuckDB表的结构描述（包括DESCRIBE结果和部分数据样例）。
        你需要根据这些信息，回答用户关于数据分析的问题。
        请根据表结构和数据样例，生成相应的DuckDB SQL查询语句来回答用户的问题。
        在生成SQL查询语句时，请确保语句能够正确执行并返回所需的结果。
        这里是DuckDB表的信息,其中的字段描述是处理过的，不是原始的：
        <duck_db_info>
            {data_info}
        </duck_db_info>
        以下是Duck表的原始信息，请结合使用：
        以下是可用的DuckDB表列表：
        <table_list>
            {', '.join(DuckDBManager.list_tables())}
        </table_list>
""",
    )
    return agent


def get_generate_data_info_agent() -> AssistantAgent:
    agent = AssistantAgent(
        name="data_info_agent",
        model_client=model_client,
        system_message="""
        你是一个 DuckDB 表结构分析专家，擅长从表结构和样例数据中推断字段含义。
        你会收到一个 DuckDB 表的 DESCRIBE 结果（包含字段名、数据类型、是否可为空等）以及前几行数据（head）。
        你的任务是：
            1. 分析 DESCRIBE 和 head 数据，补全表结构信息，特别是为 `Unnamed` 列推断有意义的列名（基于数据内容，如数值列命名为 metric_X，文本列命名为 category_X）。
            2. 保持原始字段名和数据类型不变，仅为 `Unnamed` 列提供含义描述。
            3. 使用 Markdown 表格输出补全后的表结构，包含以下列：
            - 字段名（Field）
            - 数据类型（Type）
            - 是否可为空（Nullable）
            - 描述（Description，推断的字段含义）
            4. 在表格下方提供表的简要描述，说明数据内容和用途。
            5. 仅返回 Markdown 表格和描述，无其他信息。
""",
    )
    return agent


def get_judge_agent() -> AssistantAgent:
    agent = AssistantAgent(
        name="judge_agent",
        model_client=model_client,
        system_message="""
        我会给你一个结果和标准答案，请你帮我判断结果是否正确。
        如果是结果存在小数点，则保留两位小数判断数值准确性。
        如果结果正确，回复“结果正确”。
        如果结果不正确，回复“结果不正确”，并简要说明原因。
""",
    )
    return agent
