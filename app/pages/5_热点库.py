import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from app.utils import bootstrap
from engines.script.hotspot_notes import extract_hotspot_from_note
from engines.script.hotspots import create_hotspot, list_hotspots, set_hotspot_enabled

st.set_page_config(page_title="热点库", page_icon="🔥", layout="wide")
bootstrap()
st.title("热点库")
st.caption(
    "运营手动补充热点（PRD 里热点情报管道的数据源之一），"
    "脚本生成时会检索最相关的已启用热点注入 prompt——这是检索增强生成（RAG），不是凭空瞎编。"
)

tab_structured, tab_note = st.tabs(["结构化填写", "自然语言备注"])

with tab_structured:
    with st.form("add_hotspot_structured", clear_on_submit=True):
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

with tab_note:
    st.caption(
        "写一段大白话备注（可以是自己的观察，也可以是刷到某条小红书/抖音视频后的感想），"
        "LLM 帮你提炼成关键词和结构化描述。链接只作为引用保存，不会自动分析视频内容——"
        "内容判断还是要靠你自己看过之后写的备注。"
    )
    note = st.text_area(
        "自然语言备注",
        placeholder="比如：刷到好几个美妆达人开头都用很夸张的反问句，感觉完播率不错",
        key="hotspot_note_input",
    )
    source_url = st.text_input(
        "参考链接（可选）", placeholder="小红书/抖音视频链接", key="hotspot_source_url_input"
    )

    if st.button("解析"):
        if not note.strip():
            st.warning("先写点备注再解析。")
        else:
            with st.spinner("解析中……"):
                try:
                    extracted_keyword, extracted_description = extract_hotspot_from_note(note.strip())
                except Exception as exc:  # 顶层 UI 错误边界，故意兜住所有异常给运营看友好提示
                    st.error(f"解析失败：{exc}")
                else:
                    st.session_state["hotspot_note_raw"] = note.strip()
                    st.session_state["hotspot_note_source_url"] = source_url.strip() or None
                    st.session_state["hotspot_note_keyword"] = extracted_keyword
                    st.session_state["hotspot_note_description"] = extracted_description
                    # 确认框那两个输入控件一旦渲染过就会记住自己的状态，覆盖掉下面的 value=——
                    # 解析新备注时要先清掉，不然确认框会一直显示上一次解析的旧结果
                    st.session_state.pop("confirm_keyword", None)
                    st.session_state.pop("confirm_description", None)

    if "hotspot_note_keyword" in st.session_state:
        with st.container(border=True):
            st.subheader("确认提炼结果")
            confirmed_keyword = st.text_input(
                "关键词/短语", value=st.session_state["hotspot_note_keyword"], key="confirm_keyword"
            )
            confirmed_description = st.text_area(
                "描述", value=st.session_state["hotspot_note_description"], key="confirm_description"
            )
            if st.session_state.get("hotspot_note_source_url"):
                st.caption(f"参考链接：{st.session_state['hotspot_note_source_url']}")

            if st.button("确认添加", type="primary"):
                with st.spinner("添加中……"):
                    try:
                        create_hotspot(
                            confirmed_keyword.strip(),
                            confirmed_description.strip(),
                            source_url=st.session_state.get("hotspot_note_source_url"),
                            raw_note=st.session_state.get("hotspot_note_raw"),
                        )
                    except Exception as exc:
                        st.error(f"添加失败：{exc}")
                    else:
                        st.success("已添加并生效。")
                        for key in (
                            "hotspot_note_raw",
                            "hotspot_note_source_url",
                            "hotspot_note_keyword",
                            "hotspot_note_description",
                        ):
                            st.session_state.pop(key, None)
                        st.rerun()

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
                if hotspot.source_url:
                    st.caption(f"🔗 [参考链接]({hotspot.source_url})")
                if hotspot.raw_note:
                    with st.expander("查看原始备注"):
                        st.write(hotspot.raw_note)
            with col2:
                enabled = st.toggle(
                    "启用", value=hotspot.is_enabled, key=f"hotspot_{hotspot.hotspot_id}"
                )
                if enabled != hotspot.is_enabled:
                    set_hotspot_enabled(hotspot.hotspot_id, enabled)
                    st.rerun()
