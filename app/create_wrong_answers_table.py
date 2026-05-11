"""
错题本数据库初始化脚本
======================
创建 wrong_answers 表，用于存储用户的错题记录
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

def upgrade_wrong_answers_table():
    """
    为 interview_system.db 添加错题本相关表和字段
    
    表结构：
    - wrong_answers: 错题记录表
    
    字段修改：
    - interview_questions.is_wrong: 标记是否为错题
    """
    DATABASE_NAME = 'interview_system.db'
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. 创建 wrong_answers 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wrong_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER,
            question_text TEXT NOT NULL,
            user_answer TEXT,
            correct_answer TEXT,
            score REAL,
            is_favorited INTEGER DEFAULT 1,
            retry_count INTEGER DEFAULT 0,
            best_score REAL,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            last_retry_at INTEGER
        )
        ''')
        logger.info("[DB] wrong_answers 表创建成功")
        
        # 2. 在 interview_questions 表添加 is_wrong 字段
        try:
            cursor.execute('''
            ALTER TABLE interview_questions ADD COLUMN is_wrong INTEGER DEFAULT 0
            ''')
            logger.info("[DB] interview_questions.is_wrong 字段添加成功")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e).lower():
                logger.info("[DB] interview_questions.is_wrong 字段已存在，跳过")
            else:
                raise
        
        conn.commit()
        logger.info("[DB] 错题本数据库更新完成")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB] 错题本数据库更新失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    upgrade_wrong_answers_table()