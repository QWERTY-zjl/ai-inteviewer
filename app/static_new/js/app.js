// AI面试系统 - 主逻辑
const API_BASE = '/api';
let interviewToken = '';
let currentIndex = 0;
let questions = [];
let radarChart = null;
let expressionChart = null;
let expressionScores = [];
let mediaStream = null;
let mediaRecorder = null;
let recTime = 0;
let recTimer = null;

// 页面状态管理
function showSection(name) {
    ['loginSection', 'registerSection', 'uploadSection', 'interviewSection', 'reportSection'].forEach(s => {
        const el = document.getElementById(s);
        if (el) el.classList.add('hidden');
    });
    const target = document.getElementById(name);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('fade-in');
    }
}

function showRegister() { showSection('registerSection'); }
function showLogin() { showSection('loginSection'); }
function showUpload() { showSection('uploadSection'); }

// Toast提示
function toast(msg, type = '') {
    const t = document.getElementById('toast');
    if (t) {
        t.textContent = msg;
        t.className = 'toast show ' + type;
        setTimeout(() => t.classList.remove('show'), 3000);
    }
}

// 登录
async function login() {
    const u = document.getElementById('username').value.trim();
    const p = document.getElementById('password').value;
    if (!u || !p) { toast('请输入用户名和密码', 'error'); return; }
    try {
        const res = await fetch(API_BASE + '/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, password: p})
        });
        const data = await res.json();
        if (data.status === 'success' || data.token || data.user) {
            localStorage.setItem('token', data.token || data.user?.id || 'logged_in');
            localStorage.setItem('username', u);
            toast('登录成功', 'success');
            showUpload();
            updateUserInfo();
        } else {
            toast(data.error || data.message || '登录失败', 'error');
        }
    } catch (e) { toast('登录失败: ' + e.message, 'error'); }
}

// 注册
async function register() {
    const u = document.getElementById('regUsername').value.trim();
    const e = document.getElementById('regEmail').value.trim();
    const ph = document.getElementById('regPhone').value.trim();
    const p = document.getElementById('regPassword').value;
    if (!u || !e || !p) { toast('请填写必填项', 'error'); return; }
    try {
        const res = await fetch(API_BASE + '/auth/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, email: e, phone: ph, password: p})
        });
        const data = await res.json();
        if (data.id || data.status === 'success') {
            toast('注册成功，请登录', 'success');
            showLogin();
        } else {
            toast(data.error || data.message || '注册失败', 'error');
        }
    } catch (e) { toast('注册失败: ' + e.message, 'error'); }
}

// 简历上传
async function uploadResume() {
    const fileInput = document.getElementById('resumeFile');
    const file = fileInput.files[0];
    if (!file) { toast('请选择简历文件', 'error'); return; }
    const formData = new FormData();
    formData.append('resume', file);
    try {
        toast('正在上传...');
        const res = await fetch(API_BASE + '/interview/upload_resume', {
            method: 'POST',
            headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')},
            body: formData
        });
        const data = await res.json();
        if (data.token) {
            interviewToken = data.token;
            toast('上传成功，开始面试', 'success');
            showSection('interviewSection');
            loadQuestions();
        } else {
            toast(data.error || '上传失败', 'error');
        }
    } catch (e) { toast('上传失败: ' + e.message, 'error'); }
}

// 加载问题
async function loadQuestions() {
    try {
        const res = await fetch(API_BASE + '/interview/' + interviewToken + '/get_question', {
            headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')}
        });
        const data = await res.json();
        if (data.question) {
            questions = [data.question];
            currentIndex = 0;
            renderQuestion();
            updateProgress();
            initExpressionChart();
        }
    } catch (e) { toast('获取问题失败', 'error'); }
}

// 渲染问题
function renderQuestion() {
    const q = questions[currentIndex];
    if (!q) return;
    document.getElementById('questionNum').textContent = '问题 ' + (currentIndex + 1);
    document.getElementById('questionType').textContent = q.category || '面试问题';
    document.getElementById('questionText').textContent = q.question_text || q.question || '无问题内容';
    document.getElementById('scoreStandard').textContent = q.scoring_criteria || '表达清晰、逻辑完整';
    document.getElementById('answerText').value = q.user_answer || '';
    document.getElementById('charCount').textContent = (q.user_answer || '').length;
    document.getElementById('btnSubmit').disabled = false;
    updateNavButtons();
}

