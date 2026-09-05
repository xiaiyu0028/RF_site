// RF 攻略網站 - 共用 JavaScript

// 深色模式功能
function initTheme() {
    // 檢查本地存儲的主題偏好
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else if (prefersDark) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
    
    // 創建切換按鈕
    createThemeToggle();
}

function createThemeToggle() {
    if (document.querySelector('.theme-toggle')) return;
    const toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.setAttribute('aria-label', '切換深色模式');
    toggle.setAttribute('aria-pressed', String(document.documentElement.getAttribute('data-theme') === 'dark'));
    toggle.innerHTML = getThemeIcon();
    toggle.onclick = toggleTheme;
    document.body.appendChild(toggle);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // 更新按鈕圖標
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
        toggle.innerHTML = getThemeIcon();
        toggle.setAttribute('aria-pressed', String(newTheme === 'dark'));
    }
}

function getThemeIcon() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return isDark
        ? '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"></path></svg>'
        : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.7 6.7 0 0 0 21 12.8Z"></path></svg>';
}

// 頁面載入時初始化主題
document.addEventListener('DOMContentLoaded', initTheme);

// 導航欄切換
function toggleMenu() {
    const menu = document.getElementById('navMenu');
    const toggle = document.querySelector('.navbar-toggle');
    if (menu) {
        menu.classList.toggle('active');
        toggle?.setAttribute('aria-expanded', String(menu.classList.contains('active')));
    }
}

// 關閉導航欄（點擊其他地方時）
document.addEventListener('click', function(e) {
    const navbar = document.querySelector('.navbar');
    const menu = document.getElementById('navMenu');
    if (navbar && menu && !navbar.contains(e.target)) {
        menu.classList.remove('active');
        document.querySelector('.navbar-toggle')?.setAttribute('aria-expanded', 'false');
        closeNavGroups();
    }
});

function closeNavGroups(except) {
    document.querySelectorAll('.nav-group-toggle').forEach(button => {
        if (button !== except) button.setAttribute('aria-expanded', 'false');
    });
}

function upgradeNavigation() {
    const navbar = document.querySelector('.navbar');
    const menu = document.getElementById('navMenu');
    const brand = document.querySelector('.navbar-brand');
    const toggle = document.querySelector('.navbar-toggle');
    const content = document.querySelector('.content-wrapper');
    if (!navbar || !menu || !brand || !toggle) return;

    const inPagesDirectory = /\/pages\//.test(window.location.pathname);
    const pagePrefix = inPagesDirectory ? '' : 'pages/';
    const homeHref = inPagesDirectory ? '../index.html' : 'index.html';
    const pageName = window.location.pathname.split('/').pop() || 'index.html';
    const isActive = filename => pageName === filename || (pageName === '' && filename === 'index.html');
    const link = (href, label, filename) => `<a href="${href}"${isActive(filename) ? ' class="active" aria-current="page"' : ''}>${label}</a>`;
    const group = (id, label, links) => {
        const active = links.some(item => isActive(item.filename));
        return `<li class="nav-group"><button type="button" class="nav-group-toggle${active ? ' active' : ''}" aria-expanded="false" aria-controls="${id}">${label}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"></path></svg></button><div class="nav-popover" id="${id}">${links.map(item => link(item.href, item.label, item.filename)).join('')}</div></li>`;
    };

    brand.innerHTML = '<span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3 4.5 6v5.5c0 4.7 3.2 7.8 7.5 9.5 4.3-1.7 7.5-4.8 7.5-9.5V6L12 3Z"></path><path d="M8.5 12h7M12 8.5v7"></path></svg></span><span>RF 攻略網站</span>';
    menu.innerHTML = [
        `<li>${link(homeHref, '首頁', 'index.html')}</li>`,
        group('database-menu', '資料庫', [
            { href: `${pagePrefix}characters.html`, label: '角色資料', filename: 'characters.html' },
            { href: `${pagePrefix}cities.html`, label: '城鎮資料', filename: 'cities.html' },
            { href: `${pagePrefix}nations.html`, label: '國策資訊', filename: 'nations.html' }
        ]),
        group('calculator-menu', '計算工具', [
            { href: `${pagePrefix}calculator.html`, label: '戰力計算', filename: 'calculator.html' },
            { href: `${pagePrefix}calculator_nation.html`, label: '國策戰力', filename: 'calculator_nation.html' }
        ]),
        `<li>${link(`${pagePrefix}guide.html`, '新手教學', 'guide.html')}</li>`,
        `<li>${link(`${pagePrefix}query.html`, '帳號查詢', 'query.html')}</li>`
    ].join('');

    toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"></path></svg>';
    toggle.setAttribute('aria-label', '開啟導覽選單');
    toggle.setAttribute('aria-controls', 'navMenu');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.onclick = toggleMenu;
    menu.querySelectorAll('.nav-group-toggle').forEach(button => {
        button.addEventListener('click', () => {
            const willOpen = button.getAttribute('aria-expanded') !== 'true';
            closeNavGroups(button);
            button.setAttribute('aria-expanded', String(willOpen));
        });
    });
    if (content) content.id = 'main-content';
    const skip = document.createElement('a');
    skip.className = 'skip-link';
    skip.href = '#main-content';
    skip.textContent = '跳至主要內容';
    navbar.before(skip);
    document.querySelectorAll('.page-header h1').forEach(heading => {
        heading.textContent = heading.textContent.replace(/^[\p{Extended_Pictographic}\s]+/u, '');
    });
}

