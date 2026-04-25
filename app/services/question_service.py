"""
面试问题生成服务模块
====================
本模块负责生成面试问题
使用阿里云百炼 API (qwen-turbo)
"""

import json
import logging
import os
import requests
import time

logger = logging.getLogger(__name__)


def get_default_questions():
    """
    获取默认的面试问题
    当大模型调用失败时使用此函数返回默认问题
    """
    default_q = {
        "question": "大模型调用失败",
        "score_standard": "大模型调用失败",
        "question_type": "voice"
    }
    return [default_q.copy() for _ in range(5)]


def build_prompt(candidate, position, latest_tech_info):
    """构建发送给大模型的 prompt"""
    if not latest_tech_info:
        latest_tech_info = "未提供简历分析信息"
    
    prompt = f"""你是一位专业的面试官，需要根据候选人的简历和应聘岗位生成针对性的面试问题。

候选人信息：
- 姓名：{candidate.get('name', '未提供')}
- 应聘职位：{position.get('name', '未提供')}

岗位要求：{position.get('requirements', '未提供')}
岗位职责：{position.get('responsibilities', '未提供')}

请特别关注以下简历分析结果，根据简历中的具体信息生成针对性的面试问题：
{latest_tech_info}

请根据以上信息生成5个高质量的面试问题，每个问题要包含评分标准。

请以JSON格式返回：
{{"questions": [{{"question": "问题内容", "score_standard": "评分标准", "question_type": "voice"}}]}}
"""
    return prompt


def call_llm_api(prompt, resume_image=None):
    """
    调用阿里云百炼大模型 API
    
    Args:
        prompt: 发送给大模型的提示文本
        resume_image: 简历截图（base64编码），可选
    
    Returns:
        dict: API 返回的 JSON 结果，失败时返回 None
    """
    # 从环境变量获取 API Key（同时支持 MINIMAX_API_KEY 和 DASHSCOPE_API_KEY）
    api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('MINIMAX_API_KEY')
    
    if not api_key:
        logger.warning("[Question] 未配置 API Key")
        return None
    
    # 阿里云百炼 API 地址（OpenAI 兼容模式）
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建消息内容
    content = [{"type": "text", "text": prompt}]
    
    # API 请求参数 - 使用 qwen-turbo（免费额度）
    data = {
        "model": "qwen-turbo",
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    try:
        logger.info("[Question] 发送请求到阿里云百炼...")
        response = requests.post(url, headers=headers, json=data, timeout=120)
        
        if response.status_code != 200:
            logger.error(f"[Question] API错误: {response.status_code} - {response.text}")
            return None
        
        response_json = response.json()
        
        if 'choices' not in response_json:
            logger.error("[Question] 响应缺少choices字段")
            return None
        
        message = response_json['choices'][0]['message']
        if 'content' not in message:
            logger.error("[Question] 响应缺少content字段")
            return None
        
        logger.info("[Question] 收到有效响应")
        return response_json
        
    except requests.exceptions.Timeout:
        logger.error("[Question] API调用超时")
        return None
    except Exception as e:
        logger.error(f"[Question] API调用异常: {e}")
        return None


def generate_questions(interview_id, candidate, position, interview, latest_tech_info, cursor, conn, resume_image=None):
    """
    生成面试问题的主函数
    """
    logger.info("[Question] 开始生成面试问题")
    
    try:
        # 1. 构建 prompt 并调用大模型
        prompt = build_prompt(candidate, position, latest_tech_info)
        
        logger.info("[Question] 调用大模型API...")
        result = call_llm_api(prompt, resume_image)
        
        if result is None:
            logger.warning("[Question] 大模型调用失败，使用默认问题")
            return {
                "status": "fallback",
                "message": "大模型调用失败，使用默认问题",
                "questions": get_default_questions()
            }
        
        # 2. 解析响应
        content = result['choices'][0]['message']['content']
        logger.info(f"[Question] 收到响应，长度: {len(content)}")
        
        # 3. 提取并解析 JSON
        try:
            json_match = None
            # 尝试多种方式提取 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                if 'questions' in parsed:
                    questions = parsed['questions']
                else:
                    questions = [parsed] if isinstance(parsed, dict) else []
            else:
                logger.warning("[Question] 无法提取JSON")
                questions = []
                
        except Exception as e:
            logger.error(f"[Question] 解析JSON失败: {e}")
            questions = []
        
        # 4. 如果没有有效问题，使用默认
        if not questions or len(questions) == 0:
            logger.warning("[Question] 无有效问题，使用默认")
            questions = get_default_questions()
        
        # 5. 保存问题到数据库
        saved_count = 0
        for q in questions[:5]:  # 最多保存5个
            try:
                cursor.execute('''
                    INSERT INTO interview_questions 
                    (interview_id, question, question_type, score_standard, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    interview_id,
                    q.get('question', '未知问题'),
                    q.get('question_type', 'voice'),
                    q.get('score_standard', ''),
                    int(time.time())
                ))
                saved_count += 1
            except Exception as e:
                logger.error(f"[Question] 保存问题失败: {e}")
        
        conn.commit()
        logger.info(f"[Question] 完成，保存{saved_count}个问题")
        
        return {
            "status": "success",
            "message": f"成功生成{saved_count}个面试问题",
            "questions": questions[:5]
        }
        
    except Exception as e:
        logger.error(f"[Question] 生成问题异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "questions": get_default_questions()
        }