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
        """提交重做答案 - 使用AI评分"""
        from flask import jsonify, request
        import os
        try:
            data = request.json
            user_id = data.get('user_id')
            wrong_id = data.get('wrong_id')
            new_answer = data.get('user_answer', '') or data.get('new_answer', '')
            
            conn = get_db()
            wrong = conn.execute('''
                SELECT question_text, correct_answer, user_answer, best_score
                FROM wrong_answers WHERE id = ? AND user_id = ?
            ''', (wrong_id, user_id)).fetchone()
            
            if not wrong:
                return_db(conn)
                return jsonify({"status": "error", "message": "错题不存在"}), 404
            
            question_text = wrong['question_text']
            return_db(conn)
            
            # 使用AI评分
            score = 0
            feedback = ""
            api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('OPENAI_API_KEY')
            
            if api_key and new_answer.strip():
                try:
                    import requests
                    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    prompt = f"""你是一个面试答案评分专家。

问题：{question_text}

用户答案：{new_answer}

请评估答案质量并返回JSON格式评分：
{{"score": 0-100的整数, "feedback": "简短评价"}}

评分标准：
- 90-100分：回答完整、准确、有深度
- 70-89分：回答基本准确，有一定深度
- 60-69分：回答基本正确，但不够深入
- 60分以下：回答不完整或错误
"""
                    
                    payload = {
                        "model": "qwen-plus",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                    
                    resp = requests.post(url, headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        result = resp.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        import json as json_lib
                        try:
                            score_data = json_lib.loads(content)
                            score = int(score_data.get('score', 60))
                            feedback = score_data.get('feedback', '')
                        except:
                            score = 60 if len(new_answer) > 20 else 0
                except Exception as e:
                    logger.error(f"[ERROR] AI评分失败: {e}")
                    score = 60 if len(new_answer) > 20 else 0
            else:
                score = 60 if len(new_answer) > 20 else 0
            
            # 更新数据库
            conn = get_db()
            best_score = float(wrong['best_score']) if wrong['best_score'] else 0
            new_best = max(best_score, float(score))
            passed = score >= 60
            
            conn.execute('''
                UPDATE wrong_answers
                SET user_answer = ?, score = ?, best_score = ?, retry_count = retry_count + 1
                WHERE id = ? AND user_id = ?
            ''', (new_answer, score, new_best, wrong_id, user_id))
            
            conn.commit()
            return_db(conn)
            
            return jsonify({
                "status": "success",
                "score": int(score),
                "best_score": int(new_best),
                "passed": passed,
                "feedback": feedback,
                "message": "已掌握" if passed else "继续加油"
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

    def get_wrong_answer_detail(wrong_id):
        """获取错题详情 / 删除错题"""
        from flask import jsonify, request
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({"status": "error", "message": "缺少user_id"}), 400
            
            conn = get_db()
            
            # DELETE 方法
            if request.method == 'DELETE':
                result = conn.execute('''
                    DELETE FROM wrong_answers WHERE id = ? AND user_id = ?
                ''', (wrong_id, user_id))
                conn.commit()
                return_db(conn)
                
                if result.rowcount == 0:
                    return jsonify({"status": "error", "message": "错题不存在"}), 404
                
                return jsonify({"status": "success", "message": "错题已删除"})
            
            # GET 方法
            wrong = conn.execute('''
                SELECT id, question_text, user_answer, correct_answer, score, 
                       is_favorited, retry_count, best_score, created_at
                FROM wrong_answers
                WHERE id = ? AND user_id = ?
            ''', (wrong_id, user_id)).fetchone()
            
            return_db(conn)
            
            if not wrong:
                return jsonify({"status": "error", "message": "错题不存在"}), 404
            
            return jsonify({
                "status": "success",
                "data": dict(wrong)
            })
        except Exception as e:
            logger.error(f"[ERROR] get_wrong_answer_detail: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500
    
    # 注册路由
    app.add_url_rule('/api/wrong/add', 'add_wrong_answer', add_wrong_answer, methods=['POST'])
    app.add_url_rule('/api/wrong/list', 'get_wrong_answers', get_wrong_answers, methods=['GET'])
    app.add_url_rule('/api/wrong/count', 'get_wrong_answer_count', get_wrong_answer_count, methods=['GET'])
    app.add_url_rule('/api/wrong/retry', 'retry_wrong_answer', retry_wrong_answer, methods=['POST'])
    app.add_url_rule('/api/wrong/submit', 'submit_retry_answer', submit_retry_answer, methods=['POST'])
    app.add_url_rule('/api/wrong/<int:wrong_id>', 'get_wrong_answer_detail', get_wrong_answer_detail, methods=['GET', 'DELETE'])