import streamlit as st
import requests
from datetime import datetime # Not strictly used in this version, but good to keep if needed later
import time # Not strictly used in this version

# --- Page Configuration ---
# Ensure this is the first Streamlit command, except for comments and imports.
if 'page_config_图床' not in st.session_state:
    st.set_page_config(
        page_title="图床",
        page_icon="🖼️",
        layout="wide"
    )
    st.session_state.page_config_图床 = True

# --- API Configuration ---
API_BASE_URL = "http://localhost:10009/api/v2/"

# --- Session State Initialization ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'auth_token' not in st.session_state:
    # Placeholder for token. User's code hardcodes it in headers_token for now.
    # The "获取token" button can be modified to set this state.
    st.session_state.auth_token = "14|qdU50u07xpfsMhSutwn1KhsdSg29EnWUaJn9JGf5" # Default/example from user's code
if 'api_response_data' not in st.session_state:
    st.session_state.api_response_data = {}

# --- Data Structure Definitions (based on actual API response) ---
# For documentation/reference, matching the provided JSON output
image_item_links_structure = {
    "url": str,
    "html": str,
    "bbcode": str,
    "markdown": str,
    "markdown_with_link": str,
    "thumbnail_url": str, # or None
}

image_item_structure = {
    "key": str,
    "name": str,
    "origin_name": str,
    "size": float,
    "mimetype": str,
    "extension": str,
    "md5": str,
    "sha1": str,
    "width": int,
    "height": int,
    "human_date": str,
    "date": str,
    "pathname": str,
    "links": image_item_links_structure,
}

api_data_structure = {
    "current_page": int,
    "data": [image_item_structure], # List of image_item_structure
    "first_page_url": str,
    "from": int, # or None
    "last_page": int,
    "last_page_url": str,
    "links": list, # List of pagination link objects
    "next_page_url": str, # or None
    "path": str,
    "per_page": int,
    "prev_page_url": str, # or None
    "to": int, # or None
    "total": int
}

api_response_structure = {
    "status": bool,
    "message": str,
    "data": api_data_structure,
}

# --- Upload API Data Structure Definitions ---
upload_response_links_structure = {
    "url": str,
    "html": str,
    "bbcode": str,
    "markdown": str,
    "markdown_with_link": str,
    "thumbnail_url": str,
}

# 上传响应数据结构
upload_response_data_structure = {
    "key": str,
    "name": str,
    "pathname": str,
    "origin_name": str,
    "size": float,
    "mimetype": str,
    "extension": str,
    "md5": str,
    "sha1": str,
    "links": upload_response_links_structure,
}

# 上传API响应数据结构
upload_api_response_structure = {
    "status": bool,
    "message": str,
    "data": upload_response_data_structure, # Can be None on failure
}

# --- API Interaction ---
# Token acquisition part from user
post_data_for_token = {
    "email": "2074288854@qq.com",
    "password": "1996yong" # Be careful with hardcoding credentials
}
headers_for_token = {
    "Accept": "application/json",
}

if st.sidebar.button("获取/刷新Token (可选)"):
    try:
        response = requests.post(API_BASE_URL + "tokens", data=post_data_for_token, headers=headers_for_token, verify=False, timeout=10)
        st.sidebar.write(f"Token API Status Code: {response.status_code}")
        token_response_json = response.json()
        if response.status_code == 200 and token_response_json.get("status"):
            st.session_state.auth_token = token_response_json.get("data", {}).get("token")
            st.sidebar.success(f"Token acquired: {st.session_state.auth_token}")
            st.session_state.api_response_data = token_response_json # Show token response
        else:
            st.sidebar.error(f"Token acquisition failed: {token_response_json.get('message', 'Unknown error')}")
            st.session_state.api_response_data = token_response_json
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Token API Request Error: {e}")
        st.session_state.api_response_data = {"error": str(e)}
    except ValueError as e: # Includes JSONDecodeError
        st.sidebar.error(f"Token API JSON Parse Error: {e}. Response: {response.text if 'response' in locals() else 'No response text'}")
        st.session_state.api_response_data = {"error": str(e), "raw_response": response.text if 'response' in locals() else 'No response text'}


