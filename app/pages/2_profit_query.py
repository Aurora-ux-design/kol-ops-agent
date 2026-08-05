import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import dataclasses
from contextlib import closing
from decimal import Decimal

import streamlit as st

from data.db import get_all_products, get_connection
from engines.matching.pipeline import product_row_to_profile
from engines.profit.nl_query import (
    QueryIntent,
    answer_breakeven_query,
    answer_net_profit_query,
    extract_query_params,
)

st.set_page_config(page_title="损益查询", page_icon="💰")
st.title("损益查询")

with closing(get_connection()) as conn:
    products = get_all_products(conn)

if not products:
    st.warning("商品目录是空的，先在项目根目录跑 `python -m data.seed` 初始化数据。")
    st.stop()

product_options = {row["product_id"]: f"{row['product_id']} · {row['name']}" for row in products}
product_id = st.selectbox(
    "选择商品", options=list(product_options.keys()), format_func=lambda pid: product_options[pid]
)
selected_row = next(row for row in products if row["product_id"] == product_id)
product = product_row_to_profile(selected_row)

query = st.text_input(
    "自然语言提问",
    placeholder="价格已经从选中商品带入，问题里不用重复提，比如直接问「给30%佣金还能赚多少」",
)

if st.button("解析"):
    if not query.strip():
        st.warning("先输入问题再解析。")
    else:
        with st.spinner("解析中……"):
            try:
                st.session_state["profit_query"] = query
                st.session_state["profit_params"] = extract_query_params(query)
            except Exception as exc:  # 顶层 UI 错误边界，故意兜住所有异常给运营看友好提示
                st.error(f"解析失败：{exc}")
                st.session_state.pop("profit_params", None)

params = st.session_state.get("profit_params")

if params is not None:
    st.subheader("确认参数")
    intent_label = "净利润/ROI 查询" if params.intent is QueryIntent.NET_PROFIT else "保本佣金率查询"
    st.write(f"意图：{intent_label}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("商品目录里的真实售价（计算实际用这个）", f"{product.selling_price} 元")
    with col2:
        st.metric("LLM 从问题里解析出的售价（仅供比对）", f"{params.selling_price} 元")

    confirmed_rate = None
    if params.intent is QueryIntent.NET_PROFIT:
        confirmed_rate = st.number_input(
            "达人佣金率（0~1 之间的小数）",
            min_value=0.0,
            max_value=1.0,
            value=float(params.influencer_commission_rate or 0),
            step=0.01,
        )

    if st.button("计算", type="primary"):
        confirmed_params = dataclasses.replace(params, selling_price=product.selling_price)
        if params.intent is QueryIntent.NET_PROFIT:
            confirmed_params = dataclasses.replace(
                confirmed_params, influencer_commission_rate=Decimal(str(confirmed_rate))
            )

        with st.spinner("计算中……"):
            try:
                if confirmed_params.intent is QueryIntent.NET_PROFIT:
                    result, explanation = answer_net_profit_query(
                        st.session_state["profit_query"],
                        confirmed_params,
                        product.cost_structure,
                        product.platform_commission_rate,
                    )
                    st.metric("净利润", f"{result.net_profit:.2f} 元")
                    st.metric("ROI", f"{result.roi:.2f}")
                    st.metric("保本佣金率", f"{result.breakeven_commission_rate:.2%}")
                else:
                    breakeven_rate, explanation = answer_breakeven_query(
                        st.session_state["profit_query"],
                        confirmed_params,
                        product.cost_structure,
                        product.platform_commission_rate,
                    )
                    st.metric("保本佣金率", f"{breakeven_rate:.2%}")
            except Exception as exc:
                st.error(f"计算失败：{exc}")
                st.stop()

        st.write(explanation)
