import streamlit as st
# import requests # No longer needed for login_number if fetching directly from Redis
from utils.redis_conn import get_redis_client

LOGIN_COUNTER_KEY_IN_REDIS = "login_number" # The key used by FastAPI in Redis
TOTAL_API_CALLS_KEY_IN_REDIS = "total_api_calls" # Key used in FastAPI
SIGNUP_COUNTER_KEY_IN_REDIS = "signup_number" # Assuming you'll want this too

# 从redis中获取登录次数
def get_count_from_redis(redis_key: str, metric_name: str) -> int:
    """Generic function to fetch a named counter from Redis."""
    redis_client = get_redis_client()
    if redis_client:
        try:
            count_str = redis_client.get(redis_key)
            if count_str is not None:
                try:
                    return int(count_str)
                except ValueError:
                    st.error(f"Could not convert value of '{metric_name}' ('{redis_key}': '{count_str}') from Redis to an integer.")
                    return 0 # Conversion error
            else:
                # Key doesn't exist in Redis, treat as 0 for a counter
                # st.info(f"Metric '{metric_name}' ('{redis_key}') not found in Redis. Defaulting to 0.")
                return 0 
        except Exception as e:
            st.error(f"Error fetching '{metric_name}' ('{redis_key}') from Redis: {e}")
            return 0 # Other Redis errors
    else:
        st.error(f"Failed to connect to Redis. Cannot fetch '{metric_name}' ('{redis_key}').")
        return 0 # Connection failed

# Fetch data when the page loads
live_login_count = get_count_from_redis(LOGIN_COUNTER_KEY_IN_REDIS, "用户访问量")
total_api_calls = get_count_from_redis(TOTAL_API_CALLS_KEY_IN_REDIS, "总API调用次数")
signup_count = get_count_from_redis(SIGNUP_COUNTER_KEY_IN_REDIS, "用户注册数")

st.title(f"欢迎来到 - 在线流量监控页面")
st.write("这里是仪表盘的总体概览信息。")
#st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.svg", width=300) # 示例图片
st.header("关键指标")
col1, col2, col3, col4 = st.columns(4) # Added a 4th column for signup_count
with col1:
    st.metric(label="用户访问量 (登录)", value=live_login_count, delta_color="off") # delta can be dynamic later
with col2:
    st.metric(label="总API调用次数", value=total_api_calls, delta_color="off")
with col3:
    st.metric(label="用户注册数", value=signup_count, delta_color="off")
#with col4:
    # Example: Error rate could be calculated or fetched if available
    #st.metric(label="错误率", value="0.5%", delta="0.1%", delta_color="inverse")