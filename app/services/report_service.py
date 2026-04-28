"""
面试报告生成服务模块
====================
本模块负责生成面试报告
基于阿里云 DashScope qwen-plus 模型
"""

import time
import json
import logging
import requests
from app.config.config import DASHSCOPE_API_KEY

logger = logging.getLogger(__name__)


def generate_interview_report(interview_id, interview, candidate, position, questions, expression_summary, cursor, conn):
    """
    生成面试报告
    
    参数:
        interview_id: 面试ID
        interview: 面试信息
        candidate: 候选人信息
        position: 职位信息
        questions: 面试问题列表
        expression_summary: 表情分析摘要
        cursor: 数据库游标
        conn: 数据库连接
    
    返回:
        JSON响应
    """
    logger.info(f"[Report] 开始为面试 {interview_id} 生成报告")
    
    # 检查是否有简历
    has_resume = False
    if candidate.get('resume_content'):
        has_resume = True
        logger.info(f"[Report] 候选人 {candidate['name']} 有简历")
    else:
        logger.info(f"[Report] 候选人 {candidate['name']} 无简历")
    
    prompt = f"""你是一位专业的面试评估专家，需要对候选人"{candidate['name']}"应聘"{position['name']}"职位的面试表现进行评估。
面试官是{interview['interviewer']}。

请根据以下面试问题和候选人的回答，对每个问题进行评分和点评，并给出综合评价。
注意每个问题评分范围是0-100分，综合评分范围是0-100分。

"""
    
    # 添加简历信息
    if has_resume:
        prompt += f"""
【候选人简历】
- 候选人姓名: {candidate['name']}
- 应聘职位: {position['name']}
- 简历状态: 已提供

请在评估时参考候选人的简历背景，结合面试表现给出更全面的评价。

"""
    
    for i, q in enumerate(questions, 1):
        prompt += f"""问题{i}: {q.get('question', '未提供问题')}
评分标准: {q.get('score_standard', '未提供评分标准')}
候选人回答: {q.get('answer_text', '未提供回答')}

"""
    
    if expression_summary:
        prompt += f"""
【表情与情绪分析数据】
- 总记录数: {expression_summary['total_records']}次
- 平均情绪评分: {expression_summary['avg_emotion_score']}分
- 平均表情质量评分: {expression_summary['avg_quality_score']}分
- 平均综合评分: {expression_summary['avg_final_score']}分
- 积极情绪次数: {expression_summary['positive_count']}次
- 中性情绪次数: {expression_summary['neutral_count']}次
- 消极情绪次数: {expression_summary['negative_count']}次
- 表情分布: {expression_summary['expression_distribution']}

请将表情与情绪分析数据纳入综合评估，作为"情绪管理能力"的评分依据。

"""
    
    prompt += """请以JSON格式返回评估结果，包含以下内容：
1. 每个问题的评分和评价
2. 技术能力总分(满分100)
3. 沟通能力总分(满分100)
4. 情绪管理能力总分(满分100，基于表情与情绪分析数据)
5. 综合评分(满分100，综合以上各项)
6. 面试官评语(综合评价候选人的优缺点)
7. 录用建议(推荐录用/可以考虑/不建议录用)

JSON格式示例:
{
    "question_evaluations": [
        {"id": 1, "question": "[question]", "score_standard": "[score_standard]", "answer": "[answer_text]", "score": 85, "comments": "回答详细..."}
    ],
    "technical_score": 88,
    "communication_score": 90,
    "emotion_score": 75,
    "overall_score": 85,
    "comments": "候选人技术基础扎实...",
    "recommendation": "推荐录用"
}"""
    
    # 调用阿里云百炼 API
    api_key = DASHSCOPE_API_KEY
    if not api_key:
        logger.error("[Report] 未配置 DASHSCOPE_API_KEY")
        return {"error": "未配置 API 密钥"}
    
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen-plus",
        "input": {
            "messages": [
                {"role": "system", "content": "你是一位专业的面试评估专家，负责评估技术面试表现。请返回JSON格式。"},
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "result_format": "message"
        }
    }
    
    logger.info("[Report] 正在调用阿里云百炼 API...")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        # 解析返回结果
        if 'output' in result and 'choices' in result['output']:
            choices = result['output']['choices']
            if choices and 'message' in choices[0]:
                result_text = choices[0]['message']['content']
            else:
                raise Exception("响应格式错误：缺少 message")
        elif 'choices' in result:
            result_text = result['choices'][0]['message']['content']
        else:
            logger.error(f"[Report] 响应格式未知: {result}")
            raise Exception("响应格式错误")
        
        logger.info(f"[Report] API 调用成功，响应长度: {len(result_text)}")
        
    except Exception as e:
        logger.error(f"[Report] 调用大模型失败: {e}")
        return {"error": f"调用大模型失败: {str(e)}"}
    
    # 处理 < Lang_200think> 标签
    if '< Lang_200think>' in result_text:
        result_text = result_text.split('< Lang_200think>')[-1].strip()
        logger.info("[Report] 已移除思考标签")
    
    # 解析 JSON
    try:
        # 处理 Markdown 代码块
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()
        
        evaluation_result = json.loads(result_text)
        logger.info("[Report] JSON 解析成功")
        
    except json.JSONDecodeError as e:
        logger.error(f"[Report] 解析大模型响应失败: {e}")
        # 尝试提取 JSON 部分
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                evaluation_result = json.loads(json_match.group())
                logger.info("[Report] 使用正则提取 JSON 成功")
            except:
                return {"error": "解析响应失败"}
        else:
            return {"error": "解析响应失败"}
    
    # 构建报告数据
    report_data = {
        "interview_id": interview_id,
        "candidate_name": candidate['name'],
        "position_name": position['name'],
        "interviewer": interview['interviewer'],
        "evaluation": evaluation_result,
        "generated_at": int(time.time())
    }
    
    # 保存报告到数据库
    cursor.execute('''
        UPDATE interviews SET status = 4, report_content = ? WHERE id = ?
    ''', (json.dumps(report_data), interview_id))
    
    conn.commit()
    
    logger.info(f"[Report] 报告已保存到数据库，面试ID: {interview_id}")
    
    return report_data