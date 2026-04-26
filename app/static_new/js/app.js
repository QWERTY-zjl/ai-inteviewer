// AI面试系统 - 主逻辑
const API_BASE = '/api';
let interviewToken = '';
let currentIndex = 0;
let questions = [];
let isRecording = false;
let mediaRecorder = null;
let mediaStream = null;
let recTime = 0;
let recTimer = null;
let expressionScores = [];
let radarChart = null;

// ===== 页面状态管理 =====
function showSection(name) {
  ['loginSection', 'registerSection', 'uploadSection', 'interviewSection', 'reportSection'].forEach(s => {
    document.getElementById(s).classList.add('hidden');
  });
  document.getElementById(name).classList.remove('hidden');
}

// ===== 登录注册 =====
async function login() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password})
    });
    const data = await res.json();
    
    if (data.token) {
      localStorage.setItem('token', data.token);
      localStorage.setItem('username', username);
      showUpload();
      updateUserInfo();
    } else {
      toast(data.error || '登录失败');
    }
  } catch (e) {
    toast('登录失败: ' + e.message);
  }
}

async function register() {
  const username = document.getElementById('regUsername').value;
  const email = document.getElementById('regEmail').value;
  const phone = document.getElementById('regPhone').value;
  const password = document.getElementById('regPassword').value;
  
  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, email, phone, password})
    });
    const data = await res.json();
    
    if (data.id) {
      toast('注册成功，请登录');
      showLogin();
    } else {
      toast(data.error || '注册失败');
    }
  } catch (e) {
    toast('注册失败: ' + e.message);
  }
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('username');
  showLogin();
  updateUserInfo();
}

function showRegister() {
  showSection('registerSection');
}

function showLogin() {
  showSection('loginSection');
}

function showUpload() {
  showSection('uploadSection');
}

// ===== 简历上传 =====
async function uploadResume() {
  const fileInput = document.getElementById('resumeFile');
  const file = fileInput.files[0];
  
  if (!file) {
    toast('请选择简历文件');
    return;
  }
  
  const formData = new FormData();
  formData.append('resume', file);
  
  try {
    toast('正在上传简历...');
    const res = await fetch(`${API_BASE}/interview/upload_resume`, {
      method: 'POST',
      headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')},
      body: formData
    });
    const data = await res.json();
    
    if (data.token) {
      interviewToken = data.token;
      toast('简历上传成功，开始面试');
      startInterview(data.token);
    } else {
      toast(data.error || '上传失败');
    }
  } catch (e) {
    toast('上传失败: ' + e.message);
  }
}

// ===== 面试流程 =====
async function startInterview(token) {
  interviewToken = token;
  currentIndex = 0;
  questions = [];
  showSection('interviewSection');
  
  try {
    // 获取问题
    const res = await fetch(`${API_BASE}/interview/${token}/get_question`, {
      headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')}
    });
    const data = await res.json();
    
    if (data.question) {
      questions.push(data.question);
      renderQuestion();
      updateProgress();
    }
  } catch (e) {
    toast('获取问题失败: ' + e.message);
  }
}

function renderQuestion() {
  const q = questions[currentIndex];
  if (!q) return;
  
  document.getElementById('questionNum').textContent = `问题 ${currentIndex + 1}`;
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
  
  // 如果回答过当前问题，允许下一题
  const hasAnswer = questions[currentIndex] && questions[currentIndex].user_answer;
  document.getElementById('btnNext').disabled = !hasAnswer;
}

function updateProgress() {
  const answered = questions.filter(q => q.user_answer).length;
  const total = Math.max(questions.length, 5);
  const percent = Math.round((answered / total) * 100);
  
  document.getElementById('progressText').textContent = `${answered}/${total}`;
  document.getElementById('progressFill').style.width = percent + '%';
  document.getElementById('btnFinish').disabled = answered < 3;
}

