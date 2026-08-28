#!/usr/bin/env python3
"""Check that the two-session teaching plan contains all required fields."""

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
    "苗东升",
    "中国人民大学出版社",
    "2010年3月",
    "方美琪",
    "汪小帆",
    "高等教育出版社",
    "2012年4月",
    "钟永光",
    "科学出版社",
    "2025年4月",
    "Melanie Mitchell",
    "Oxford University Press",
    "Barabási",
    "Cambridge University Press",
    "2016",
    "钱学森",
    "Nature Communications",
    "Holland",
]

missing = [item for item in required if item not in text]
session_markers = text.count("#### 课程思政教学内容设计")

print(f"文档: {DOC}")
print(f"字数: {len(text)}")
if missing:
    print("缺失条目:")
    for item in missing:
        print(f"  - {item}")
    sys.exit(1)

if session_markers < 2:
    print(f"思政栏目次数不足: {session_markers}")
    sys.exit(1)

print("校验通过：两次课所需栏目与核心教材信息均已填写。")
