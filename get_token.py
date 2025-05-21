import os
import requests
from dotenv import load_dotenv, set_key

# 加载 .env 文件
ENV_FILE = "/app/backend/.env"  # 修改为你需要的 .env 文件路径
load_dotenv(ENV_FILE)

# 配置 API 请求信息
API_BASE_URL = "http://lskypro:8000/api/v1/"  # 替换为你的 API 基础地址
TOKEN_API_ENDPOINT = "tokens"  # Token 请求的 API 路径
EMAIL = "halfpeopl1e@outlook.com"  # 替换为你的邮箱
PASSWORD = "yfz200504"  # 替换为你的密码

def request_token(api_url: str, email: str, password: str) -> str:
    """
    请求 API 获取 token
    """
    payload = {
        "email": email,
        "password": password
    }
    headers = {
        "Accept": "application/json",
    }
    try:
        response = requests.post(api_url, data=payload, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        token_response_json = response.json()
        if response.status_code == 200 and token_response_json.get("status"):
            token = token_response_json.get("data", {}).get("token")
            if not token:
                raise ValueError("未从响应中获取到 token")
            return token
        else:
            raise ValueError(f"Token 请求失败: {token_response_json.get('message', '未知错误')}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"请求 token 时发生网络错误: {e}")
    except ValueError as e:
        raise RuntimeError(f"请求 token 时发生数据解析错误: {e}")

def update_env_token(token: str):
    """
    更新 .env 文件中的 LKPRO_TOKEN
    """
    try:
        # 确保 token 不带引号
        set_key(ENV_FILE, "LKPRO_TOKEN", token.strip("'\""))  # 去掉可能的引号
        print(f"成功更新 .env 文件中的 LKPRO_TOKEN: {token}")
    except Exception as e:
        raise RuntimeError(f"更新 .env 文件时发生错误: {e}")

if __name__ == "__main__":
    try:
        print("正在请求 token...")
        token = request_token(f"{API_BASE_URL}{TOKEN_API_ENDPOINT}", EMAIL, PASSWORD)
        print(f"成功获取 token: {token}")
        
        print("正在更新 .env 文件...")
        update_env_token(token)
    except Exception as e:
        print(f"脚本运行失败: {e}")
