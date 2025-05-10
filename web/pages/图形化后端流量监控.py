import streamlit as st
import requests
import pandas as pd
# import plotly.graph_objects as go # No longer needed
from datetime import datetime
import time

# --- Configuration ---
API_URL = "https://localhost/metrics-json"  # Updated API endpoint
UPDATE_INTERVAL_SECONDS = 1
MAX_DATAPOINTS = 200

# It's good practice to have set_page_config as the first Streamlit command.
# If you have it in your main app page (e.g., 主页面.py) and this is a page in a multi-page app,
# then you might not need it here, or ensure it's only called once if this can be run standalone.
# For now, I'll keep it here, assuming this might be run as a standalone page sometimes.
if 'page_configured' not in st.session_state:
    st.set_page_config(
        page_title="后端流量实时监控 (Area Chart)",
        page_icon="🏞️",
        layout="wide"
    )
    st.session_state.page_configured = True

# --- Initialize Session State ---
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []
if 'request_sizes' not in st.session_state:
    st.session_state.request_sizes = []
if 'response_sizes' not in st.session_state:
    st.session_state.response_sizes = []
if 'error_count' not in st.session_state:
    st.session_state.error_count = 0
if 'last_request_size' not in st.session_state:
    st.session_state.last_request_size = 0
if 'last_response_size' not in st.session_state:
    st.session_state.last_response_size = 0
if 'last_api_response' not in st.session_state: # For debugging
    st.session_state.last_api_response = "No response yet."

# --- Helper Functions ---
def fetch_data():
    """Fetches data from the JSON API endpoint."""
    try:
        response = requests.get(API_URL, verify=False, timeout=5)
        st.session_state.last_api_response = response.text # Store raw text for debugging
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        
        request_size = data.get("nginx_http_request_bytes_last_second", 0)
        response_size = data.get("nginx_http_response_bytes_last_second", 0)
        
        st.session_state.last_request_size = request_size
        st.session_state.last_response_size = response_size
        
        return datetime.now(), request_size, response_size
    except requests.exceptions.RequestException as e:
        st.session_state.error_count += 1
        st.session_state.last_api_response = f"Request Error: {e}"
        # Return last known values on error to keep the chart from breaking if API is temp down
        return datetime.now(), st.session_state.last_request_size, st.session_state.last_response_size
    except ValueError as e: # JSONDecodeError is a subclass of ValueError
        st.session_state.error_count += 1
        st.session_state.last_api_response = f"JSON Parse Error: {e}. Raw response: {st.session_state.last_api_response}"
        return datetime.now(), st.session_state.last_request_size, st.session_state.last_response_size

# --- Page Layout ---
st.title("🏞️ 后端流量实时监控 (Area Chart)")
st.markdown(f"每 `{UPDATE_INTERVAL_SECONDS * 1000}` 毫秒从 `{API_URL}` 更新数据。图表最多显示 `{MAX_DATAPOINTS}` 个数据点。")

# Placeholders for metrics and chart
col1, col2, col3 = st.columns(3)
with col1:
    request_size_metric = st.empty()
with col2:
    response_size_metric = st.empty()
with col3:
    error_count_metric = st.empty()

chart_placeholder = st.empty()

st.subheader("最新API响应调试信息")
# Define the placeholder once, outside the loop
api_response_debug_placeholder = st.empty()

# --- Main Loop for Real-time Updates ---
while True:
    time.sleep(UPDATE_INTERVAL_SECONDS)
    timestamp, request_size, response_size = fetch_data()
    # Use st.code for displaying the raw API response text
    # No key is needed here as st.empty() manages the slot, and st.code is simpler.
    api_response_debug_placeholder.code(st.session_state.last_api_response, language="text")

    # Update data lists in session state (FIFO)
    st.session_state.timestamps.append(timestamp)
    st.session_state.request_sizes.append(request_size)
    st.session_state.response_sizes.append(response_size)

    # Keep lists to a maximum size
    if len(st.session_state.timestamps) > MAX_DATAPOINTS:
        st.session_state.timestamps.pop(0)
        st.session_state.request_sizes.pop(0)
        st.session_state.response_sizes.pop(0)

    # Update metrics
    request_size_metric.metric("当前请求大小 (bytes)", f"{st.session_state.last_request_size:,}")
    response_size_metric.metric("当前响应大小 (bytes)", f"{st.session_state.last_response_size:,}")
    error_count_metric.metric("API错误次数", st.session_state.error_count)

    # Prepare data for st.area_chart
    # st.area_chart expects a DataFrame where each column is a series to plot.
    # The index of the DataFrame is used for the x-axis.
    if st.session_state.timestamps: # Ensure there is data to plot
        chart_data = pd.DataFrame({
            '请求大小 (bytes)': st.session_state.request_sizes,
            '响应大小 (bytes)': st.session_state.response_sizes,
        }, index=pd.to_datetime(st.session_state.timestamps)) # Use timestamps as index
        
        chart_placeholder.area_chart(chart_data, height=400) # Adjust height as needed

    # time.sleep(UPDATE_INTERVAL_SECONDS) # Removed duplicate sleep
