import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from contextlib import closing
from datetime import date

import streamlit as st

from data.db import get_all_products, get_connection
from engines.matching.pipeline import match_influencers

st.set_page_config(page_title="达人匹配", page_icon="🎯")
st.title("达人匹配")

with closing(get_connection()) as conn:
    products = get_all_products(conn)

if not products:
    st.warning("商品目录是空的，先在项目根目录跑 `python -m data.seed` 初始化数据。")
    st.stop()

product_options = {row["product_id"]: f"{row['product_id']} · {row['name']}" for row in products}
product_id = st.selectbox(
    "选择商品", options=list(product_options.keys()), format_func=lambda pid: product_options[pid]
)
requested_date = st.date_input("期望投放日期", value=date.today())

if st.button("开始匹配", type="primary"):
    with st.spinner("匹配中，第一次调用会加载本地 embedding 模型，可能要几秒到几十秒……"):
        try:
            result = match_influencers(product_id, requested_date=requested_date)
        except Exception as exc:  # 顶层 UI 错误边界，故意兜住所有异常给运营看友好提示
            st.error(f"匹配失败：{exc}")
            st.stop()

    st.subheader(f"Top{len(result.candidates)} 候选")
    for rank, candidate in enumerate(result.candidates, start=1):
        st.markdown(f"**{rank}. {candidate.influencer_id}** —— 总分 {candidate.weighted_total:.1f}")
        st.write(candidate.reason or "（没有生成理由）")
        with st.expander("查看 5 维度打分依据"):
            for dim in candidate.dimension_scores:
                st.write(f"- **{dim.name}**：{dim.score:.1f} 分 —— {dim.detail}")