# Headers for image requests using the token
headers_for_images = {
    "Authorization": f"Bearer {st.session_state.auth_token}",
    "Accept": "application/json",
}

# Default parameters for image listing
# These could be made into st.sidebar inputs
default_params = {
    "order": "newest",  # newest, earliest, most, least
    "permission": "public", # public, private
    "album_id": 1, # Example: 1 or None for all
    "keyword": "",
}

def fetch_images(page_num, order="newest", permission="public", album_id=None, keyword=""):
    params = {
        "page": page_num,
        "order": order,
        "permission": permission,
        "keyword": keyword,
    }
    if album_id is not None:
        params["album_id"] = album_id

    try:
        request = requests.get(API_BASE_URL + "images", headers=headers_for_images, params=params, verify=False, timeout=10)
        st.session_state.api_response_data = {"status_code": request.status_code, "text": request.text, "url": request.url} # Store raw info first
        
        response_json = request.json()
        st.session_state.api_response_data = response_json # Replace with parsed JSON if successful

        if request.status_code == 200 and response_json.get("status"):
            data_payload = response_json.get("data", {})
            images_list = data_payload.get("data", [])
            last_page = data_payload.get("last_page", 1)
            current_api_page = data_payload.get("current_page", 1)
            total_images = data_payload.get("total", 0)
            return images_list, last_page, current_api_page, total_images
        else:
            st.error(f"API Error: {response_json.get('message', 'Failed to fetch images.')} (Status: {request.status_code})")
            return [], 1, 1, 0
            
    except requests.exceptions.RequestException as e:
        st.error(f"Request Error: {e}")
        st.session_state.api_response_data = {"error": str(e), "details": "RequestException during image fetch"}
        return [], 1, 1, 0
    except ValueError as e:  # Includes JSONDecodeError
        st.error(f"JSON Decode Error: {e}. Raw response text was stored for debugging.")
        # The raw response is already in st.session_state.api_response_data from before the .json() call
        return [], 1, 1, 0

# --- Page Layout & Logic ---
st.title("🖼️ 图床画廊")

# --- Image Upload Section ---
st.header("📤 上传新图片")
uploaded_file = st.file_uploader("选择图片文件 (jpg, jpeg, png, gif)...", type=["jpg", "jpeg", "png", "gif"], key="file_uploader")

if uploaded_file is not None:
    st.image(uploaded_file, caption=f"待上传: {uploaded_file.name}", width=200)
    
    # strategy_id_input = st.number_input("储存策略ID (可选)", min_value=1, step=1, value=None, key="strategy_id")

    if st.button(f"上传: {uploaded_file.name}", key="upload_button"):
        if not st.session_state.auth_token or st.session_state.auth_token == "3|Q07kKqG6GqDNUO6W2rPi94HuQTuckvnkEFM5rFdP": # Check if token is the placeholder
            st.warning("请先在侧边栏获取有效的API Token再上传图片。如果已获取，请确保它已更新。")
        else:
            files_payload = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            # upload_data_payload = {}
            # if strategy_id_input:
            #     upload_data_payload['strategy_id'] = strategy_id_input

            current_headers_for_upload = {
                "Authorization": f"Bearer {st.session_state.auth_token}",
                "Accept": "application/json",
            }

            with st.spinner("正在上传图片..."):
                try:
                    upload_response = requests.post(
                        API_BASE_URL + "upload",
                        headers=current_headers_for_upload,
                        files=files_payload,
                        # data=upload_data_payload, # If sending strategy_id
                        verify=False,
                        timeout=60 # Increased timeout for uploads
                    )
                    
                    st.subheader("上传响应:")
                    try:
                        upload_json_response = upload_response.json()
                        st.json(upload_json_response)
                        if upload_response.status_code < 300 and upload_json_response.get("status"):
                            st.success(f"图片上传成功: {upload_json_response.get('data', {}).get('name')}")
                            if upload_json_response.get('data') and upload_json_response['data'].get('links'):
                                st.image(upload_json_response['data']['links'].get('url'), caption="上传成功", width=200)
                            # Optionally, trigger a rerun to refresh the gallery if it should show the new image immediately
                            # This might require adjusting pagination or how filters are reapplied.
                            # For now, user has to manually navigate or refresh to see it in the gallery below.
                            # st.button("刷新图库查看 (可能需要调整页码)")
                        else:
                            err_msg = upload_json_response.get('message', f'HTTP Status {upload_response.status_code}')
                            st.error(f"上传失败: {err_msg}")
                    except ValueError: # JSONDecodeError
                        st.error(f"上传响应解析失败 (非JSON). Status: {upload_response.status_code}")
                        st.text(upload_response.text)

                except requests.exceptions.RequestException as e:
                    st.error(f"上传请求错误: {e}")

