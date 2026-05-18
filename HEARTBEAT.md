# HEARTBEAT.md - 胖猫心跳任务

> **核心职责**：作为调度中枢，定时监控所有后台任务和系统健康状态

---

## 🚀 胖猫调度规则

### 任务提交规范
- 复杂/长任务：设置超时为 0（无限制）或很长（如 3600s）
- 任务提交后：**不要等待**，记录 task_id 到下方监控列表
- 统一由心跳文件驱动监控，不再依赖 CLI 超时

### 监控策略
- 每 5 分钟检查一次所有进行中的任务
- 任务完成后整理结果上报皇上
- 任务失败时立即上报皇上

---

## 📊 当前监控任务

| Task ID | 负责人 | 任务类型 | 状态 | 完成时间 |
|---------|--------|----------|------|----------|
| 9db4c8aa-bb58-4715-bbe0-50051655d9b7 | 奶龙 | 每日市场分析 | ✅ 正常 | 每天9:00 |

### 已完成任务（历史记录）

| Task ID | 负责人 | 任务类型 | 状态 | 完成时间 |
|---------|--------|----------|------|----------|
| - | 胖猫 | 评分报告API修复 | ✅ 完成 | 2026-04-26 03:00 |
| - | 胖猫 | question_service markdown解析修复 | ✅ 完成 | 2026-04-26 02:30 |
| - | 胖猫 | TTS语音合成修复 | ✅ 完成 | 2026-04-26 02:40 |
| - | 胖猫 | TTS音频播放中断修复 | ✅ 完成 | 2026-04-27 20:30 |
| - | 胖猫 | 音色列表API添加 | ✅ 完成 | 2026-04-27 20:30 |
| - | 胖猫 | ASR语音识别功能 | ✅ 完成 | 2026-04-27 20:50 |
| - | 胖猫 | HTTPS配置 | ✅ 完成 | 2026-04-28 |
| - | 胖猫 | 错题本功能 | ✅ 完成 | 2026-05-11 |
| - | 胖猫 | 错题重试AI评分 | ✅ 完成 | 2026-05-19 |

---

## ⚠️ 问题检测

| 问题 | 优先级 | 状态 | 说明 |
|------|--------|------|------|
| App容器无限重启 | 🔴 紧急 | ✅ 已修复 | 使用volume挂载最新代码 |
| 健康检查端点 | 🟡 中 | ✅ 已添加 | /api/health 返回 {"service":"project-interview","status":"ok"} |
| 阿里云TTS免费额度用完 | 🔴 高 | ⚠️ 待处理 | 返回403，需关闭"仅使用免费额度" |
| 表情识别API | 🔴 高 | ⚠️ 待验证 | 需真实图片测试（400错误可能额度问题） |
| 摄像头/麦克风需要HTTPS | 🟡 中 | ✅ 已配置 | getUserMedia需要安全上下文 |

---

## 🔍 奶龙定时任务监控

| 项目 | 值 |
|------|-----|
| 任务ID | 9db4c8aa-bb58-4715-bbe0-50051655d9b7 |
| 新Cron | `0 * * * *`（每小时） |
| 下次执行 | 03:00 (Asia/Shanghai) |
| 监控状态 | 🔄 监控中... |

---

## 🔍 系统健康检查（每 5 分钟）

### 1. Docker 容器
```bash
sudo docker ps --format "{{.Names}}: {{.Status}}" | grep -v "Up"
```
**异常处理**：`sudo docker restart project-interview-app project-interview-nginx-1`

### 2. 服务健康
```bash
curl -s --max-time 5 http://localhost:10003/api/health
sudo docker logs project-interview-app --since 5m 2>&1 | grep -i "error\|exception" | tail -5
```

---

## 🌐 HTTPS配置 (2026-04-28)

| 项目 | 值 |
|------|-----|
| 证书类型 | 自签名证书 |
| 证书CN | 47.101.129.131 |
| HTTP端口 | 80 → 301重定向到HTTPS |
| HTTPS端口 | 443 |
| 配置文件 | /home/admin/project-interview/project-interview/nginx/ssl_new/ |

**访问地址**：
| URL | 说明 |
|-----|------|
| https://47.101.129.131/login.html | 登录页 |
| https://47.101.129.131/pricing.html | 套餐页 |
| https://47.101.129.131/admin.html | 管理后台 |
| https://47.101.129.131/wrong.html | 错题本 |
| https://47.101.129.131/interview.html | 面试页 |

---

## 🎨 UI风格

| 页面 | 文件 | 风格 |
|------|------|------|
| 登录页 | login.html | 北极光波浪 + 流星 + 星空 |
| 套餐页 | pricing.html | 赛博朋克极光 + 毛玻璃卡片 |
| 面试页 | interview.html | 赛博朋克极光 + 极光动画 |
| 错题本 | wrong.html | 赛博朋克极光 + 极光动画 |
| 管理页 | admin.html | 保持原样 |

---

## 🔊 TTS/ASR 配置

| 项目 | 值 |
|------|-----|
| TTS模型 | qwen3-tts-flash |
| TTS音色 | Ethan(男), Cherry/Serena(女), Aiden |
| ASR模型 | qwen3-asr-flash |
| 前端默认 | 云端ASR模式 |

**API接口**：
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/tts/voices` | GET | 获取可用音色列表 |
| `/api/asr/recognize` | POST | 语音识别 |

---

## 🔧 错题本功能 (2026-05-19)

**流程**：
```
面试结束 → 判定score<60 → 自动加入错题本
                                    ↓
用户访问错题本 → 点击重新练习 → 答题界面
                                    ↓
用户答题 → AI评分 → 自动回到错题本
```

**API**：
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/wrong/add` | POST | 添加错题 |
| `/api/wrong/list` | GET | 获取错题列表 |
| `/api/wrong/<id>` | GET/DELETE | 获取详情/删除 |
| `/api/wrong/submit` | POST | 提交重做答案（AI评分） |
| `/api/wrong/count` | GET | 获取错题数量 |

**评分**：使用 qwen-plus 大模型评估答案质量

---

## 🔧 Nginx配置

**静态文件配置**：
```nginx
location /static/ {
    alias /app/static/;
    expires 30d;
}
location / {
    try_files $uri $uri/ /admin.html;
}
```

---

## 📋 待处理任务

| 任务 | 负责人 | 优先级 | 状态 |
|------|--------|--------|------|
| 阿里云TTS免费额度用完 | - | 🔴 高 | ⚠️ 待处理 |
| 表情识别API | - | 🔴 高 | ⚠️ 待验证 |
| db_pool.py 清理 | 洋洋 | 🟢 低 | 可选 |

---

*最后更新：2026-05-19*