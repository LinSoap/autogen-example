from autogen_agentchat.agents import (
    AssistantAgent,
)
from autogen_agentchat.conditions import (
    TextMentionTermination,
    MaxMessageTermination,
    FunctionCallTermination,
)
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult
from config.model_config import model_client
import duckdb
import asyncio
import os
import pandas as pd


# Singleton-like DuckDB connection manager
class DuckDBManager:
    _connection = None

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            cls._connection = duckdb.connect()
        return cls._connection

    @classmethod
    def register_dataframe(cls, df: pd.DataFrame, table_name: str):
        """Register a DataFrame as a table in DuckDB with the given table name."""
        con = cls.get_connection()
        con.register(table_name, df)
        return table_name

    @classmethod
    def query(cls, query: str) -> pd.DataFrame:
        """Execute a query and return results as a DataFrame."""
        con = cls.get_connection()
        return con.execute(query).df()

    @classmethod
    def list_tables(cls) -> list:
        """List all available tables in the DuckDB connection."""
        con = cls.get_connection()
        result = con.execute("SHOW TABLES").fetchall()
        return [row[0] for row in result]

    @classmethod
    def close(cls):
        """Close the DuckDB connection."""
        if cls._connection is not None:
            cls._connection.close()
            cls._connection = None


# DuckDB query tool for autogen
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
        reflect_on_tool_use=True,
        system_message=f"""
        以下是用户的问题:
        <question>
            {question}
        </question>
        你只有在完成用户目标后，得出具体的分析结论,这个结论要包含用户的问题以及具体的数据分析结果，使用task_done工具。
        你是一个数据分析专家，擅长使用DuckDB进行数据分析。
        你会接收到一个DuckDB表的结构描述（包括DESCRIBE结果和部分数据样例）。
        你需要根据这些信息，回答用户关于数据分析的问题。
        请根据表结构和数据样例，生成相应的DuckDB SQL查询语句来回答用户的问题。
        在生成SQL查询语句时，请确保语句能够正确执行并返回所需的结果。
        你只需回复SQL查询语句，不要包含其他多余信息。
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


# def get_ciritical_agent(question, data_info: str) -> AssistantAgent:
#     agent = AssistantAgent(
#         name="critical_agent",
#         model_client=model_client,
#         tools=[task_done],
#         model_client_stream=True,
#         system_message=f"""
#         这是用户的问题:
#         <question>
#             {question}
#         </question>
#         你是一个数据分析结果解读专家，擅长从数据分析结果中提取关键信息并进行解释。
#         如果数据分析没有返回结果，请说明没有结果的可能原因。并给出改进建议。
#         如果有结果，请提取结果中的关键信息，进行简要解释，并给出下一步的建议。直到完成用户目标任务。
#         只有在完全完成用户目标后，使用task_done工具。
#         <duck_db_info>
#             {data_info}
#         </duck_db_info>
#         以下是Duck表的原始信息，请结合使用：
#         以下是可用的DuckDB表列表：
#         <table_list>
#             {', '.join(DuckDBManager.list_tables())}
#         </table_list>
#         """,
#     )
#     return agent


def get_generate_data_info_agent() -> AssistantAgent:
    agent = AssistantAgent(
        name="data_info_agent",
        model_client=model_client,
        model_client_stream=True,
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


async def assistant_run() -> None:
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, "1-2.xlsx")

    df = pd.read_excel(excel_path)

    print(df.describe())
    print(df.value_counts())

    # 3. 将 DataFrame 注册为一个临时表（例如，'my_table'）
    DuckDBManager.register_dataframe(df, "duckdb_table")

    # 4. 现在可以使用 DuckDB 查询该表
    con = DuckDBManager.get_connection()

    head_result = con.execute(
        """
        SELECT * FROM duckdb_table limit 20
    """
    ).df()

    # desc_result = con.execute(
    #     """
    #     DESCRIBE duckdb_table
    # """
    # ).df()

    # info_agent = get_generate_data_info_agent()

    # async for message in info_agent.run_stream(
    #     task=TextMessage(
    #         content=f"""
    #         请使用中文分析以下DataFrame的信息：
    #         <desc_info>{desc_result}</desc_info>
    #         <data_head>{head_result}</data_head>
    #         """,
    #         source="user",
    #     )
    # ):
    #     if isinstance(message, TaskResult):
    #         autogen_result = message.model_dump()
    #         new_data_info = autogen_result["messages"][-1]["content"]
    # print(new_data_info)

    # question = "计算所有人事部门员工的平均薪资。"

    # response_agent = get_assistant_agent(question, new_data_info)
    # # critical_agent = get_ciritical_agent(question, new_data_info)

    # termination_condition = MaxMessageTermination(15) | FunctionCallTermination(
    #     "task_done"
    # )
    # team = RoundRobinGroupChat(
    #     [response_agent],
    #     termination_condition=termination_condition,
    # )

    # await Console(
    #     team.run_stream(
    #         task=[
    #             TextMessage(
    #                 content=question,
    #                 source="user",
    #             )
    #         ]
    #     ),
    #     output_stats=True,
    # )


asyncio.run(assistant_run())
