import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from contextlib import closing
from datetime import date

import streamlit as st

from app.utils import product_picker
from data.db import get_all_products, get_connection
from engines.matching.pipeline import match_influencers

st.set_page_config(page_title="达人匹配", page_icon="🎯", layout="wide")
st.title("达人匹配")
st.caption("给定商品，从达人池里筛出并排序最匹配的候选，附可读理由。")

with closing(get_connection()) as conn:
    products = get_all_products(conn)

if not products:
    st.warning("商品目录是空的，先在项目根目录跑 `python -m data.seed` 初始化数据。")
    st.stop()

product_id = product_picker(products)
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
        with st.container(border=True):
            score_col, reason_col = st.columns([1, 4])
            with score_col:
                st.metric(f"第 {rank} 名", candidate.influencer_id)
                st.caption(f"总分 {candidate.weighted_total:.1f}")
            with reason_col:
                st.write(candidate.reason or "（没有生成理由）")
            with st.expander("查看 5 维度打分依据"):
                for dim in candidate.dimension_scores:
                    st.write(f"- **{dim.name}**：{dim.score:.1f} 分 —— {dim.detail}")
