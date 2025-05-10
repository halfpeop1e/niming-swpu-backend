import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import utils

# 获取style.json文件
style_dict = utils.load_json('style.json')
# --- 页面配置 (可选，但推荐放在开头) ---
st.set_page_config(
    page_title="我的监控仪表盘",
    page_icon="📊",
    layout="wide", # 可以是 "centered" 或 "wide"
    initial_sidebar_state="expanded" # "auto", "expanded", "collapsed"
)

