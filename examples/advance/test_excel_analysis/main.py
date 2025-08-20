import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from autogen_agentchat.conditions import (
    MaxMessageTermination,
    FunctionCallTermination,
)
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
import asyncio
import os
import pandas as pd
import json
from collections import defaultdict


from src.agents import (
    get_assistant_agent,
    get_generate_data_info_agent,
    get_judge_agent,
)
from src.db_manager import DuckDBManager


async def main() -> None:
    # 读取测试集
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "output_data.json")
    with open(json_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    # 按文件名对测试用例进行分组
    grouped_cases = defaultdict(list)
    for case in test_cases:
        grouped_cases[case["file_name"]].append(case)

    # 结果收集
    result_csv_path = os.path.join(current_dir, "test_result_version2.csv")
    # 写入表头
    with open(result_csv_path, "w", encoding="utf-8-sig") as f:
        f.write("id,question,answer,analysis_result,judge_result\n")

    for file_name, cases in grouped_cases.items():
        print(f"--- Processing file: {file_name} ---")
        excel_path = os.path.join(current_dir, "extracted_tables", file_name)

        try:
            df = pd.read_csv(excel_path)
        except FileNotFoundError:
            print(f"Error: File not found at {excel_path}")
            # 记录该文件下所有问题为失败
            for case in cases:
                row = {
                    "id": case["id"],
                    "question": case["question"],
                    "answer": case["answer"],
                    "analysis_result": "File not found",
                    "judge_result": "Error",
                }
                pd.DataFrame([row]).to_csv(
                    result_csv_path,
                    mode="a",
                    header=False,
                    index=False,
                    encoding="utf-8-sig",
                )
            continue

        # 为每个文件重置DuckDB表
        DuckDBManager.close()
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

        for case in cases:
            question = case["question"]
            answer = case["answer"]
            analysis_result = ""
            judge_result = ""

            response_agent = get_assistant_agent(question, new_data_info)
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

            row = {
                "id": case["id"],
                "question": question,
                "answer": answer,
                "analysis_result": analysis_result,
                "judge_result": judge_result,
            }
            pd.DataFrame([row]).to_csv(
                result_csv_path,
                mode="a",
                header=False,
                index=False,
                encoding="utf-8-sig",
            )

    print(f"测试结果已保存到: {result_csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
