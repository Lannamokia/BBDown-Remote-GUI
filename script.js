// 全局变量
let apiClient = null;
let refreshTimer = null;
let isConnected = false;
let currentTasks = [];

// API客户端类
class BBDownAPIClient {
    constructor(host = 'localhost', port = 58682) {
        this.host = host;
        this.port = port;
        this.baseUrl = `http://${host}:${port}`;
    }

    updateConnection(host, port) {
        this.host = host;
        this.port = port;
        this.baseUrl = `http://${host}:${port}`;
    }

    async request(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }

    async getTasks() {
        return await this.request('/api/Tasks');
    }

    async addTask(url, options = {}) {
        const taskData = {
            Url: url,
            ...options
        };
        return await this.request('/api/Tasks', 'POST', taskData);
    }

    async removeTask(aid) {
        return await this.request(`/api/Tasks/${aid}`, 'DELETE');
    }

    async getTaskDetail(aid) {
        return await this.request(`/api/Tasks/${aid}`);
    }

    async testConnection() {
        try {
            await this.request('/api/Tasks');
            return true;
        } catch (error) {
            return false;
        }
    }
}

// 工具函数
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatSpeed(bytesPerSecond) {
    if (!bytesPerSecond || bytesPerSecond === 0) return '-';
    return formatBytes(bytesPerSecond) + '/s';
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // 自动移除通知
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
    
    // 点击移除
    notification.addEventListener('click', () => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    });
}

function showLoading(show = true) {
    const loading = document.getElementById('loading-indicator');
    if (show) {
        loading.classList.add('show');
    } else {
        loading.classList.remove('show');
    }
}

function updateConnectionStatus(connected) {
    isConnected = connected;
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    const connectBtn = document.getElementById('connect-btn');
    
    if (connected) {
        statusIndicator.className = 'status-indicator online';
        statusText.textContent = '已连接';
        connectBtn.innerHTML = '<span class="icon">🔗</span> 已连接';
        connectBtn.disabled = false;
    } else {
        statusIndicator.className = 'status-indicator offline';
        statusText.textContent = '未连接';
        connectBtn.innerHTML = '<span class="icon">🔗</span> 连接';
        connectBtn.disabled = false;
    }
}

// 选项卡功能
function initTabs() {
    const tabHeaders = document.querySelectorAll('.tab-header');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const targetTab = header.getAttribute('data-tab');
            
            // 移除所有活动状态
            tabHeaders.forEach(h => h.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // 添加活动状态
            header.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
}

// 折叠组功能
function initCollapsibleGroups() {
    const groupHeaders = document.querySelectorAll('.group-header');
    
    groupHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const groupName = header.getAttribute('data-group');
            const content = document.getElementById(`${groupName}-options`);
            const icon = header.querySelector('.toggle-icon');
            
            if (content.classList.contains('expanded')) {
                content.classList.remove('expanded');
                header.classList.remove('expanded');
            } else {
                content.classList.add('expanded');
                header.classList.add('expanded');
            }
        });
    });
    
    // 默认展开基本选项
    const basicHeader = document.querySelector('[data-group="basic"]');
    const basicContent = document.getElementById('basic-options');
    if (basicHeader && basicContent) {
        basicHeader.classList.add('expanded');
        basicContent.classList.add('expanded');
    }
}

// 连接功能
async function connectToServer() {
    const hostInput = document.getElementById('host-input');
    const portInput = document.getElementById('port-input');
    const connectBtn = document.getElementById('connect-btn');
    
    const host = hostInput.value.trim() || 'localhost';
    const port = parseInt(portInput.value) || 58682;
    
    connectBtn.disabled = true;
    connectBtn.innerHTML = '<span class="icon">⏳</span> 连接中...';
    
    const statusIndicator = document.querySelector('.status-indicator');
    statusIndicator.className = 'status-indicator connecting';
    
    try {
        if (!apiClient) {
            apiClient = new BBDownAPIClient(host, port);
        } else {
            apiClient.updateConnection(host, port);
        }
        
        const connected = await apiClient.testConnection();
        
        if (connected) {
            updateConnectionStatus(true);
            showNotification('连接成功！', 'success');
            startAutoRefresh();
            await refreshTasks();
        } else {
            updateConnectionStatus(false);
            showNotification('连接失败，请检查服务器地址和端口', 'error');
        }
    } catch (error) {
        updateConnectionStatus(false);
        showNotification(`连接失败: ${error.message}`, 'error');
    }
}