document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    closeNavGroups();
    const menu = document.getElementById('navMenu');
    if (menu?.classList.contains('active')) toggleMenu();
});

// 分頁切換功能
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabGroup = this.closest('.tabs-container');
            const targetId = this.getAttribute('data-tab');
            
            // 移除所有 active 狀態
            tabGroup.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            tabGroup.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // 啟用目標 tab
            this.classList.add('active');
            const targetContent = tabGroup.querySelector(`#${targetId}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
}

// 摺疊面板功能
function initAccordion() {
    const headers = document.querySelectorAll('.accordion-header');
    headers.forEach(header => {
        header.addEventListener('click', function() {
            const body = this.nextElementSibling;
            const isActive = this.classList.contains('active');
            
            // 關閉其他面板（可選）
            // this.closest('.accordion').querySelectorAll('.accordion-header').forEach(h => {
            //     h.classList.remove('active');
            //     h.nextElementSibling.classList.remove('active');
            // });
            
            if (isActive) {
                this.classList.remove('active');
                body.classList.remove('active');
            } else {
                this.classList.add('active');
                body.classList.add('active');
            }
        });
    });
}

// 搜尋過濾功能
function initSearch(inputId, itemSelector, textSelector) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    input.addEventListener('input', function() {
        const searchText = this.value.toLowerCase().trim();
        const items = document.querySelectorAll(itemSelector);
        
        items.forEach(item => {
            const text = item.querySelector(textSelector)?.textContent.toLowerCase() || 
                         item.textContent.toLowerCase();
            if (text.includes(searchText)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

// 通用的 API 請求函數
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API 請求失敗:', error);
        throw error;
    }
}

// 載入 JSON 資料
async function loadJSON(path) {
    try {
        const response = await fetch(path);
        if (!response.ok) {
            throw new Error(`無法載入 ${path}`);
        }
        return await response.json();
    } catch (error) {
        console.error('載入 JSON 失敗:', error);
        return null;
    }
}

// HTML 逸出（避免資料內的角括號破壞版面）
function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// 圖片路徑轉換（將遊戲 API 路徑轉為本地路徑）
// /images/... -> ../passionfruit/images/... (從 pages/ 目錄存取)
// /audio/... -> ../passionfruit/audio/...
function getAssetPath(originalPath) {
    if (!originalPath) return '';
    
    // 如果已經是正確的相對路徑，直接返回
    if (originalPath.startsWith('../passionfruit/') || originalPath.startsWith('./passionfruit/')) {
        return originalPath;
    }
    
    // 轉換 /images/, /audio/, /video/ 開頭的路徑
    if (originalPath.startsWith('/images/')) {
        return '../passionfruit' + originalPath;
    }
    if (originalPath.startsWith('/audio/')) {
        return '../passionfruit' + originalPath;
    }
    if (originalPath.startsWith('/video/')) {
        return '../passionfruit' + originalPath;
    }
    
    // 其他情況直接返回原始路徑
    return originalPath;
}

// 從根目錄存取的圖片路徑（用於 index.html）
function getAssetPathFromRoot(originalPath) {
    if (!originalPath) return '';
    
    if (originalPath.startsWith('/images/')) {
        return 'passionfruit' + originalPath;
    }
    if (originalPath.startsWith('/audio/')) {
        return 'passionfruit' + originalPath;
    }
    if (originalPath.startsWith('/video/')) {
        return 'passionfruit' + originalPath;
    }
    
    return originalPath;
}

// 顯示載入中
function showLoading(container) {
    if (typeof container === 'string') {
        container = document.getElementById(container);
    }
    if (container) {
        container.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <p style="margin-top: 15px;">載入中...</p>
            </div>
        `;
    }
}

