#!/usr/bin/env python3
"""
合并question.json和answers.json文件的脚本
"""
import json


def merge_questions_answers():
    """合并问题和答案文件"""
    # 读取两个JSON文件
    with open("question.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    with open("answers.json", "r", encoding="utf-8") as f:
        answers = json.load(f)

    print(f"读取到 {len(questions)} 个问题")
    print(f"读取到 {len(answers)} 个答案")

    # 创建答案字典，以id为键
    answers_dict = {item["id"]: item for item in answers}

    # 合并数据
    merged_data = []
    for question in questions:
        question_id = question["id"]
        merged_item = question.copy()  # 复制问题数据

        # 如果存在对应的答案，添加答案信息
        if question_id in answers_dict:
            answer_data = answers_dict[question_id]
            merged_item["answer"] = answer_data["answer"]
            merged_item["status"] = answer_data["status"]
        else:
            merged_item["answer"] = None
            merged_item["status"] = "unknown"

        merged_data.append(merged_item)

    # 将合并后的数据写入新文件
    with open("merged_questions_answers.json", "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print("文件合并完成！已创建 merged_questions_answers.json")
    print(f"合并了 {len(merged_data)} 个条目")


if __name__ == "__main__":
    merge_questions_answers()
