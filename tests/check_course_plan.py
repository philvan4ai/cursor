#!/usr/bin/env python3
"""Check that the two-session teaching plan is ML-focused and complete."""

from pathlib import Path
import sys

DOC = Path(__file__).resolve().parents[1] / "docs" / "复杂系统理论与方法-26级学博留博-两次课教学信息.md"
text = DOC.read_text(encoding="utf-8")

required = [
    "《复杂系统理论与方法》",
    "26级学博留博",
    "推荐教材",
    "教学进度",
    "第1次课",
    "第2次课",
    "课程思政教学内容设计",
    "最新科研成果教学设计",
    "课程目标",
    "教学内容",
    "教学方法及形式",
    "必读书目",
    "参考文献目录",
    "思考讨论题",
    "机器学习",
    "周志华",
    "清华大学出版社",
    "2016年1月",
    "李航",
    "统计学习方法",
    "2019年5月",
    "邱锡鹏",
    "机械工业出版社",
    "2020年4月",
    "Goodfellow",
    "Deep Learning",
    "MIT Press",
    "Sutton",
    "Reinforcement Learning",
    "2018",
    "Hastie",
    "深度学习",
    "图神经网络",
    "强化学习",
]

forbidden_as_main = [
    "从还原论到复杂性",
    "涌现、自组织与复杂适应系统",
]

missing = [item for item in required if item not in text]
session_markers = text.count("#### 课程思政教学内容设计")
ml_count = text.count("机器学习")

print(f"文档: {DOC}")
print(f"字数: {len(text)}")
print(f"“机器学习”出现次数: {ml_count}")

errors = []
if missing:
    errors.append("缺失条目: " + ", ".join(missing))
if session_markers < 2:
    errors.append(f"思政栏目次数不足: {session_markers}")
if ml_count < 8:
    errors.append("机器学习主线不够突出")
for phrase in forbidden_as_main:
    if phrase in text:
        errors.append(f"仍保留旧主题标题: {phrase}")

if errors:
    print("校验失败:")
    for item in errors:
        print(f"  - {item}")
    sys.exit(1)

print("校验通过：两次课以机器学习为主线，所需栏目与教材信息均已填写。")