// 任务刷新功能
async function refreshTasks() {
    if (!isConnected || !apiClient) {
        return;
    }
    
    try {
        const tasks = await apiClient.getTasks();
        currentTasks = tasks;
        updateTaskTables(tasks);
    } catch (error) {
        console.error('刷新任务失败:', error);
        updateConnectionStatus(false);
        showNotification('刷新任务失败，连接已断开', 'error');
    }
}

function updateTaskTables(tasks) {
    const runningTable = document.getElementById('running-tasks-table').querySelector('tbody');
    const finishedTable = document.getElementById('finished-tasks-table').querySelector('tbody');
    const runningEmpty = document.getElementById('running-empty');
    const finishedEmpty = document.getElementById('finished-empty');
    
    // 清空表格
    runningTable.innerHTML = '';
    finishedTable.innerHTML = '';
    
    const runningTasks = tasks.filter(task => 
        task.Status === 'Running' || task.Status === 'Pending' || task.Status === 'Downloading'
    );
    const finishedTasks = tasks.filter(task => 
        task.Status === 'Completed' || task.Status === 'Failed' || task.Status === 'Cancelled'
    );
    
    // 更新运行中任务
    if (runningTasks.length > 0) {
        runningEmpty.style.display = 'none';
        runningTasks.forEach(task => {
            const row = createTaskRow(task, 'running');
            runningTable.appendChild(row);
        });
    } else {
        runningEmpty.style.display = 'block';
    }
    
    // 更新已完成任务
    if (finishedTasks.length > 0) {
        finishedEmpty.style.display = 'none';
        finishedTasks.forEach(task => {
            const row = createTaskRow(task, 'finished');
            finishedTable.appendChild(row);
        });
    } else {
        finishedEmpty.style.display = 'block';
    }
}

function createTaskRow(task, type) {
    const row = document.createElement('tr');
    
    const progress = task.Progress || 0;
    const progressBar = `
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${progress}%"></div>
        </div>
        <span>${progress.toFixed(1)}%</span>
    `;
    
    const statusClass = {
        'Running': 'running',
        'Downloading': 'running',
        'Pending': 'pending',
        'Completed': 'completed',
        'Failed': 'failed',
        'Cancelled': 'failed'
    }[task.Status] || 'pending';
    
    const statusText = {
        'Running': '运行中',
        'Downloading': '下载中',
        'Pending': '等待中',
        'Completed': '已完成',
        'Failed': '失败',
        'Cancelled': '已取消'
    }[task.Status] || task.Status;
    
    if (type === 'running') {
        row.innerHTML = `
            <td>${task.AID || '-'}</td>
            <td class="task-title" title="${task.Title || ''}">${(task.Title || '未知标题').substring(0, 50)}${(task.Title || '').length > 50 ? '...' : ''}</td>
            <td>${formatTimestamp(task.CreatedAt)}</td>
            <td>${progressBar}</td>
            <td>${formatSpeed(task.Speed)}</td>
            <td>${formatBytes(task.Size || 0)}</td>
            <td><span class="status ${statusClass}">${statusText}</span></td>
            <td>
                <button class="btn btn-secondary" onclick="showTaskDetail('${task.AID}')" title="查看详情">
                    <span class="icon">👁️</span>
                </button>
                <button class="btn btn-danger" onclick="removeTask('${task.AID}')" title="移除任务">
                    <span class="icon">🗑️</span>
                </button>
            </td>
        `;
    } else {
        row.innerHTML = `
            <td>${task.AID || '-'}</td>
            <td class="task-title" title="${task.Title || ''}">${(task.Title || '未知标题').substring(0, 50)}${(task.Title || '').length > 50 ? '...' : ''}</td>
            <td>${formatTimestamp(task.CreatedAt)}</td>
            <td>${formatTimestamp(task.CompletedAt)}</td>
            <td>${progressBar}</td>
            <td>${formatBytes(task.Size || 0)}</td>
            <td><span class="status ${statusClass}">${statusText}</span></td>
            <td>
                <button class="btn btn-secondary" onclick="showTaskDetail('${task.AID}')" title="查看详情">
                    <span class="icon">👁️</span>
                </button>
                <button class="btn btn-danger" onclick="removeTask('${task.AID}')" title="移除任务">
                    <span class="icon">🗑️</span>
                </button>
            </td>
        `;
    }
    
    return row;
}

// 自动刷新功能
function startAutoRefresh() {
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    if (autoRefreshCheckbox.checked && isConnected) {
        refreshTimer = setInterval(refreshTasks, 10000); // 10秒刷新一次
    }
}

function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

