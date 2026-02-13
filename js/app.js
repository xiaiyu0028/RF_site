// RF 攻略網站 - 共用 JavaScript

// 導航欄切換
function toggleMenu() {
    const menu = document.getElementById('navMenu');
    if (menu) {
        menu.classList.toggle('active');
    }
}

// 關閉導航欄（點擊其他地方時）
document.addEventListener('click', function(e) {
    const navbar = document.querySelector('.navbar');
    const menu = document.getElementById('navMenu');
    if (navbar && menu && !navbar.contains(e.target)) {
        menu.classList.remove('active');
    }
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
    initTabs();
    initAccordion();
});