function updateNavButtons() {
    document.getElementById('btnPrev').disabled = currentIndex === 0;
    const hasAnswer = questions[currentIndex] && questions[currentIndex].user_answer;
    document.getElementById('btnNext').disabled = !hasAnswer || currentIndex >= questions.length - 1;
}

function updateProgress() {
    const answered = questions.filter(q => q.user_answer).length;
    const total = Math.max(questions.length, 5);
    const percent = Math.round((answered / total) * 100);
    document.getElementById('progressText').textContent = answered + '/' + total;
    document.getElementById('progressFill').style.width = percent + '%';
    document.getElementById('btnFinish').disabled = answered < 3;
}

// 提交答案
async function submitAnswer() {
    const answer = document.getElementById('answerText').value.trim();
    if (!answer) { toast('请输入回答', 'error'); return; }
    const q = questions[currentIndex];
    q.user_answer = answer;
    try {
        toast('正在提交...');
        const res = await fetch(API_BASE + '/interview/' + interviewToken + '/submit_text_answer', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token')},
            body: JSON.stringify({question_id: q.id, answer_text: answer})
        });
        const data = await res.json();
        if (data.next_question) {
            questions.push(data.next_question);
            toast('回答已提交', 'success');
        } else {
            toast('这是最后一题', 'success');
        }
        updateProgress();
        updateNavButtons();
        if (currentIndex < questions.length - 1) {
            setTimeout(function() { currentIndex++; renderQuestion(); }, 1000);
        }
    } catch (e) { toast('提交失败', 'error'); }
}

function prevQuestion() {
    if (currentIndex > 0) { currentIndex--; renderQuestion(); }
}

function nextQuestion() {
    if (currentIndex < questions.length - 1) { currentIndex++; renderQuestion(); }
}

// 完成面试
async function finishInterview() {
    try {
        toast('正在生成报告...');
        const res = await fetch(API_BASE + '/evaluation/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token')},
            body: JSON.stringify({token: interviewToken})
        });
        const data = await res.json();
        if (data.evaluation) {
            renderReport(data.evaluation);
        } else {
            toast(data.error || '生成报告失败', 'error');
        }
    } catch (e) { toast('生成报告失败', 'error'); }
}

function renderReport(evaluation) {
    showSection('reportSection');
    const score = evaluation.averageScore || evaluation.overall_score || 0;
    document.getElementById('totalScore').textContent = score;
    
    // 等级徽章
    const levelEl = document.getElementById('levelBadge');
    let levelClass = 'level-pass';
    let levelText = '需改进';
    if (score >= 90) { levelClass = 'level-excellent'; levelText = '🌟 优秀'; }
    else if (score >= 80) { levelClass = 'level-good'; levelText = '👍 良好'; }
    else if (score >= 70) { levelClass = 'level-average'; levelText = '💪 中等'; }
    else if (score >= 60) { levelClass = 'level-pass'; levelText = '⚠️ 及格'; }
    else { levelClass = 'level-pass'; levelText = '📚 需改进'; }
    levelEl.innerHTML = '<span class="level-badge ' + levelClass + '">' + levelText + '</span>';
    
    // 建议
    const rec = document.getElementById('recommendation');
    if (evaluation.recommendation) {
        rec.innerHTML = '<p style="color:var(--muted)">' + evaluation.recommendation + '</p>';
    }
    
    // 详细评价
    const details = document.getElementById('evaluationDetails');
    if (evaluation.detailedScores && evaluation.detailedScores.length) {
        details.innerHTML = evaluation.detailedScores.map(function(s) {
            return '<div class="evaluation-item"><div class="evaluation-header"><span>' + s.name + '</span><span style="color:var(--accent)">' + s.percentage + '%</span></div><div class="progress-bar"><div class="progress-fill" style="width:' + s.percentage + '%"></div></div></div>';
        }).join('');
    } else {
        details.innerHTML = '<p style="color:var(--muted)">暂无详细评价</p>';
    }
    
    // 改进建议
    const improvements = document.getElementById('improvements');
    if (evaluation.improvements && evaluation.improvements.length) {
        improvements.innerHTML = '<ul style="list-style:none;padding:0">' + evaluation.improvements.map(function(i) {
            return '<li style="padding:0.5rem 0;border-bottom:1px solid var(--border)">💡 ' + i + '</li>';
        }).join('') + '</ul>';
    } else {
        improvements.innerHTML = '<p style="color:var(--muted)">暂无改进建议</p>';
    }
    
    // 雷达图
    renderRadarChart(evaluation.detailedScores || []);
}