// 收集表单选项
function collectOptions() {
    const options = {};
    
    // 基本选项
    if (document.getElementById('only-show-info').checked) options.onlyShowInfo = true;
    if (document.getElementById('show-all').checked) options.showAll = true;
    if (document.getElementById('interactive').checked) options.interactive = true;
    
    const area = document.getElementById('area-select').value;
    if (area) options.area = area;
    
    const language = document.getElementById('language-input').value.trim();
    if (language) options.language = language;
    
    const delay = parseInt(document.getElementById('delay-input').value);
    if (delay > 0) options.delay = delay;
    
    // API选项
    const apiType = document.querySelector('input[name="api-type"]:checked');
    if (apiType) {
        switch (apiType.value) {
            case 'tv': options.useTvApi = true; break;
            case 'app': options.useAppApi = true; break;
            case 'intl': options.useIntlApi = true; break;
        }
    }
    
    const tvHost = document.getElementById('tv-host-input').value.trim();
    if (tvHost) options.tvHost = tvHost;
    
    // 内容选择
    const contentType = document.querySelector('input[name="content-type"]:checked');
    if (contentType) {
        switch (contentType.value) {
            case 'video': options.videoOnly = true; break;
            case 'audio': options.audioOnly = true; break;
        }
    }
    
    if (document.getElementById('danmaku-only').checked) options.danmakuOnly = true;
    if (document.getElementById('cover-only').checked) options.coverOnly = true;
    if (document.getElementById('sub-only').checked) options.subOnly = true;
    if (document.getElementById('download-danmaku').checked) options.downloadDanmaku = true;
    
    const danmakuFormats = document.getElementById('danmaku-formats').value.trim();
    if (danmakuFormats) options.danmakuFormats = danmakuFormats;
    
    if (document.getElementById('skip-ai').checked) options.skipAi = true;
    
    // 下载控制
    if (document.getElementById('multi-thread').checked) options.multiThread = true;
    if (document.getElementById('use-mp4box').checked) options.useMp4box = true;
    if (document.getElementById('use-aria2c').checked) options.useAria2c = true;
    if (document.getElementById('simply-mux').checked) options.simplyMux = true;
    if (document.getElementById('skip-mux').checked) options.skipMux = true;
    if (document.getElementById('skip-subtitle').checked) options.skipSubtitle = true;
    if (document.getElementById('skip-cover').checked) options.skipCover = true;
    
    const encodingPriority = document.getElementById('encoding-priority').value.trim();
    if (encodingPriority) options.encodingPriority = encodingPriority;
    
    const dfnPriority = document.getElementById('dfn-priority').value.trim();
    if (dfnPriority) options.dfnPriority = dfnPriority;
    
    const selectPage = document.getElementById('select-page').value.trim();
    if (selectPage) options.selectPage = selectPage;
    
    // 文件命名
    const filePattern = document.getElementById('file-pattern').value.trim();
    if (filePattern) options.filePattern = filePattern;
    
    const multiFilePattern = document.getElementById('multi-file-pattern').value.trim();
    if (multiFilePattern) options.multiFilePattern = multiFilePattern;
    
    if (document.getElementById('add-dfn-subfix').checked) options.addDfnSubfix = true;
    if (document.getElementById('no-padding-page').checked) options.noPaddingPage = true;
    
    // 路径设置
    const workDir = document.getElementById('work-dir').value.trim();
    if (workDir) options.workDir = workDir;
    
    const ffmpegPath = document.getElementById('ffmpeg-path').value.trim();
    if (ffmpegPath) options.ffmpegPath = ffmpegPath;
    
    const mp4boxPath = document.getElementById('mp4box-path').value.trim();
    if (mp4boxPath) options.mp4boxPath = mp4boxPath;
    
    const aria2cPath = document.getElementById('aria2c-path').value.trim();
    if (aria2cPath) options.aria2cPath = aria2cPath;
    
    // 网络设置
    const userAgent = document.getElementById('user-agent').value.trim();
    if (userAgent) options.userAgent = userAgent;
    
    const cookie = document.getElementById('cookie').value.trim();
    if (cookie) options.cookie = cookie;
    
    const accessToken = document.getElementById('access-token').value.trim();
    if (accessToken) options.accessToken = accessToken;
    
    const hostNetwork = document.getElementById('host-input-network').value.trim();
    if (hostNetwork) options.host = hostNetwork;
    
    const epHost = document.getElementById('ep-host-input').value.trim();
    if (epHost) options.epHost = epHost;
    
    const uposHost = document.getElementById('upos-host').value.trim();
    if (uposHost) options.uposHost = uposHost;
    
    const aria2cArgs = document.getElementById('aria2c-args').value.trim();
    if (aria2cArgs) options.aria2cArgs = aria2cArgs;
    
    const aria2cProxy = document.getElementById('aria2c-proxy').value.trim();
    if (aria2cProxy) options.aria2cProxy = aria2cProxy;
    
    // 高级设置
    if (document.getElementById('debug').checked) options.debug = true;
    if (document.getElementById('force-http').checked) options.forceHttp = true;
    if (document.getElementById('allow-pcdn').checked) options.allowPcdn = true;
    if (document.getElementById('force-replace-host').checked) options.forceReplaceHost = true;
    if (document.getElementById('save-archives').checked) options.saveArchives = true;
    if (document.getElementById('video-asc').checked) options.videoAsc = true;
    if (document.getElementById('audio-asc').checked) options.audioAsc = true;
    if (document.getElementById('bandwidth-asc').checked) options.bandwidthAsc = true;
    
    // 兼容性选项
    const codecType = document.querySelector('input[name="codec-type"]:checked');
    if (codecType) {
        switch (codecType.value) {
            case 'hevc': options.onlyHevc = true; break;
            case 'avc': options.onlyAvc = true; break;
            case 'av1': options.onlyAv1 = true; break;
        }
    }
    
    return options;
}

