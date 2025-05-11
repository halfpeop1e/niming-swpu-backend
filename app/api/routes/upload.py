import uuid
import httpx
import os
import hashlib

from fastapi import APIRouter, Depends,HTTPException,Request, Query, File, UploadFile, Form, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from pydantic import BaseModel, Field, HttpUrl
from loguru import logger
from typing import Optional, Any, List
from app import crud
from app.api.deps import AsyncSessionDep, CurrentUser, SessionDep, RedisClient
from app.models import Message, ImageUploadResponse, ImageData, ImageDataLinks

router = APIRouter(prefix="/upload", tags=["upload"])

# 假设这些是常量或从配置中读取
IMAGE_HOST_URL = "http://127.0.0.1:8000/api/v1/upload"
IMAGE_HOST_TOKEN = "3|Q07kKqG6GqDNUO6W2rPi94HuQTuckvnkEFM5rFdP" # 例如 "3|Q07kKqG6GqDNUO6W2rPi94HuQTuckvnkEFM5rFdP"

# Define a response model in this file for returning multiple image details
# This is similar to what was discussed for getCard.py but now in upload.py
class MultipleImagesUploadResponse(BaseModel):
    status: bool
    message: str
    data: Optional[List[ImageData]] = None

# Define new, simpler response models locally in this file for the specific client requirement
class ImagePathInfo(BaseModel):
    original_filename: Optional[str] = None # To help client map response to original file
    relativePath: str # The part of the URL after "/i/"

class MultipleImagePathsResponse(BaseModel): # Renamed for clarity
    status: bool
    message: str
    data: Optional[List[ImagePathInfo]] = None

# 处理上传图片的接口
@router.post("/upload-images", response_model=MultipleImagePathsResponse)
async def upload_image_to_host(
    current_user: CurrentUser,
    redis: RedisClient,
    imageFiles: List[UploadFile] = File(...)
):
    # 上传接口说明
    # *file	File	需要上传的图片文件
    # strategy_id	Integer	储存策略ID 可为空，不携带则使用默认策略
    # *Content-Type	String	需要设置为 multipart/form-data
    # token = 3|Q07kKqG6GqDNUO6W2rPi94HuQTuckvnkEFM5rFdP
    # api: http://127.0.0.1:8000/api/v1/upload
    # Authorization	String	授权 Token，例如：Bearer 1|1bJbwlqBfnggmOMEZqXT5XusaIwqiZjCDs7r1Ob5
    # *Accept	String	必须设置为 application/json
    logger.info(f"User '{current_user.id}' (email: '{current_user.email}') initiated an upload of {len(imageFiles)} file(s).")

    if not imageFiles:
        logger.warning(f"User '{current_user.id}' submitted an upload request, but no files were found in 'imageFiles'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供图片文件。"
        )

    processed_file_paths: List[ImagePathInfo] = [] # Changed to store ImagePathInfo
    files_successfully_hosted_count = 0

    async with httpx.AsyncClient() as client:
        for index, single_file in enumerate(imageFiles):
            original_filename_for_response = single_file.filename # Store for response
            try:
                contents = await single_file.read()
                await single_file.seek(0)

                logger.info(
                    f"Processing file #{index + 1} for user '{current_user.id}': "
                    f"Filename: '{single_file.filename}', Content-Type: '{single_file.content_type}'"
                )

                files_for_host = {"file": (single_file.filename, contents, single_file.content_type)}
                headers_for_host = {
                    "Authorization": f"Bearer {IMAGE_HOST_TOKEN}",
                    "Accept": "application/json"
                }

                logger.info(f"Sending '{single_file.filename}' to image host: {IMAGE_HOST_URL}")
                
                response_from_host = await client.post(
                    IMAGE_HOST_URL,
                    files=files_for_host,
                    headers=headers_for_host
                )
                response_from_host.raise_for_status()
                host_response_json = response_from_host.json()
                logger.info(f"Response from image host for '{single_file.filename}': {host_response_json}")

                if host_response_json.get("status") is True and isinstance(host_response_json.get("data"), dict):
                    img_data_from_host = host_response_json["data"]
                    links_from_host = img_data_from_host.get("links", {})
                    full_url = links_from_host.get("url")

                    if full_url:
                        # Extract the part after "/i/"
                        url_parts = full_url.split("/i/", 1)
                        relative_path = url_parts[1] if len(url_parts) > 1 else ""
                        
                        if relative_path:
                            processed_file_paths.append(ImagePathInfo(
                                original_filename=original_filename_for_response,
                                relativePath=relative_path
                            ))
                            files_successfully_hosted_count += 1
                            logger.info(f"Successfully extracted relative path '{relative_path}' for '{original_filename_for_response}'.")
                        else:
                            logger.error(f"Could not extract relative path from URL '{full_url}' for '{original_filename_for_response}' (missing '/i/' or path after it)." )
                    else:
                        logger.error(f"No 'url' found in links from image host response for '{original_filename_for_response}'.")
                else:
                    logger.error(f"Image host returned non-success status or malformed data for '{original_filename_for_response}'. Message: {host_response_json.get('message', 'N/A')}")

                await single_file.close()

            except httpx.HTTPStatusError as e_http:
                logger.exception(f"HTTP error occurred when uploading '{original_filename_for_response}' to image host: {e_http.response.status_code} - {e_http.response.text}")
            except Exception as e_general:
                logger.exception(f"General error processing file '{original_filename_for_response}' for image host upload: {e_general}")
    
    if files_successfully_hosted_count == 0 and imageFiles:
        logger.warning(f"User '{current_user.id}' - No files were successfully processed to extract URL paths out of {len(imageFiles)} attempts.")
        return MultipleImagePathsResponse(
            status=False, 
            message="所有图片均未能成功处理以提取URL路径。请检查日志。", 
            data=[]
        )
    
    success_message = f"成功处理了{files_successfully_hosted_count} 张图片。"
    if files_successfully_hosted_count < len(imageFiles):
        success_message += f" {len(imageFiles) - files_successfully_hosted_count} 张图片处理失败或未能提取URL路径。"
    
    logger.info(f"User '{current_user.id}' - Finished image URL path extraction process: {success_message}")
    return MultipleImagePathsResponse(
        status=True,
        message=success_message,
        data=processed_file_paths
    )