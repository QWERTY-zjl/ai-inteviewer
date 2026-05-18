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
        
        logger.info(f"[ASR] 音频数据大小: {len(audio_data)} bytes, 格式: {format}")
        
        # 调用阿里云 ASR API (qwen3-asr-flash)
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "qwen3-asr-flash",
                "input": {
                    "audio": audio_base64,
                    "prompt": "请识别这段音频的内容，直接输出识别到的文字，不要做其他任何操作。"
                },
                "parameters": {
                    "use_raw_prompt": True
                }
            },
            timeout=60
        )
        
        logger.info(f"[ASR] API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"[ASR] 响应内容: {result}")
            
            # qwen3-asr-flash 返回格式：output.choices[0].message.content[0].text
            try:
                text = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", [{}])[0].get("text", "")
            except (IndexError, KeyError):
                text = None
            
            if text and text.strip():
                # 过滤掉无效的重复响应或错误提示
                filtered_text = text.strip()
                if "请提供音频" in filtered_text or "不要做任何" in filtered_text or len(filtered_text) < 5:
                    logger.warning(f"[ASR] 检测到无效响应: {filtered_text[:50]}...")
                    return None, "语音识别未返回有效文字 (模型无法识别该音频格式)"
                    
                logger.info(f"[ASR] 识别成功: {filtered_text}")
                return filtered_text, None
            return None, "未识别到文字"
        
        error_msg = response.text[:200] if response.text else "Unknown error"
        logger.error(f"[ASR] API调用失败: {response.status_code} - {error_msg}")
        return None, f"语音识别失败: {response.status_code} - {error_msg}"
    except Exception as e:
        logger.error(f"[ASR] 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/speech/synthesis",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "qwen-tts-flash",
                "input": {
                    "text": text
                },
                "parameters": {
                    "voice": voice,
                    "response_format": "mp3",
                    "sample_rate": 16000
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"[TTS] 合成成功，音频大小: {len(response.content)} bytes")
            return response.content, None
        
        error_msg = response.text[:200] if response.text else "Unknown error"
        logger.error(f"[TTS] API调用失败: {response.status_code} - {error_msg}")
        return None, f"语音合成失败: {response.status_code} - {error_msg}"
    except Exception as e:
        logger.error(f"[TTS] 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, str(e)