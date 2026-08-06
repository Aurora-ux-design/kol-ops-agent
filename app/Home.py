import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.utils import bootstrap

st.set_page_config(page_title="达人运营智能 Agent", page_icon="🎯", layout="wide")
bootstrap()

st.title("达人运营智能 Agent")
st.caption("输入一个商品，Agent 告诉你应该找哪个达人、用什么脚本卖、佣金给到多少不亏。")

st.divider()
st.subheader("四个引擎")

col1, col2, col3, col4 = st.columns(4)
with col1, st.container(border=True):
    st.markdown("**🎯 达人匹配**")
    st.success("✅ 已完成")
    st.caption("向量粗排 + 确定性打分，附可读匹配理由")
    st.caption("👈 左侧「达人匹配」页")
with col2, st.container(border=True):
    st.markdown("**📝 脚本生成**")
    st.success("✅ 已完成")
    st.caption("口播/剧情/测评三形态，确定性合规检查")
    st.caption("👈 左侧「脚本生成」页")
with col3, st.container(border=True):
    st.markdown("**💰 损益计算**")
    st.success("✅ 已完成")
    st.caption("自然语言查佣金上限/ROI/保本线，算术全走确定性公式")
    st.caption("👈 左侧「损益查询」页")
with col4, st.container(border=True):
    st.markdown("**🔍 投产审核**")
    st.warning("⏳ V3.0 规划中")
    st.caption("异常检测 + 直播间品控三重信号交叉验证")
    st.caption("暂未接入")

st.divider()
st.subheader("为什么做这个项目")
st.markdown(
    """
做过 16 个月快消品牌产品运营，最大的感受是：达人运营工作**重复度极高、但匹配效率极低**。
同一批达人池，每次选品都要凭记忆和感觉重新想一遍"这次该找谁"；佣金谈判时手边没有实时的成本模型，
只能大致估算保本线；投放开着之后基本就是"人肉盯盘"，达人在直播间到底有没有认真讲本品，品牌方其实并不知道。

市面上也有蝉圈圈这类工具，年费五六万，但用下来发现一个核心问题：**它只给一个匹配结果，不给理由，也不能调**。
运营没法知道"为什么推荐这个达人"，更没法根据自己团队的经验去调整匹配逻辑——工具越黑盒，运营对它的信任度反而越低。

这个项目想验证的是：如果把"匹配理由可解释、匹配权重可调、关键决策留人工确认"这几件事做对，
能不能让运营真正开始信任并依赖这套系统，而不是把它当摆设。
"""
)

st.subheader("几条设计原则")
st.markdown(
    """
1. **钱的计算不经过 LLM**——中间算术全部走确定性 Python 函数，LLM 只做"自然语言 → 结构化参数"和"数字 → 人话"两端
2. **运营始终拥有最终拍板权**——涉及资金或对外内容的环节，Agent 只产出候选和建议，默认需要人工确认后才生效
3. **误判代价不对称，宁可"存疑"也不要武断判定**——单路信号不一致时应标记"存疑"交人工核查，不强行给二元结论
4. **可解释、可调，不做黑盒**——匹配分数、脚本生成都能输出"为什么"，权重/阈值可在配置里调，不用改代码
"""
)

st.divider()
st.caption(
    "四个引擎围绕一个决策闭环运转：选匹配达人 → 生成脚本 → 计算损益 → 审核通过 → 达人开播 → 监控投产 → 数据回流"
)
