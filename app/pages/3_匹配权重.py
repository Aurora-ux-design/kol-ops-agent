import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json

import streamlit as st

_WEIGHTS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "matching_weights.json"

st.set_page_config(page_title="匹配权重调控", page_icon="⚙️", layout="wide")
st.title("匹配权重调控")
st.caption("调整 5 个匹配维度的权重，保存后立即生效，不需要改代码或重启。")

with _WEIGHTS_PATH.open(encoding="utf-8") as f:
    config = json.load(f)

DIMENSION_LABELS = {
    "audience_overlap": "粉丝画像重合度",
    "content_style_match": "内容风格匹配",
    "historical_performance": "历史带货表现",
    "commission_fit": "佣金匹配度",
    "schedule_availability": "档期可用性",
}

weights = {}
with st.container(border=True):
    for key, label in DIMENSION_LABELS.items():
        input_col, bar_col = st.columns([2, 3])
        with input_col:
            weights[key] = st.number_input(
                label,
                min_value=0.0,
                max_value=1.0,
                value=float(config["dimension_weights"][key]),
                step=0.05,
            )
        with bar_col:
            st.progress(min(max(weights[key], 0.0), 1.0), text=f"{weights[key]:.0%}")

total = sum(weights.values())
if abs(total - 1.0) > 1e-6:
    st.warning(f"5 项权重之和是 {total:.2f}，不等于 1，保存前请调整。")
else:
    st.success(f"5 项权重之和是 {total:.2f}，可以保存。")

if st.button("保存", type="primary", disabled=abs(total - 1.0) > 1e-6):
    config["dimension_weights"] = weights
    with _WEIGHTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    st.success("已保存，下次匹配会用新权重。")
