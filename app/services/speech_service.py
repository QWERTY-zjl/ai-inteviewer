"""
语音服务模块
============
负责语音识别（ASR）和语音合成（TTS）功能
基于阿里云 DashScope API
"""

import base64
import logging
import requests
import time
from app.config.config import DASHSCOPE_API_KEY

logger = logging.getLogger(__name__)

# 音色映射表：前端音色类型 → 阿里云音色ID
VOICE_MAP = {
    "professional_male": "Ethan",     # 专业男声
    "professional_female": "Serena",   # 专业女声
    "energetic_male": "Ethan",         # 活力男声
    "gentle_female": "Cherry"          # 温柔女声
}

def transcribe_audio(audio_data, format="wav"):
    """
    使用阿里云 qwen3-asr-flash 模型进行语音识别
    
    Args:
        audio_data: 音频二进制数据
        format: 音频格式，支持 wav/mp3/pcm 等
    
    Returns:
        tuple: (识别文本, 错误信息)，成功时错误信息为 None
    """
    try:
        api_key = DASHSCOPE_API_KEY
        if not api_key:
            return None, "未配置 API Key"
        
        # 将音频转换为 base64 编码
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # 调用阿里云 ASR API (qwen3-asr-flash)
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "qwen3-asr-flash",
                "input": {
                    "audio": audio_base64,
                    "prompt": "请识别这段音频的内容"
                },
                "parameters": {
                    "use_raw_prompt": True
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            # qwen3-asr-flash 返回格式：output.audio.text
            text = result.get("output", {}).get("audio", {}).get("text", "")
            if text:
                logger.info(f"[ASR] 识别成功: {text}")
                return text, None
            return None, "未识别到文字"
        
        error_msg = response.text[:200] if response.text else "Unknown error"
        logger.error(f"[ASR] API调用失败: {response.status_code} - {error_msg}")
        return None, f"语音识别失败: {response.status_code} - {error_msg}"
    except Exception as e:
        logger.error(f"[ASR] 错误: {e}")
        return None, str(e)


def synthesize_speech(text, voice_type="professional_male"):
    """
    使用阿里云 Qwen-TTS 进行语音合成
    
    Args:
        text: 要合成的文本
        voice_type: 音色类型，默认 professional_male
    
    Returns:
        tuple: (音频二进制数据, 错误信息)，成功时错误信息为 None
    """
    try:
        api_key = DASHSCOPE_API_KEY
        if not api_key:
            return None, "未配置 API Key"
        
        # 映射音色类型
        voice = VOICE_MAP.get(voice_type, "Ethan")
        
        # 调用阿里云 TTS API (官方文档格式)
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "qwen3-tts-flash",
                "input": {
                    "text": text
                },
                "parameters": {
                    "voice": voice,
                    "language_type": "Chinese"
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            # 从响应中获取音频URL
            audio_url = result.get("output", {}).get("audio", {}).get("url", "")
            
            if not audio_url:
                return None, "未获取到音频URL"
            
            # 从URL下载音频
            audio_response = requests.get(audio_url, timeout=60)
            if audio_response.status_code == 200:
                logger.info(f"[TTS] 成功合成音频，大小: {len(audio_response.content)} bytes")
                return audio_response.content, None
            else:
                return None, f"下载音频失败: {audio_response.status_code}"
        else:
            error_msg = response.text[:200] if response.text else "Unknown error"
            logger.error(f"[TTS] API调用失败: {response.status_code} - {error_msg}")
            return None, f"语音合成失败: {response.status_code} - {error_msg}"
    except Exception as e:
        logger.error(f"[TTS] 错误: {e}")
        return None, str(e)
