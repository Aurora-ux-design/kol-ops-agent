from __future__ import annotations

import os
import sqlite3
from contextlib import closing

import streamlit as st

from data import db as data_db


def _ensure_env_from_secrets() -> None:
    # 本地开发靠 .env（load_dotenv 已经在 integrations/llm_client.py 里做了），
    # 云端部署没有 .env，只能从 Streamlit 的 secrets 管理里取，桥接进 os.environ
    # 这样 llm_client.py 读 os.environ["DEEPSEEK_API_KEY"] 的代码不用因为部署环境改
    if "DEEPSEEK_API_KEY" in os.environ:
        return
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        return
    os.environ["DEEPSEEK_API_KEY"] = api_key


@st.cache_resource
def _ensure_seeded() -> None:
    # 云端是全新环境，data/kol_ops.db 和 data/chroma/ 都没提交到仓库（故意的，见 .gitignore）。
    # 第一次有人打开应用时，检测到商品目录是空的就自动跑一遍 seed，本地已经 seed 过的话这里直接跳过。
    # 用 st.cache_resource 包一层，保证这个检测+跑 seed 的过程每个进程只执行一次，不会每次翻页都重跑。
    from data import seed as data_seed

    with closing(data_db.get_connection()) as conn:
        data_db.init_db(conn)
        already_seeded = len(data_db.get_all_products(conn)) > 0
    if not already_seeded:
        data_seed.seed()


def bootstrap() -> None:
    _ensure_env_from_secrets()
    _ensure_seeded()


def product_picker(products: list[sqlite3.Row], label: str = "选择商品") -> str:
    options = {row["product_id"]: f"{row['product_id']} · {row['name']}" for row in products}
    return st.selectbox(label, options=list(options.keys()), format_func=lambda pid: options[pid])


def influencer_picker(influencers: list[sqlite3.Row], label: str = "选择达人") -> str:
    options = {row["influencer_id"]: f"{row['influencer_id']} · {row['name']}" for row in influencers}
    return st.selectbox(label, options=list(options.keys()), format_func=lambda iid: options[iid])