// 渲染雷达图
function renderRadarChart(detailedScores) {
    const ctx = document.getElementById('radarChart');
    if (!ctx) return;
    if (radarChart) radarChart.destroy();
    
    const labels = detailedScores.length ? detailedScores.map(function(s) { return s.name; }) : ['表达能力', '技术能力', '逻辑思维', '应变能力', '经验匹配'];
    const data = detailedScores.length ? detailedScores.map(function(s) { return s.percentage || 50; }) : [70, 65, 80, 75, 60];
    
    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: '能力评分',
                data: data,
                backgroundColor: 'rgba(0, 240, 255, 0.2)',
                borderColor: '#00f0ff',
                borderWidth: 2,
                pointBackgroundColor: '#ff00ff',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#00f0ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { stepSize: 20, color: '#8888aa', backdropColor: 'transparent' },
                    pointLabels: { color: '#ffffff', font: { family: 'Rajdhani', size: 14 } },
                    grid: { color: 'rgba(0, 240, 255, 0.2)' },
                    angleLines: { color: 'rgba(0, 240, 255, 0.2)' }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// 表情图表
function initExpressionChart() {
    const ctx = document.getElementById('expressionChart');
    if (!ctx) return;
    if (expressionChart) expressionChart.destroy();
    
    expressionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '情绪得分',
                data: [],
                borderColor: '#00f0ff',
                backgroundColor: 'rgba(0, 240, 255, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 100, ticks: { color: '#8888aa' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                x: { ticks: { color: '#8888aa' }, grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// 摄像头功能
async function startCamera() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        const video = document.getElementById('videoPreview');
        video.srcObject = mediaStream;
        document.getElementById('cameraOverlay').classList.add('hidden');
        document.getElementById('btnStartRec').disabled = false;
        toast('摄像头已启动', 'success');
    } catch (e) { toast('无法访问摄像头: ' + e.message, 'error'); }
}

function startRecording() {
    if (!mediaStream) return;
    mediaRecorder = new MediaRecorder(mediaStream);
    const chunks = [];
    mediaRecorder.ondataavailable = function(e) { chunks.push(e.data); };
    mediaRecorder.onstop = function() {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        formData.append('question_id', questions[currentIndex]?.id || 0);
        fetch(API_BASE + '/interview/' + interviewToken + '/upload_audio', {
            method: 'POST',
            headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')},
            body: formData
        });
        toast('录音已保存', 'success');
    };
    mediaRecorder.start();
    document.getElementById('btnStartRec').classList.add('hidden');
    document.getElementById('btnStopRec').classList.remove('hidden');
    document.getElementById('recordingIndicator').classList.remove('hidden');
    recTime = 0;
    recTimer = setInterval(function() {
        recTime++;
        var m = Math.floor(recTime / 60).toString().padStart(2, '0');
        var s = (recTime % 60).toString().padStart(2, '0');
        document.getElementById('recTime').textContent = m + ':' + s;
    }, 1000);
}

function stopRecording() {
    if (mediaRecorder) { mediaRecorder.stop(); }
    document.getElementById('btnStartRec').classList.remove('hidden');
    document.getElementById('btnStopRec').classList.add('hidden');
    document.getElementById('recordingIndicator').classList.add('hidden');
    clearInterval(recTimer);
}

// 用户信息
function updateUserInfo() {
    var u = localStorage.getItem('username');
    if (u) {
        var ui = document.getElementById('navUser');
        if (ui) { ui.textContent = '👤 ' + u; ui.classList.remove('hidden'); }
        var lo = document.getElementById('btnLogout');
        if (lo) lo.classList.remove('hidden');
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    showLogin();
    document.getElementById('navUser').classList.add('hidden');
    document.getElementById('btnLogout').classList.add('hidden');
}

// 文件选择显示
document.getElementById('resumeFile')?.addEventListener('change', function() {
    var fn = document.getElementById('fileName');
    if (fn) fn.textContent = this.files[0]?.name || '支持 PDF、Word 格式';
});

// 文字计数
document.getElementById('answerText')?.addEventListener('input', function() {
    var cc = document.getElementById('charCount');
    if (cc) cc.textContent = this.value.length;
});

// 回车登录
document.getElementById('password')?.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') login();
});

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('token')) {
        showUpload();
        updateUserInfo();
    } else {
        showLogin();
    }
});

console.log('AI面试系统 loaded');