async function submitAnswer() {
  const answer = document.getElementById('answerText').value.trim();
  if (!answer) {
    toast('请输入回答');
    return;
  }
  
  const q = questions[currentIndex];
  q.user_answer = answer;
  
  try {
    toast('正在提交...');
    const res = await fetch(`${API_BASE}/interview/${interviewToken}/submit_text_answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
      },
      body: JSON.stringify({
        question_id: q.id,
        answer_text: answer
      })
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
    
    // 自动跳到下一题
    if (currentIndex < questions.length - 1) {
      setTimeout(() => {
        currentIndex++;
        renderQuestion();
      }, 1000);
    }
  } catch (e) {
    toast('提交失败: ' + e.message);
  }
}

function prevQuestion() {
  if (currentIndex > 0) {
    currentIndex--;
    renderQuestion();
  }
}

function nextQuestion() {
  if (currentIndex < questions.length - 1) {
    currentIndex++;
    renderQuestion();
  }
}

// ===== 完成面试 =====
async function finishInterview() {
  try {
    toast('正在生成报告...');
    const res = await fetch(`${API_BASE}/evaluation/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
      },
      body: JSON.stringify({token: interviewToken})
    });
    const data = await res.json();
    
    if (data.evaluation) {
      renderReport(data.evaluation);
    } else {
      toast(data.error || '生成报告失败');
    }
  } catch (e) {
    toast('生成报告失败: ' + e.message);
  }
}

function renderReport(evaluation) {
  showSection('reportSection');
  
  // 综合评分
  document.getElementById('totalScore').textContent = evaluation.averageScore || evaluation.overall_score || '--';
  const level = getLevelText(evaluation.averageScore || evaluation.overall_score);
  document.getElementById('totalLevel').textContent = level;
  
  // 建议
  const rec = document.getElementById('recommendation');
  if (evaluation.recommendation) {
    rec.innerHTML = `<span class="badge ${evaluation.recommendation === '强烈推荐' ? 'badge-success' : 'badge-warning'}">${evaluation.recommendation}</span>`;
  }
  
  // 详细评价
  const details = document.getElementById('evaluationDetails');
  if (evaluation.detailedScores) {
    details.innerHTML = evaluation.detailedScores.map(s => `
      <div class="mb-3">
        <div class="flex justify-between mb-1">
          <span>${s.name}</span>
          <span class="text-gradient font-bold">${s.percentage}%</span>
        </div>
        <div class="progress"><div class="progress-fill" style="width:${s.percentage}%"></div></div>
      </div>
    `).join('');
  } else {
    details.innerHTML = '<p class="text-muted">暂无详细评价</p>';
  }
  
  // 改进建议
  const improvements = document.getElementById('improvements');
  if (evaluation.improvements) {
    improvements.innerHTML = '<ul>' + evaluation.improvements.map(i => `<li class="mb-2">${i}</li>`).join('') + '</ul>';
  } else {
    improvements.innerHTML = '<p class="text-muted">暂无改进建议</p>';
  }
  
  // 雷达图
  renderRadarChart(evaluation.detailedScores || []);
}

function renderRadarChart(detailedScores) {
  const ctx = document.getElementById('radarChart');
  if (!ctx) return;
  
  if (radarChart) {
    radarChart.destroy();
  }
  
  const labels = detailedScores.length ? detailedScores.map(s => s.name) : ['表达能力', '技术能力', '逻辑思维', '应变能力', '经验匹配'];
  const data = detailedScores.length ? detailedScores.map(s => s.percentage || 50) : [70, 65, 80, 75, 60];
  
  radarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: labels,
      datasets: [{
        label: '能力评分',
        data: data,
        backgroundColor: 'rgba(99, 102, 241, 0.2)',
        borderColor: '#6366f1',
        tension: 0.4,
        fill: true,
        backgroundColor: 'rgba(99, 102, 241, 0.1)'
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { color: '#9ca3af' } },
        x: { ticks: { color: '#9ca3af' } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

// ===== 重新开始面试 =====
function restartInterview() {
  interviewToken = '';
  currentIndex = 0;
  questions = [];
  expressionScores = [];
  showUpload();
}

// ===== 获取URL参数 =====
function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

// 从URL启动面试
const urlToken = getQueryParam('token');
if (urlToken) {
  startInterview(urlToken);
}
        borderWidth: 2,
        pointBackgroundColor: '#6366f1',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#6366f1'
      }]
    },
    options: {
      responsive: true,
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          ticks: { stepSize: 20, color: '#9ca3af' },
          pointLabels: { color: '#e5e7eb' }
        }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function getLevelText(score) {
  if (!score) return '暂无评分';
  if (score >= 90) return '优秀';
  if (score >= 80) return '良好';
  if (score >= 70) return '中等';
  if (score >= 60) return '及格';
  return '需改进';
}

// ===== 摄像头功能 =====
async function startCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    const video = document.getElementById('videoPreview');
    video.srcObject = mediaStream;
    document.getElementById('cameraOverlay').classList.add('hidden');
    document.getElementById('btnStartRec').disabled = false;
    document.getElementById('expressionStatus').textContent = '摄像头已启动，开始表情分析...';
    
    // 开始表情分析
    startExpressionAnalysis();
  } catch (e) {
    toast('无法访问摄像头: ' + e.message);
  }
}