st.markdown("---") # Separator before the gallery

# Sidebar for controls (optional, can be in main page)
st.sidebar.header("筛选条件")
# For simplicity, using hardcoded params. Can be replaced with st.selectbox, st.text_input etc.
selected_order = st.sidebar.selectbox("排序", ["newest", "earliest", "most", "least"], index=["newest", "earliest", "most", "least"].index(default_params["order"]))
selected_permission = st.sidebar.selectbox("权限", ["public", "private"], index=["public", "private"].index(default_params["permission"]))
# album_id can be an integer or None. For now, let's use a text input allowing empty for None.
album_id_input = st.sidebar.text_input("相册ID (可选)", value=str(default_params["album_id"] if default_params["album_id"] is not None else ""))
selected_keyword = st.sidebar.text_input("关键词", value=default_params["keyword"])

# Convert album_id_input to int if not empty, else None
try:
    current_album_id = int(album_id_input) if album_id_input else None
except ValueError:
    st.sidebar.warning("相册ID必须是数字。")
    current_album_id = None


# Fetch data for the current page from session state
images, last_page_num, current_api_page_num, total_items = fetch_images(
    st.session_state.current_page,
    order=selected_order,
    permission=selected_permission,
    album_id=current_album_id,
    keyword=selected_keyword
)

# Pagination controls
st.write(f"总共 {total_items} 张图片。 当前页: {st.session_state.current_page} / {last_page_num}")

col_prev, col_page_info, col_next = st.columns([1, 3, 1])

with col_prev:
    if st.button("上一页", disabled=(st.session_state.current_page <= 1)):
        st.session_state.current_page -= 1
        st.rerun() # Rerun to fetch new page

with col_next:
    if st.button("下一页", disabled=(st.session_state.current_page >= last_page_num)):
        st.session_state.current_page += 1
        st.rerun()

st.markdown("---")

# Display Images
if images:
    num_images = len(images)
    cols_per_row = 5
    
    for i in range(0, num_images, cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < num_images:
                image_item = images[i+j]
                # Directly use the 'url' from the links
                img_url_to_display = image_item.get("links", {}).get("url")
                
                if img_url_to_display:
                    with cols[j]:
                        st.image(img_url_to_display, caption=image_item.get("name", "N/A"), width=150) # Fixed width
                        # You can add more details if needed:
                        # st.caption(f"Key: {image_item.get('key')}")
                else:
                    with cols[j]:
                        st.warning(f"No URL for {image_item.get('name')}")
else:
    st.info("没有找到图片，或者API返回数据为空。")

st.markdown("---")
st.subheader("原始API响应:")
st.json(st.session_state.api_response_data)

# The user's original print statements for debugging, can be removed or kept.
# print(f"Status Code: {request.status_code}") # This 'request' object is from user's old global scope
# print(f"Response Text: {request.text}")      # This one too.
# data_list = request.json()["data"]["data"] # This would fail if request object is not from the current fetch_images call.

