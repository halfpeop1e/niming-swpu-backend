# import streamlit as st
# from streamlit_option_menu import option_menu
# import pandas as pd

# # markdown
# st.markdown('Streamlit Demo')

# # 设置网页标题
# st.title('一个傻瓜式构建可视化 web的 Python 神器 -- streamlit')

# # 展示一级标题
# st.header('1. 安装')

# st.text('和安装其他包一样，安装 streamlit 非常简单，一条命令即可')
# code1 = '''pip3 install streamlit'''
# st.code(code1, language='bash')


# # 展示一级标题
# st.header('2. 使用')

# # 展示二级标题
# st.subheader('2.1 生成 Markdown 文档')

# # 纯文本
# st.text('导入 streamlit 后，就可以直接使用 st.markdown() 初始化')

# # 展示代码，有高亮效果
# code2 = '''import streamlit as st
# st.markdown('Streamlit Demo')'''
# st.code(code2, language='python')


# # --- 根据选择的页面显示不同内容 ---
# if selected_page == "仪表盘概览":
#     st.title(f"欢迎来到 - {selected_page}")
#     st.write("这里是仪表盘的总体概览信息。")
#     st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.svg", width=300) # 示例图片
    
#     st.header("关键指标")
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.metric(label="活跃用户", value="1,274", delta="12%")
#     with col2:
#         st.metric(label="API 调用次数 (今日)", value="85,302", delta="-2.5%")
#     with col3:
#         st.metric(label="错误率", value="0.5%", delta="0.1%", delta_color="inverse")

# elif selected_page == "API 指标":
#     st.title(f"详细 - {selected_page}")
#     st.write("这里展示详细的 API 性能指标和图表。")
#     # --- 在这里放置你的 Plotly 图表或其他 API 指标相关内容 ---
#     st.subheader("请求延迟分布 (示例)")
#     # 模拟数据
#     import numpy as np
#     import pandas as pd
#     import plotly.express as px
#     latency_data = np.random.lognormal(mean=1, sigma=0.5, size=500) * 100 # ms
#     df_latency = pd.DataFrame(latency_data, columns=['latency_ms'])
#     fig = px.histogram(df_latency, x="latency_ms", nbins=50, title="API 请求延迟 (ms)")
#     st.plotly_chart(fig, use_container_width=True)

# elif selected_page == "日志查看器":
#     st.title(f"应用 - {selected_page}")
#     st.write("这里可以查看和筛选应用程序的日志。")
#     # --- 在这里放置你的日志查看和筛选逻辑 ---
#     log_data = [
#         {"timestamp": "2023-05-07 10:00:01", "level": "INFO", "message": "User 'admin' logged in."},
#         {"timestamp": "2023-05-07 10:02:30", "level": "WARNING", "message": "Low disk space detected."},
#         {"timestamp": "2023-05-07 10:05:15", "level": "ERROR", "message": "Failed to process payment for order 123."},
#         {"timestamp": "2023-05-07 10:05:45", "level": "INFO", "message": "Order 124 processed successfully."},
#     ]
#     df_logs = pd.DataFrame(log_data)
#     st.dataframe(df_logs, use_container_width=True)

#     log_level_filter = st.selectbox("按级别筛选日志:", options=["所有"] + sorted(df_logs['level'].unique()))
#     if log_level_filter != "所有":
#         st.dataframe(df_logs[df_logs['level'] == log_level_filter], use_container_width=True)


# elif selected_page == "用户管理":
#     st.title(f"系统 - {selected_page}")
#     st.write("这里可以管理用户信息。")
#     # --- 用户管理相关内容 ---
#     if st.button("添加新用户"):
#         st.success("跳转到添加用户页面 (模拟)")

# elif selected_page == "系统设置":
#     st.title(f"配置 - {selected_page}")
#     st.write("这里可以配置系统参数。")
#     # --- 系统设置相关内容 ---
#     api_key = st.text_input("API 密钥", type="password", value="***********")
#     if st.checkbox("启用高级功能"):
#         st.write("高级功能已启用！")

# # --- 页脚 (可选) ---
# st.sidebar.markdown("---")
# st.sidebar.info("监控系统 v0.1.0")
import utils
print(utils.load_json('style.json'))
# 将json文件转换为python字典
style_dict = utils.load_json('style.json')
print(style_dict)
