import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(page_title="达人运营智能 Agent", page_icon="🎯")

st.title("达人运营智能 Agent")
st.caption("输入一个商品，Agent 告诉你应该找哪个达人、佣金给到多少不亏。")

st.markdown(
    """
达人运营的四个决策环节，本项目目前跑通了其中两个：

- **选谁带货** —— 达人匹配引擎：向量粗排 + 确定性打分，附可读匹配理由（左侧「matching」页）
- **赚不赚钱** —— 损益计算引擎：自然语言查询佣金上限/ROI/保本线，算术全部走确定性公式，LLM 只负责翻译成人话（左侧「profit_query」页）

脚本生成引擎、投产审核引擎还在规划中，暂未接入。

匹配引擎的 5 个打分维度权重可以在「weights」页实时调整，不需要改代码。

---

四个引擎围绕一个决策闭环运转：

`选匹配达人 → 生成脚本 → 计算损益 → 审核通过 → 达人开播 → 监控投产 → 数据回流`
"""
)
