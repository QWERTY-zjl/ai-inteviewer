"""
错题本管理API模块
"""

import logging
import time
from fastapi import Path, Query, Body, HTTPException
from fastapi.responses import JSONResponse

from app.db.db import get_db, return_db

logger = logging.getLogger(__name__)


async def add_wrong_answer(
    user_id: int = Body(...),
    session_id: int = Body(...),
    question_text: str = Body(...),
    user_answer: str = Body(...),
    correct_answer: str = Body(None),
    score: float = Body(...)
):
    """
    添加错题记录
    
    参数:
        user_id: 用户ID
        session_id: 面试会话ID
        question_text: 问题文本
        user_answer: 用户答案
        correct_answer: 正确答案（可选）
        score: 得分
    
    返回:
        添加结果
    """
    try:
        conn = get_db()
        
        # 插入错题记录
        cursor = conn.execute('''
            INSERT INTO wrong_answers 
            (user_id, session_id, question_text, user_answer, correct_answer, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, session_id, question_text, user_answer, correct_answer, score, int(time.time())))
        
        conn.commit()
        
        return_db(conn)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "id": cursor.lastrowid,
                "message": "错题已添加"
            }
        )
    except Exception as e:
        logger.error(f"[ERROR] add_wrong_answer: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def get_wrong_answers(user_id: int = Query(...)):
    """
    获取用户的错题列表
    
    参数:
        user_id: 用户ID
    
    返回:
        错题列表
    """
    try:
        conn = get_db()
        
        # 获取错题列表
        wrong_answers = conn.execute('''
            SELECT id, question_text, user_answer, correct_answer, score, 
                   is_favorited, retry_count, best_score, created_at
            FROM wrong_answers
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,)).fetchall()
        
        return_db(conn)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "count": len(wrong_answers),
                "data": [dict(item) for item in wrong_answers]
            }
        )
    except Exception as e:
        logger.error(f"[ERROR] get_wrong_answers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def get_wrong_answer_count(user_id: int = Query(...)):
    """
    获取用户的错题数量（用于首页显示）
    
    参数:
        user_id: 用户ID
    
    返回:
        错题数量
    """
    try:
        conn = get_db()
        
        count = conn.execute('''
            SELECT COUNT(*) as count FROM wrong_answers WHERE user_id = ?
        ''', (user_id,)).fetchone()
        
        return_db(conn)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "count": count['count'] if count else 0
            }
        )
    except Exception as e:
        logger.error(f"[ERROR] get_wrong_answer_count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def retry_wrong_answer(
    user_id: int = Body(...),
    wrong_id: int = Body(...)
):
    """
    重做错题
    
    参数:
        user_id: 用户ID
        wrong_id: 错题记录ID
    
    返回:
        错题题目信息
    """
    try:
        conn = get_db()
        
        # 获取错题记录
        wrong = conn.execute('''
            SELECT id, question_text, correct_answer
            FROM wrong_answers
            WHERE id = ? AND user_id = ?
        ''', (wrong_id, user_id)).fetchone()
        
        if not wrong:
            return_db(conn)
            raise HTTPException(status_code=404, detail="错题不存在")
        
        # 更新重试次数
        conn.execute('''
            UPDATE wrong_answers
            SET retry_count = retry_count + 1, last_retry_at = ?
            WHERE id = ?
        ''', (int(time.time()), wrong_id))
        
        conn.commit()
        return_db(conn)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "id": wrong['id'],
                "question_text": wrong['question_text'],
                "correct_answer": wrong['correct_answer']
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] retry_wrong_answer: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def submit_retry_answer(
    user_id: int = Body(...),
    wrong_id: int = Body(...),
    new_answer: str = Body(...),
    score: float = Body(...)
):
    """
    提交重做答案
    
    参数:
        user_id: 用户ID
        wrong_id: 错题记录ID
        new_answer: 新答案
        score: 新得分
    
    返回:
        提交结果
    """
    try:
        conn = get_db()
        
        # 获取当前最佳分数
        current = conn.execute('''
            SELECT best_score FROM wrong_answers WHERE id = ? AND user_id = ?
        ''', (wrong_id, user_id)).fetchone()
        
        # 更新记录
        best_score = current['best_score'] if current else 0
        new_best = max(best_score, score)
        
        conn.execute('''
            UPDATE wrong_answers
            SET user_answer = ?, score = ?, best_score = ?
            WHERE id = ? AND user_id = ?
        ''', (new_answer, score, new_best, wrong_id, user_id))
        
        conn.commit()
        return_db(conn)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "score": score,
                "best_score": new_best,
                "passed": score >= 60
            }
        )
    except Exception as e:
        logger.error(f"[ERROR] submit_retry_answer: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_wrong_answer(
    user_id: int = Query(...),
    wrong_id: int = Path(...)
):
    """
    删除错题记录
    
    参数:
        user_id: 用户ID
        wrong_id: 错题记录ID
    
    返回:
        删除结果
    """
    try:
        conn = get_db()
        
        # 删除错题（只能删除自己的）
        result = conn.execute('''
            DELETE FROM wrong_answers WHERE id = ? AND user_id = ?
        ''', (wrong_id, user_id))
        
        conn.commit()
        return_db(conn)
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="错题不存在")
        
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "错题已删除"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] delete_wrong_answer: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def toggle_favorite(
    user_id: int = Body(...),
    wrong_id: int = Body(...),
    is_favorited: bool = Body(...)
):
    """
    切换错题收藏状态
    
    参数:
        user_id: 用户ID
        wrong_id: 错题记录ID
        is_favorited: 是否收藏
    
    返回:
        操作结果
    """
    try:
        conn = get_db()
        
        conn.execute('''
            UPDATE wrong_answers
            SET is_favorited = ?
            WHERE id = ? AND user_id = ?
        ''', (1 if is_favorited else 0, wrong_id, user_id))
        
        conn.commit()
        return_db(conn)
        
        return JSONResponse(
            status_code=200,
            content={"status": "success", "is_favorited": is_favorited}
        )
    except Exception as e:
        logger.error(f"[ERROR] toggle_favorite: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))