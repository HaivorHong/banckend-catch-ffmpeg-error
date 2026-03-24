import subprocess
import os
import logging
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FFmpeg Video Parser", description="Single process call ffmpeg to parse video, record logs when errors occur")

# Configure logs (only for the framework's own logs)
logging.basicConfig(level=logging.INFO)


class VideoRequest(BaseModel):
    video_url: str  # supply loacl / url addr


def extract_video_name(url: str) -> str:
    """从 URL/路径中提取文件名（不含扩展名）"""
    parsed = urlparse(url)
    # 如果 path 为空，尝试直接使用原始字符串（可能是本地路径）
    path = parsed.path if parsed.path else url
    base = os.path.basename(path)
    # 去掉扩展名
    name, _ = os.path.splitext(base)
    return name if name else "unknown"


def run_ffmpeg(video_url: str, timeout: int = 30):
    """
    执行 ffmpeg -i 命令，返回 (returncode, stdout, stderr)
    如果 timeout 秒内未完成，抛出 subprocess.TimeoutExpired
    """
    cmd = ["ffmpeg", "-i", video_url]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace"  # 避免编码问题导致异常
    )
    return result.returncode, result.stdout, result.stderr


def write_error_log(video_name: str, error_output: str) -> str:
    """将错误输出写入本地文件，返回日志文件路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{video_name}_{timestamp}.log"
    # 可以修改为指定目录，例如 logs/，这里直接放在当前目录
    log_path = Path.cwd() / log_filename
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"视频源: {video_name}\n")
        f.write(f"时间: {datetime.now().isoformat()}\n")
        f.write("错误详情:\n")
        f.write(error_output)
    return str(log_path)


@app.post("/parse_video")
async def parse_video(request: VideoRequest):
    """
    解析视频接口
    - 传入 video_url（本地路径或网络地址）
    - 调用 ffmpeg -i 获取信息
    - 若 ffmpeg 执行失败（非0返回码），将错误信息写入本地日志文件，并返回错误详情
    - 若成功，返回解析信息（ffmpeg 输出的元数据）
    """
    video_url = request.video_url
    video_name = extract_video_name(video_url)

    try:
        returncode, stdout, stderr = run_ffmpeg(video_url)
    except subprocess.TimeoutExpired:
        # 超时也视为错误
        error_msg = f"ffmpeg 执行超时（超过30秒）: {video_url}"
        log_path = write_error_log(video_name, error_msg)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ffmpeg 超时",
                "message": error_msg,
                "log_file": log_path
            }
        )
    except FileNotFoundError:
        # ffmpeg 未安装或不在 PATH 中
        error_msg = "ffmpeg 未找到，请确保已安装并加入系统 PATH"
        log_path = write_error_log(video_name, error_msg)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ffmpeg not found",
                "message": error_msg,
                "log_file": log_path
            }
        )
    except Exception as e:
        # 其他未知异常
        error_msg = f"未知错误: {str(e)}"
        log_path = write_error_log(video_name, error_msg)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal error",
                "message": error_msg,
                "log_file": log_path
            }
        )

    if returncode != 0:
        # ffmpeg 返回非0，说明有错误
        log_path = write_error_log(video_name, stderr)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ffmpeg 解析失败",
                "message": stderr.strip(),
                "log_file": log_path
            }
        )

    # 成功：ffmpeg 输出信息通常在 stderr 中
    return {
        "status": "success",
        "video_url": video_url,
        "video_name": video_name,
        "info": stderr.strip()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