// 添加任务
async function addTask() {
    const urlInput = document.getElementById('url-input');
    const url = urlInput.value.trim();
    
    if (!url) {
        showNotification('请输入视频URL', 'warning');
        return;
    }
    
    if (!isConnected || !apiClient) {
        showNotification('请先连接到服务器', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const options = collectOptions();
        const result = await apiClient.addTask(url, options);
        
        showNotification('任务添加成功！', 'success');
        urlInput.value = '';
        
        // 刷新任务列表
        await refreshTasks();
        
        // 切换到仪表盘
        const dashboardTab = document.querySelector('[data-tab="dashboard"]');
        dashboardTab.click();
        
    } catch (error) {
        showNotification(`添加任务失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 移除任务
async function removeTask(aid) {
    if (!isConnected || !apiClient) {
        showNotification('请先连接到服务器', 'warning');
        return;
    }
    
    if (!confirm(`确定要移除任务 ${aid} 吗？`)) {
        return;
    }
    
    showLoading(true);
    
    try {
        await apiClient.removeTask(aid);
        showNotification('任务移除成功！', 'success');
        await refreshTasks();
    } catch (error) {
        showNotification(`移除任务失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 批量移除任务
async function removeAllFinished() {
    if (!isConnected || !apiClient) {
        showNotification('请先连接到服务器', 'warning');
        return;
    }
    
    const finishedTasks = currentTasks.filter(task => 
        task.Status === 'Completed' || task.Status === 'Failed' || task.Status === 'Cancelled'
    );
    
    if (finishedTasks.length === 0) {
        showNotification('没有已完成的任务', 'info');
        return;
    }
    
    if (!confirm(`确定要移除所有 ${finishedTasks.length} 个已完成任务吗？`)) {
        return;
    }
    
    showLoading(true);
    
    try {
        for (const task of finishedTasks) {
            await apiClient.removeTask(task.AID);
        }
        showNotification(`成功移除 ${finishedTasks.length} 个任务！`, 'success');
        await refreshTasks();
    } catch (error) {
        showNotification(`批量移除失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

async function removeAllFailed() {
    if (!isConnected || !apiClient) {
        showNotification('请先连接到服务器', 'warning');
        return;
    }
    
    const failedTasks = currentTasks.filter(task => 
        task.Status === 'Failed' || task.Status === 'Cancelled'
    );
    
    if (failedTasks.length === 0) {
        showNotification('没有失败的任务', 'info');
        return;
    }
    
    if (!confirm(`确定要移除所有 ${failedTasks.length} 个失败任务吗？`)) {
        return;
    }
    
    showLoading(true);
    
    try {
        for (const task of failedTasks) {
            await apiClient.removeTask(task.AID);
        }
        showNotification(`成功移除 ${failedTasks.length} 个失败任务！`, 'success');
        await refreshTasks();
    } catch (error) {
        showNotification(`批量移除失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

async function removeByAid() {
    const aidInput = document.getElementById('aid-input');
    const aid = aidInput.value.trim();
    
    if (!aid) {
        showNotification('请输入要移除的任务AID', 'warning');
        return;
    }
    
    await removeTask(aid);
    aidInput.value = '';
}

// 显示任务详情
async function showTaskDetail(aid) {
    if (!isConnected || !apiClient) {
        showNotification('请先连接到服务器', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const task = await apiClient.getTaskDetail(aid);
        displayTaskDetail(task);
    } catch (error) {
        showNotification(`获取任务详情失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

function displayTaskDetail(task) {
    const modal = document.getElementById('task-detail-modal');
    const content = document.getElementById('task-detail-content');
    
    const progress = task.Progress || 0;
    const statusClass = {
        'Running': 'running',
        'Downloading': 'running',
        'Pending': 'pending',
        'Completed': 'completed',
        'Failed': 'failed',
        'Cancelled': 'failed'
    }[task.Status] || 'pending';
    
    const statusText = {
        'Running': '运行中',
        'Downloading': '下载中',
        'Pending': '等待中',
        'Completed': '已完成',
        'Failed': '失败',
        'Cancelled': '已取消'
    }[task.Status] || task.Status;
    
    content.innerHTML = `
        <div class="task-detail">
            <div class="detail-row">
                <strong>AID:</strong> ${task.AID || '-'}
            </div>
            <div class="detail-row">
                <strong>标题:</strong> ${task.Title || '未知标题'}
            </div>
            <div class="detail-row">
                <strong>URL:</strong> <a href="${task.Url || '#'}" target="_blank">${task.Url || '-'}</a>
            </div>
            <div class="detail-row">
                <strong>状态:</strong> <span class="status ${statusClass}">${statusText}</span>
            </div>
            <div class="detail-row">
                <strong>进度:</strong> 
                <div class="progress-bar" style="width: 200px; margin-left: 10px;">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <span style="margin-left: 10px;">${progress.toFixed(1)}%</span>
            </div>
            <div class="detail-row">
                <strong>下载速度:</strong> ${formatSpeed(task.Speed)}
            </div>
            <div class="detail-row">
                <strong>文件大小:</strong> ${formatBytes(task.Size || 0)}
            </div>
            <div class="detail-row">
                <strong>创建时间:</strong> ${formatTimestamp(task.CreatedAt)}
            </div>
            <div class="detail-row">
                <strong>完成时间:</strong> ${formatTimestamp(task.CompletedAt)}
            </div>
            ${task.ErrorMessage ? `
                <div class="detail-row">
                    <strong>错误信息:</strong> 
                    <div style="background: #ffebee; padding: 10px; border-radius: 4px; margin-top: 5px; color: #c62828;">
                        ${task.ErrorMessage}
                    </div>
                </div>
            ` : ''}
            ${task.OutputPath ? `
                <div class="detail-row">
                    <strong>输出路径:</strong> ${task.OutputPath}
                </div>
            ` : ''}
        </div>
    `;
    
    modal.classList.add('show');
}

// 模态框功能
function initModal() {
    const modal = document.getElementById('task-detail-modal');
    const closeButtons = modal.querySelectorAll('.modal-close');
    
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modal.classList.remove('show');
        });
    });
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
}

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化各种功能
    initTabs();
    initCollapsibleGroups();
    initModal();
    
    // 绑定事件
    document.getElementById('connect-btn').addEventListener('click', connectToServer);
    document.getElementById('refresh-btn').addEventListener('click', refreshTasks);
    document.getElementById('add-task-btn').addEventListener('click', addTask);
    document.getElementById('remove-all-btn').addEventListener('click', removeAllFinished);
    document.getElementById('remove-failed-btn').addEventListener('click', removeAllFailed);
    document.getElementById('remove-by-aid-btn').addEventListener('click', removeByAid);
    
    // 自动刷新复选框事件
    document.getElementById('auto-refresh').addEventListener('change', (e) => {
        if (e.target.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
    
    // 回车键提交
    document.getElementById('url-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            addTask();
        }
    });
    
    document.getElementById('aid-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            removeByAid();
        }
    });
    
    // 连接输入框回车
    document.getElementById('host-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            connectToServer();
        }
    });
    
    document.getElementById('port-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            connectToServer();
        }
    });
    
    // 初始化连接状态
    updateConnectionStatus(false);
    
    console.log('BBDown任务管理器已初始化');
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .detail-row {
        margin-bottom: 15px;
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }
    
    .detail-row strong {
        min-width: 80px;
        color: #495057;
    }
    
    .detail-row a {
        color: #667eea;
        text-decoration: none;
        word-break: break-all;
    }
    
    .detail-row a:hover {
        text-decoration: underline;
    }
`;
document.head.appendChild(style);