async function startExpressionAnalysis() {
  if (!mediaStream) return;
  
  const video = document.getElementById('videoPreview');
  const canvas = document.createElement('canvas');
  canvas.width = 320;
  canvas.height = 240;
  const ctx = canvas.getContext('2d');
  
  setInterval(async () => {
    if (!mediaStream || !document.getElementById('expressionChart')) return;
    
    ctx.drawImage(video, 0, 0, 320, 240);
    const imageData = canvas.toDataURL('image/jpeg', 0.5);
    
    try {
      const res = await fetch(`${API_BASE}/expression/detect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
        body: JSON.stringify({image: imageData})
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.emotion) {
          const score = data.emotion_score || 80;
          expressionScores.push(score);
          updateExpressionUI(score);
        }
      }
    } catch (e) {
      // 静默失败，不影响面试
    }
  }, 5000); // 每5秒分析一次
}

function updateExpressionUI(score) {
  document.getElementById('emotionScore').textContent = score;
  document.getElementById('expressionCount').textContent = expressionScores.length;
  const avg = Math.round(expressionScores.reduce((a, b) => a + b, 0) / expressionScores.length);
  document.getElementById('avgScore').textContent = avg;
}

// ===== 录制功能 =====
function startRecording() {
  if (!mediaStream) return;
  
  mediaRecorder = new MediaRecorder(mediaStream);
  audioChunks = [];
  
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstop = uploadRecording;
  
  mediaRecorder.start();
  isRecording = true;
  
  document.getElementById('btnStartRec').classList.add('hidden');
  document.getElementById('btnStopRec').classList.remove('hidden');
  document.getElementById('recordingIndicator').classList.remove('hidden');
  
  // 计时器
  recTime = 0;
  recTimer = setInterval(() => {
    recTime++;
    const mins = Math.floor(recTime / 60).toString().padStart(2, '0');
    const secs = (recTime % 60).toString().padStart(2, '0');
    document.getElementById('recTime').textContent = `${mins}:${secs}`;
  }, 1000);
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    
    document.getElementById('btnStartRec').classList.remove('hidden');
    document.getElementById('btnStopRec').classList.add('hidden');
    document.getElementById('recordingIndicator').classList.add('hidden');
    
    clearInterval(recTimer);
  }
}

async function uploadRecording() {
  if (!audioChunks.length) return;
  
  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');
  formData.append('question_id', questions[currentIndex]?.id || 0);
  
  try {
    await fetch(`${API_BASE}/interview/${interviewToken}/upload_audio`, {
      method: 'POST',
      headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')},
      body: formData
    });
    toast('录音已保存');
  } catch (e) {
    toast('上传录音失败');
  }
}

// ===== 文字输入监控 =====
document.addEventListener('DOMContentLoaded', () => {
  const answerText = document.getElementById('answerText');
  if (answerText) {
    answerText.addEventListener('input', () => {
      document.getElementById('charCount').textContent = answerText.value.length;
    });
  }
  
  // 检查登录状态
  if (localStorage.getItem('token')) {
    showUpload();
    updateUserInfo();
  } else {
    showLogin();
  }
});

function updateUserInfo() {
  const username = localStorage.getItem('username');
  if (username) {
    document.getElementById('userInfo').textContent = '欢迎，' + username;
    document.getElementById('userInfo').classList.remove('hidden');
    document.getElementById('btnLogout').classList.remove('hidden');
  }
}

// ===== Toast提示 =====
function toast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// ===== 初始化表情图表 =====
function initExpressionChart() {
  const ctx = document.getElementById('expressionChart');
  if (!ctx) return;
  
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: '情绪得分',
        data: [],
        borderColor: '#6366f1',
        tension: 0.4,
        fill: true,
        backgroundColor: 'rgba(99, 102, 241, 0.1)'
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { color: '#9ca3af' } },
        x: { ticks: { color: '#9ca3af' } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

// ===== 重新开始面试 =====
function restartInterview() {
  interviewToken = '';
  currentIndex = 0;
  questions = [];
  expressionScores = [];
  showUpload();
}

// ===== 获取URL参数 =====
function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

// 从URL启动面试
const urlToken = getQueryParam('token');
if (urlToken) {
  startInterview(urlToken);
}
