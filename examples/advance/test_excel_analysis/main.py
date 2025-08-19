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
import json


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


async def main() -> None:
    # 读取测试集

    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "test_excel.json")
    with open(json_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    # 获取当前脚本的目录
    excel_path = os.path.join(current_dir, test_cases[0].get("file_name"))

    df = pd.read_excel(excel_path)
    DuckDBManager.register_dataframe(df, "duckdb_table")
    con = DuckDBManager.get_connection()
    head_result = con.execute("SELECT * FROM duckdb_table limit 20").df()
    desc_result = con.execute("DESCRIBE duckdb_table").df()

    info_agent = get_generate_data_info_agent()
    # 获取表结构描述
    new_data_info = None
    async for message in info_agent.run_stream(
        task=TextMessage(
            content=f"""
            请使用中文分析以下DataFrame的信息：
            <desc_info>{desc_result}</desc_info>
            <data_head>{head_result}</data_head>
            """,
            source="user",
        )
    ):
        if isinstance(message, TaskResult):
            autogen_result = message.model_dump()
            new_data_info = autogen_result["messages"][-1]["content"]
    print("表结构描述:\n", new_data_info)

    judge_agent = get_judge_agent()
    termination_condition = MaxMessageTermination(15) | FunctionCallTermination(
        "task_done"
    )

    # 结果收集
    results = []

    for case in test_cases:
        question = case["question"]
        answer = case["answer"]
        analysis_result = ""
        judge_result = ""

        response_agent = get_assistant_agent(question, new_data_info)
        # critical_agent = get_ciritical_agent(question, new_data_info)
        team = RoundRobinGroupChat(
            [response_agent],
            termination_condition=termination_condition,
        )

        # 1. 让team分析问题
        async for message in team.run_stream(
            task=TextMessage(
                content=question,
                source="user",
            )
        ):
            if isinstance(message, TextMessage):
                print(f"Q: {question}\nA: {message.content}")
            if isinstance(message, TaskResult):
                autogen_result = message.model_dump()
                analysis_result = autogen_result["messages"][-1]["content"]

        print("-" * 50)
        print(f"Q: {question}\n分析结果: {analysis_result}")

        # 2. 让team评测分析结果和标准答案
        async for message in judge_agent.run_stream(
            task=TextMessage(
                content=f"请帮我检查问题和答案是否正确，只回答正确和不正确\n<question>{analysis_result}</question>\n<answer>{answer}</answer>",
                source="user",
            )
        ):
            if isinstance(message, TaskResult):
                autogen_result = message.model_dump()
                judge_result = autogen_result["messages"][-1]["content"]

        print("-" * 50)
        print(f"评测: {judge_result}\n")

        results.append(
            {
                "id": case["id"],
                "question": question,
                "answer": answer,
                "analysis_result": analysis_result,
                "judge_result": judge_result,
            }
        )

    # 保存结果到DataFrame并导出csv

    result_df = pd.DataFrame(results)
    result_csv_path = os.path.join(current_dir, "test_result_version2.csv")
    result_df.to_csv(result_csv_path, index=False, encoding="utf-8-sig")
    print(f"测试结果已保存到: {result_csv_path}")

    # 计算准确率

    correct_count = result_df["judge_result"].apply(lambda x: "正确" in str(x)).sum()
    total_count = len(result_df)
    accuracy = correct_count / total_count if total_count > 0 else 0
    print(f"准确率: {accuracy:.2%} ({correct_count}/{total_count})")

    # 将准确率信息也保存到DataFrame和csv
    summary_row = {
        "id": "准确率",
        "question": "",
        "answer": "",
        "analysis_result": "",
        "judge_result": f"{accuracy:.2%} ({correct_count}/{total_count})",
    }
    result_df_with_acc = pd.concat(
        [result_df, pd.DataFrame([summary_row])], ignore_index=True
    )
    result_df_with_acc.to_csv(result_csv_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    asyncio.run(main())
