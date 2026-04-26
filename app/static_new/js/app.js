// AI面试系统 - 主逻辑
const API_BASE = '/api';
let interviewToken = '';
let currentIndex = 0;
let questions = [];

// 页面状态管理
function showSection(name) {
  ['loginSection', 'registerSection', 'uploadSection', 'interviewSection', 'reportSection'].forEach(s => {
    const el = document.getElementById(s);
    if (el) el.classList.add('hidden');
  });
  const target = document.getElementById(name);
  if (target) target.classList.remove('hidden');
}

function showRegister() { showSection('registerSection'); }
function showLogin() { showSection('loginSection'); }
function showUpload() { showSection('uploadSection'); }

// Toast提示
function toast(msg) {
  const t = document.getElementById('toast');
  if (t) { t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 3000); }
}

// 登录
async function login() {
  const u = document.getElementById('username').value;
  const p = document.getElementById('password').value;
  if (!u || !p) { toast('请输入用户名和密码'); return; }
  try {
    const res = await fetch(API_BASE + '/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username: u, password: p})
    });
    const data = await res.json();
    if (data.status === 'success' || data.token) {
      localStorage.setItem('token', data.token || 'logged_in');
      localStorage.setItem('username', u);
      toast('登录成功');
      showUpload();
      updateUserInfo();
    } else {
      toast(data.error || data.message || '登录失败');
    }
  } catch (e) { toast('登录失败: ' + e.message); }
}

// 注册
async function register() {
  const u = document.getElementById('regUsername').value;
  const e = document.getElementById('regEmail').value;
  const ph = document.getElementById('regPhone').value;
  const p = document.getElementById('regPassword').value;
  if (!u || !e || !p) { toast('请填写必填项'); return; }
  try {
    const res = await fetch(API_BASE + '/auth/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username: u, email: e, phone: ph, password: p})
    });
    const data = await res.json();
    if (data.id) {
      toast('注册成功，请登录');
      showLogin();
    } else {
      toast(data.error || '注册失败');
    }
  } catch (e) { toast('注册失败: ' + e.message); }
}

// 简历上传
async function uploadResume() {
  const fileInput = document.getElementById('resumeFile');
  const file = fileInput.files[0];
  if (!file) { toast('请选择简历文件'); return; }
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
      toast('上传成功，开始面试');
      showSection('interviewSection');
      loadQuestions();
    } else {
      toast(data.error || '上传失败');
    }
  } catch (e) { toast('上传失败: ' + e.message); }
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
    }
  } catch (e) { toast('获取问题失败'); }
}

// 渲染问题
function renderQuestion() {
  const q = questions[currentIndex];
  if (!q) return;
  document.getElementById('questionNum').textContent = '问题 ' + (currentIndex + 1);
  document.getElementById('questionType').textContent = q.category || '面试问题';
  document.getElementById('questionText').textContent = q.question_text || q.question || '无问题内容';
  document.getElementById('scoreStandard').textContent = q.scoring_criteria || '表达清晰、逻辑完整';
  document.getElementById('answerText').value = '';
  document.getElementById('charCount').textContent = '0';
  document.getElementById('btnSubmit').disabled = false;
  updateNavButtons();
}

function updateNavButtons() {
  document.getElementById('btnPrev').disabled = currentIndex === 0;
  document.getElementById('btnNext').disabled = currentIndex >= questions.length - 1;
  const hasAnswer = questions[currentIndex] && questions[currentIndex].user_answer;
  document.getElementById('btnNext').disabled = !hasAnswer;
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
  if (!answer) { toast('请输入回答'); return; }
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
      toast('回答已提交');
    } else {
      toast('这是最后一题');
    }
    updateProgress();
    updateNavButtons();
    if (currentIndex < questions.length - 1) {
      setTimeout(function() { currentIndex++; renderQuestion(); }, 1000);
    }
  } catch (e) { toast('提交失败'); }
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
      toast(data.error || '生成报告失败');
    }
  } catch (e) { toast('生成报告失败'); }
}

function renderReport(evaluation) {
  showSection('reportSection');
  document.getElementById('totalScore').textContent = evaluation.averageScore || evaluation.overall_score || '--';
  document.getElementById('totalLevel').textContent = getLevelText(evaluation.averageScore || evaluation.overall_score);
  if (evaluation.recommendation) {
    document.getElementById('recommendation').innerHTML = '<span class="badge badge-success">' + evaluation.recommendation + '</span>';
  }
  if (evaluation.detailedScores) {
    document.getElementById('evaluationDetails').innerHTML = evaluation.detailedScores.map(function(s) {
      return '<div class="mb-3"><div class="flex justify-between mb-1"><span>' + s.name + '</span><span class="text-gradient font-bold">' + s.percentage + '%</span></div><div class="progress"><div class="progress-fill" style="width:' + s.percentage + '%"></div></div></div>';
    }).join('');
  }
  renderRadarChart(evaluation.detailedScores || []);
}

function getLevelText(score) {
  if (!score) return '暂无评分';
  if (score >= 90) return '优秀';
  if (score >= 80) return '良好';
  if (score >= 70) return '中等';
  if (score >= 60) return '及格';
  return '需改进';
}

// 渲染雷达图
let radarChart = null;
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
        backgroundColor: 'rgba(99, 102, 241, 0.2)',
        borderColor: '#6366f1',
        borderWidth: 2,
        pointBackgroundColor: '#6366f1'
      }]
    },
    options: {
      responsive: true,
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          ticks: { stepSize: 20, color: '#9ca3af' }
        }
      }
    }
  });
}

// 更新用户信息
function updateUserInfo() {
  const u = localStorage.getItem('username');
  if (u) {
    const ui = document.getElementById('userInfo');
    if (ui) { ui.textContent = '欢迎，' + u; ui.classList.remove('hidden'); }
    const lo = document.getElementById('btnLogout');
    if (lo) lo.classList.remove('hidden');
  }
}

// 退出登录
function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('username');
  showLogin();
}

// 文字计数
document.addEventListener('DOMContentLoaded', function() {
  const ta = document.getElementById('answerText');
  if (ta) {
    ta.addEventListener('input', function() {
      document.getElementById('charCount').textContent = ta.value.length;
    });
  }
  if (localStorage.getItem('token')) {
    showUpload();
    updateUserInfo();
  } else {
    showLogin();
  }
});

console.log('app.js loaded');
