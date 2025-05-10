import streamlit as st
import PageConfig
# --- Main Introduction ---
st.title("🚀 服务端后端监控网站")

st.markdown(
    """
    这里可以做到监管数据和流控
    您可以通过左侧的导航栏访问不同的功能模块，例如：


    *   **(其他页面1)**: 流量监控页面
    *   **(其他页面2)**: 测试页，暂且没有使用

    基于python的streamlit框架实现，后期可继续扩展。
    --- 
    *如果您有任何疑问或建议，请随时通过 "Get Help" 或 "Report a bug" 菜单项与我们联系。*
    """
)

st.info("小提示：您可以使用左侧的导航栏切换到不同的功能页面。", icon="ℹ️")

# --- Placeholder for further content or navigation to other pages ---
# Depending on how PageConfig and your multi-page app structure works,
# you might have more code here to display content or navigate.

# Example: if PageConfig handles page switching based on a selection
# if hasattr(PageConfig, 'run'):
#     PageConfig.run() 
# else:
#     st.write("请从侧边栏选择一个页面。")
