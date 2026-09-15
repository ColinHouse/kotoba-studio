"""Prompt for contextual explanations aimed at Chinese-speaking learners."""

from __future__ import annotations

import json

SYSTEM = (
    "你是一位面向中文母语者的日语老师。你只解释当前这一句里目标词或表达的用法，"
    "不复述词典定义，不编造剧情，不根据单句断定人物关系。"
    "只输出一个 JSON 对象，不要输出任何其他文字。所有字段用简体中文。字段：\n"
    '  "meaning_here": 在这句话里的意思（一两句）；\n'
    '  "form": 词形说明（缩约/活用/敬体等，'
    "例如 しょうがない 是 しようがない 的口语形；无则填 null）；\n"
    '  "tone": 语气与语体（口语/敬体/粗俗/亲近/无奈等）；\n'
    '  "needs_context": 仅凭这句无法确定、需要上下文的部分（无则填 null）；\n'
    '  "daily_usable": 日常对话能否这样说，以及注意点；\n'
    '  "trap_for_zh": 对中文母语者的提醒（中日同形异义、易混词），无则填 null；\n'
    '  "confidence": 0 到 1 的数字，表示你对以上解释的把握。'
)


def explain_prompt(
    headword: str,
    reading: str,
    surface: str,
    sentence: str,
    prior_lines: list[str],
    glosses: list[str],
    trap: dict | None,
) -> tuple[str, str]:
    context = "\n".join(f"- {line}" for line in prior_lines[-3:]) or "（无）"
    payload = {
        "目标词": headword,
        "读音": reading or None,
        "在句中的形式": surface or headword,
        "当前句": sentence,
        "之前的几句（可能有帮助，禁止推断后续剧情）": context,
        "词典释义（仅供参考）": glosses[:4],
        "已知的同形词提示": trap,
    }
    user = json.dumps(payload, ensure_ascii=False, indent=1)
    return SYSTEM, user
