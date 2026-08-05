from __future__ import annotations

import sqlite3

import streamlit as st


def product_picker(products: list[sqlite3.Row], label: str = "选择商品") -> str:
    options = {row["product_id"]: f"{row['product_id']} · {row['name']}" for row in products}
    return st.selectbox(label, options=list(options.keys()), format_func=lambda pid: options[pid])


def influencer_picker(influencers: list[sqlite3.Row], label: str = "选择达人") -> str:
    options = {row["influencer_id"]: f"{row['influencer_id']} · {row['name']}" for row in influencers}
    return st.selectbox(label, options=list(options.keys()), format_func=lambda iid: options[iid])
