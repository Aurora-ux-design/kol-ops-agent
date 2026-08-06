import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from contextlib import closing

import streamlit as st

from app.utils import bootstrap, influencer_picker, product_picker
from data.db import get_all_influencers, get_all_products, get_connection
from engines.script.models import ScriptFormat
from engines.script.pipeline import generate_scripts

st.set_page_config(page_title="脚本生成", page_icon="📝", layout="wide")
bootstrap()
st.title("脚本生成")
st.caption("给定商品+达人，生成口播/剧情/测评三版脚本，附确定性合规词检查。")

with closing(get_connection()) as conn:
    products = get_all_products(conn)
    influencers = get_all_influencers(conn)

if not products or not influencers:
    st.warning("商品或达人数据是空的，先在项目根目录跑 `python -m data.seed` 初始化数据。")
    st.stop()

product_id = product_picker(products)
influencer_id = influencer_picker(influencers)
target_seconds = st.slider("目标时长（秒）", min_value=15, max_value=90, value=30, step=5)

FORMAT_LABELS = {
    ScriptFormat.VOICEOVER: "口播",
    ScriptFormat.NARRATIVE: "剧情",
    ScriptFormat.REVIEW: "测评",
}

if st.button("生成脚本", type="primary"):
    with st.spinner("生成中，三种形态各要调用一次 LLM，可能要十几秒……"):
        try:
            result = generate_scripts(product_id, influencer_id, target_seconds=target_seconds)
        except Exception as exc:  # 顶层 UI 错误边界，故意兜住所有异常给运营看友好提示
            st.error(f"生成失败：{exc}")
            st.stop()

    tabs = st.tabs([FORMAT_LABELS[variant.format] for variant in result.variants])
    for tab, variant in zip(tabs, result.variants):
        with tab:
            if variant.compliance_flags:
                st.warning(f"命中违禁词，请人工核查后再使用：{'、'.join(variant.compliance_flags)}")
            with st.container(border=True):
                st.text(variant.rendered_text)
            st.caption(f"适用场景：{variant.applicable_scenario}")
