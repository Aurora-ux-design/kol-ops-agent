import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from app.utils import bootstrap
from engines.script.hotspots import create_hotspot, list_hotspots, set_hotspot_enabled

st.set_page_config(page_title="热点库", page_icon="🔥", layout="wide")
bootstrap()
st.title("热点库")
st.caption(
    "运营手动补充热点（PRD 里热点情报管道的数据源之一），"
    "脚本生成时会检索最相关的已启用热点注入 prompt——这是检索增强生成（RAG），不是凭空瞎编。"
)

with st.form("add_hotspot", clear_on_submit=True):
    keyword = st.text_input("热点关键词/短语", placeholder="比如：秋天的第一杯奶茶")
    description = st.text_area("描述", placeholder="这个梗/结构/Hook 大概是什么样，适合什么场景")
    submitted = st.form_submit_button("添加", type="primary")
    if submitted:
        if not keyword.strip() or not description.strip():
            st.warning("关键词和描述都要填。")
        else:
            with st.spinner("添加中……"):
                try:
                    create_hotspot(keyword.strip(), description.strip())
                except Exception as exc:  # 顶层 UI 错误边界，故意兜住所有异常给运营看友好提示
                    st.error(f"添加失败：{exc}")
                else:
                    st.success("已添加并生效。")

st.subheader("已有热点")
hotspots = list_hotspots()
if not hotspots:
    st.info("还没有热点，先在上面加一条。")
else:
    for hotspot in hotspots:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{hotspot.keyword}**")
                st.caption(hotspot.description)
            with col2:
                enabled = st.toggle(
                    "启用", value=hotspot.is_enabled, key=f"hotspot_{hotspot.hotspot_id}"
                )
                if enabled != hotspot.is_enabled:
                    set_hotspot_enabled(hotspot.hotspot_id, enabled)
                    st.rerun()