// 顯示錯誤訊息
function showError(container, message) {
    if (typeof container === 'string') {
        container = document.getElementById(container);
    }
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <strong>錯誤：</strong> ${message}
            </div>
        `;
    }
}

// 顯示空資料訊息
function showEmpty(container, message = '沒有找到資料') {
    if (typeof container === 'string') {
        container = document.getElementById(container);
    }
    if (container) {
        container.innerHTML = `
            <div class="alert alert-info">
                ${message}
            </div>
        `;
    }
}

// 格式化數字
function formatNumber(num) {
    return num?.toLocaleString() || '0';
}

// 格式化百分比
function formatPercent(num) {
    return `${(num * 100).toFixed(1)}%`;
}

// 取得稀有度 CSS class
function getScarcityClass(scarcity) {
    switch (scarcity) {
        case 'R': return 'scarcity-R';
        case 'SR': return 'scarcity-SR';
        case 'SSR': return 'scarcity-SSR';
        default: return '';
    }
}

// 取得職業名稱
function getRoleName(role) {
    const roles = {
        'agitator': '宣傳家',
        'sponsor': '資助者',
        'spy': '間諜',
        'guerrilla': '游擊隊'
    };
    return roles[role] || role;
}

// 取得陣營名稱
function getNationName(nationId) {
    const nations = {
        1: '紅軍',
        2: '臺灣',
        3: '香港',
        4: '藏國',
        5: '維吾爾',
        6: '哈薩克',
        7: '滿洲',
        8: '蒙古',
        9: '自由勢力',
        10: '反賊聯盟'
    };
    return nations[nationId] || '未知';
}

// 取得陣營顏色 class
function getNationClass(nationId) {
    const classes = {
        1: 'faction-red',
        2: 'faction-taiwan',
        3: 'faction-hongkong',
        4: 'faction-tibet',
        5: 'faction-uyghur',
        6: 'faction-kazakh',
        7: 'faction-manchuria',
        8: 'faction-mongolia',
        9: 'faction-free',
        10: 'faction-rebel'
    };
    return classes[nationId] || '';
}

// 解析 Markdown（簡易版本）
function parseMarkdown(markdown) {
    if (!markdown) return '';
    
    let html = markdown
        // Headers
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Code blocks
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        // Inline code
        .replace(/`(.*?)`/g, '<code>$1</code>')
        // Links
        .replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Lists
        .replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>')
        // Blockquotes
        .replace(/^>\s+(.*$)/gim, '<blockquote>$1</blockquote>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    
    // Wrap list items
    html = html.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');
    // Clean up multiple ul tags
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    
    return `<p>${html}</p>`;
}

// 本地儲存工具
const storage = {
    get(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            return defaultValue;
        }
    },
    
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            return false;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            return false;
        }
    }
};

// 產生唯一 ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// 防抖函數
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 節流函數
function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 複製到剪貼簿
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (e) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        return true;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    upgradeNavigation();
    initTabs();
    initAccordion();
});
