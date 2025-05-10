import streamlit as st

st.title(f"欢迎来到 - 123")
st.write("这里是仪表盘的总体概览信息。")
st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.svg", width=300) # 示例图片

st.header("关键指标")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="活跃用户", value="1,274", delta="12%")
with col2:
    st.metric(label="API 调用次数 (今日)", value="85,302", delta="-2.5%")
with col3:
    st.metric(label="错误率", value="0.5%", delta="0.1%", delta_color="inverse")