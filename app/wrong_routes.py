"""
错题本管理API - Flask版本
"""

def register_wrong_routes(app, get_db, return_db, logger):
    """注册错题本相关路由"""
    
    def add_wrong_answer():
        """添加错题记录"""
        from flask import jsonify, request
        import time
        try:
            data = request.json
            user_id = data.get('user_id')
            session_id = data.get('session_id')
            question_text = data.get('question_text')
            user_answer = data.get('user_answer', '')
            correct_answer = data.get('correct_answer', '')
            score = data.get('score', 0)
            
            if not all([user_id, question_text]):
                return jsonify({"status": "error", "message": "参数不完整"}), 400
            
            conn = get_db()
            cursor = conn.execute('''
                INSERT INTO wrong_answers 
                (user_id, session_id, question_text, user_answer, correct_answer, score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, session_id, question_text, user_answer, correct_answer, score, int(time.time())))
            
            conn.commit()
            return_db(conn)
            
            return jsonify({"status": "success", "id": cursor.lastrowid, "message": "错题已添加"})
        except Exception as e:
            logger.error(f"[ERROR] add_wrong_answer: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

    def get_wrong_answers():
        """获取用户的错题列表"""
        from flask import jsonify, request
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({"status": "error", "message": "缺少user_id"}), 400
            
            conn = get_db()
            wrong_answers = conn.execute('''
                SELECT id, question_text, user_answer, correct_answer, score, 
                       is_favorited, retry_count, best_score, created_at
                FROM wrong_answers
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,)).fetchall()
            
            return_db(conn)
            
            return jsonify({
                "status": "success",
                "count": len(wrong_answers),
                "data": [dict(item) for item in wrong_answers]
            })
        except Exception as e:
            logger.error(f"[ERROR] get_wrong_answers: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

    def get_wrong_answer_count():
        """获取用户的错题数量"""
        from flask import jsonify, request
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({"status": "error", "message": "缺少user_id"}), 400
            
            conn = get_db()
            count = conn.execute('''
                SELECT COUNT(*) as count FROM wrong_answers WHERE user_id = ?
            ''', (user_id,)).fetchone()
            
            return_db(conn)
            
            return jsonify({"status": "success", "count": count['count'] if count else 0})
        except Exception as e:
            logger.error(f"[ERROR] get_wrong_answer_count: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def retry_wrong_answer():
        """获取错题详情用于重做"""
        from flask import jsonify, request
        import time
        try:
            data = request.json
            user_id = data.get('user_id')
            wrong_id = data.get('wrong_id')
            
            conn = get_db()
            wrong = conn.execute('''
                SELECT id, question_text, correct_answer
                FROM wrong_answers
                WHERE id = ? AND user_id = ?
            ''', (wrong_id, user_id)).fetchone()
            
            if not wrong:
                return_db(conn)
                return jsonify({"status": "error", "message": "错题不存在"}), 404
            
            conn.execute('''
                UPDATE wrong_answers
                SET retry_count = retry_count + 1, last_retry_at = ?
                WHERE id = ?
            ''', (int(time.time()), wrong_id))
            
            conn.commit()
            return_db(conn)
            
            return jsonify({
                "status": "success",
                "id": wrong['id'],
                "question_text": wrong['question_text'],
                "correct_answer": wrong['correct_answer']
            })
        except Exception as e:
            logger.error(f"[ERROR] retry_wrong_answer: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

    def submit_retry_answer():
        """提交重做答案"""
        from flask import jsonify, request
        try:
            data = request.json
            user_id = data.get('user_id')
            wrong_id = data.get('wrong_id')
            new_answer = data.get('new_answer', '')
            score = data.get('score', 0)
            
            conn = get_db()
            current = conn.execute('''
                SELECT best_score FROM wrong_answers WHERE id = ? AND user_id = ?
            ''', (wrong_id, user_id)).fetchone()
            
            best_score = current['best_score'] if current else 0
            new_best = max(best_score, score)
            
            conn.execute('''
                UPDATE wrong_answers
                SET user_answer = ?, score = ?, best_score = ?
                WHERE id = ? AND user_id = ?
            ''', (new_answer, score, new_best, wrong_id, user_id))
            
            conn.commit()
            return_db(conn)
            
            return jsonify({
                "status": "success",
                "score": score,
                "best_score": new_best,
                "passed": score >= 60
            })
        except Exception as e:
            logger.error(f"[ERROR] submit_retry_answer: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

    def delete_wrong_answer(wrong_id):
        """删除错题记录"""
        from flask import jsonify, request
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({"status": "error", "message": "缺少user_id"}), 400
            
            conn = get_db()
            result = conn.execute('''
                DELETE FROM wrong_answers WHERE id = ? AND user_id = ?
            ''', (wrong_id, user_id))
            
            conn.commit()
            return_db(conn)
            
            if result.rowcount == 0:
                return jsonify({"status": "error", "message": "错题不存在"}), 404
            
            return jsonify({"status": "success", "message": "错题已删除"})
        except Exception as e:
            logger.error(f"[ERROR] delete_wrong_answer: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500
    
    # 注册路由
    app.add_url_rule('/api/wrong/add', 'add_wrong_answer', add_wrong_answer, methods=['POST'])
    app.add_url_rule('/api/wrong/list', 'get_wrong_answers', get_wrong_answers, methods=['GET'])
    app.add_url_rule('/api/wrong/count', 'get_wrong_answer_count', get_wrong_answer_count, methods=['GET'])
    app.add_url_rule('/api/wrong/retry', 'retry_wrong_answer', retry_wrong_answer, methods=['POST'])
    app.add_url_rule('/api/wrong/submit', 'submit_retry_answer', submit_retry_answer, methods=['POST'])
    app.add_url_rule('/api/wrong/<int:wrong_id>', 'delete_wrong_answer', lambda wrong_id: delete_wrong_answer(wrong_id), methods=['DELETE'])