/**
 * Ledger Scrolls v2.0 - Main Application
 * 
 * "A Library That Cannot Burn"
 * 
 * A viewer for immutable documents stored on the Cardano blockchain.
 */

// --- Binary rendering helpers (MP4, images, PDFs, etc.) ---
let _activeObjectUrl = null;
function revokeActiveObjectUrl() {
    if (_activeObjectUrl) {
        URL.revokeObjectURL(_activeObjectUrl);
        _activeObjectUrl = null;
    }
}
function makeObjectUrl(bytes, contentType) {
    const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    const blob = new Blob([u8], { type: contentType || "application/octet-stream" });
    revokeActiveObjectUrl();
    _activeObjectUrl = URL.createObjectURL(blob);
    return { blob, url: _activeObjectUrl };
}
function guessFileExtension(contentType) {
    const ct = (contentType || "").toLowerCase();
    if (ct.includes("video/mp4")) return "mp4";
    if (ct.includes("image/png")) return "png";
    if (ct.includes("image/jpeg")) return "jpg";
    if (ct.includes("application/pdf")) return "pdf";
    if (ct.includes("text/html")) return "html";
    if (ct.includes("text/plain")) return "txt";
    return "bin";
}
function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "download";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}
function renderScrollBytesIntoViewer({ bytes, contentType, filename }, viewerContentEl) {
    const ct = (contentType || "application/octet-stream").toLowerCase();
    const ext = guessFileExtension(ct);
    const finalName = filename || `ledger_scroll.${ext}`;
    const { blob, url } = makeObjectUrl(bytes, ct);

    viewerContentEl.innerHTML = "";

    if (ct.startsWith("video/") || ct.includes("video/mp4")) {
        const wrap = document.createElement("div");
        wrap.className = "video-wrap";
        const vid = document.createElement("video");
        vid.controls = true;
        vid.playsInline = true;
        vid.preload = "metadata";
        vid.src = url;
        vid.style.width = "100%";
        vid.style.maxHeight = "70vh";
        vid.style.borderRadius = "12px";
        wrap.appendChild(vid);
        viewerContentEl.appendChild(wrap);
        return { blob, url, filename: finalName, kind: "video" };
    }

    if (ct.startsWith("image/")) {
        const img = document.createElement("img");
        img.src = url;
        img.alt = finalName;
        img.style.maxWidth = "100%";
        img.style.borderRadius = "12px";
        viewerContentEl.appendChild(img);
        return { blob, url, filename: finalName, kind: "image" };
    }

    if (ct.includes("application/pdf")) {
        const iframe = document.createElement("iframe");
        iframe.src = url;
        iframe.style.width = "100%";
        iframe.style.height = "70vh";
        iframe.style.border = "0";
        iframe.style.borderRadius = "12px";
        viewerContentEl.appendChild(iframe);
        return { blob, url, filename: finalName, kind: "pdf" };
    }

    if (ct.startsWith("text/") || ct.includes("application/json")) {
        const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
        const text = new TextDecoder("utf-8", { fatal: false }).decode(u8);
        if (ct.includes("text/html")) {
            const iframe = document.createElement("iframe");
            iframe.setAttribute("sandbox", "allow-same-origin");
            iframe.style.width = "100%";
            iframe.style.height = "70vh";
            iframe.style.border = "0";
            iframe.style.borderRadius = "12px";
            viewerContentEl.appendChild(iframe);
            const doc = iframe.contentDocument;
            doc.open();
            doc.write(text);
            doc.close();
            return { blob, url, filename: finalName, kind: "html" };
        }
        const pre = document.createElement("pre");
        pre.textContent = text.length > 50000 ? text.substring(0, 50000) + "\n\n... (truncated)" : text;
        pre.style.whiteSpace = "pre-wrap";
        viewerContentEl.appendChild(pre);
        return { blob, url, filename: finalName, kind: "text" };
    }

    const p = document.createElement("p");
    p.textContent = `Binary content (${ct}). Use Download.`;
    viewerContentEl.appendChild(p);
    return { blob, url, filename: finalName, kind: "binary" };
}

class LedgerScrollsApp {
    constructor() {
        // State
        this.client = null;
        this.reconstructor = null;
        this.connected = false;
        this.currentScroll = null;
        this.currentCategory = 'all';
        this.loadedContent = null;
        this._currentBlobUrl = null;

        // Settings
        this.settings = this._loadSettings();

        // Initialize
        this._initializeUI();
        this._bindEvents();
        this._initParticles();
        this._applyTheme(this.settings.theme);
        this._renderScrollLibrary();

        // Auto-connect if we have an API key
        if (this.settings.apiKey || this.settings.mode === 'koios') {
            this._connect();
        }

        this._log('info', 'Ledger Scrolls v2.0 initialized. Welcome to the eternal library.');
    }

    // =========================================================================
    // Settings Management
    // =========================================================================

    _loadSettings() {
        try {
            const saved = localStorage.getItem('ledgerScrollsSettings');
            const fallback = {
                mode: window.LS_DEFAULT_MODE || 'blockfrost',
                apiKey: '',
                koiosProxy: '',
                theme: 'dark'
            };
            const settings = saved ? JSON.parse(saved) : fallback;
            if (typeof settings.koiosProxy === 'undefined') {
                settings.koiosProxy = '';
            }
            if (window.LS_OVERRIDE_MODE) {
                settings.mode = window.LS_OVERRIDE_MODE;
            }
            return settings;
        } catch {
            return { mode: window.LS_DEFAULT_MODE || 'blockfrost', apiKey: '', koiosProxy: '', theme: 'dark' };
        }
    }

    _saveSettings() {
        localStorage.setItem('ledgerScrollsSettings', JSON.stringify(this.settings));
    }

    // =========================================================================
    // UI Initialization
    // =========================================================================

    _initializeUI() {
        this.elements = {
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            connectBtn: document.getElementById('connectBtn'),
            scrollGrid: document.getElementById('scrollGrid'),
            scrollCategories: document.getElementById('scrollCategories'),
            searchInput: document.getElementById('searchScrolls'),
            viewerPanel: document.getElementById('viewerPanel'),
            viewerTitle: document.getElementById('viewerTitle'),
            viewerLoading: document.getElementById('viewerLoading'),
            viewerContent: document.getElementById('viewerContent'),
            loadingText: document.getElementById('loadingText'),
            progressBar: document.getElementById('progressBar'),
            progressFill: document.getElementById('progressFill'),
            scrollMetadata: document.getElementById('scrollMetadata'),
            downloadBtn: document.getElementById('downloadBtn'),
            verifyBtn: document.getElementById('verifyBtn'),
            logEntries: document.getElementById('logEntries'),
            activityLog: document.getElementById('activityLog'),
            settingsModal: document.getElementById('settingsModal'),
            aboutModal: document.getElementById('aboutModal'),
            verifyModal: document.getElementById('verifyModal'),
            customScrollModal: document.getElementById('customScrollModal'),
            apiKeyInput: document.getElementById('apiKeyInput'),
            koiosProxyInput: document.getElementById('koiosProxyInput'),
            koiosProxyStatus: document.getElementById('koiosProxyStatus'),
            modeRadios: document.querySelectorAll('input[name="connectionMode"]'),
            themeBtns: document.querySelectorAll('.theme-btn'),
            toastContainer: document.getElementById('toastContainer')
        };

        if (this.settings.apiKey) {
            this.elements.apiKeyInput.value = this.settings.apiKey;
        }
        if (this.elements.koiosProxyInput) {
            this.elements.koiosProxyInput.value = this.settings.koiosProxy || '';
        }
        if (this.elements.koiosProxyStatus) {
            this.elements.koiosProxyStatus.textContent = `Current: ${this.settings.koiosProxy || '(none)'}`;
        }
    }

    _bindEvents() {
        document.getElementById('settingsBtn').addEventListener('click', () => this._openModal('settingsModal'));
        document.getElementById('infoBtn').addEventListener('click', () => this._openModal('aboutModal'));
        this.elements.connectBtn.addEventListener('click', () => this._connect());
        this.elements.searchInput.addEventListener('input', (e) => this._onSearch(e.target.value));
        document.getElementById('refreshLibrary').addEventListener('click', () => this._renderScrollLibrary());
        this.elements.downloadBtn.addEventListener('click', () => this._downloadCurrentScroll());
        this.elements.verifyBtn.addEventListener('click', () => this._verifyCurrentScroll());
        document.getElementById('closeViewerBtn').addEventListener('click', () => this._closeViewer());
        document.getElementById('logToggle').addEventListener('click', () => {
            this.elements.activityLog.classList.toggle('collapsed');
        });
        document.getElementById('clearLogBtn').addEventListener('click', () => this._clearLog());

        document.querySelectorAll('.modal-backdrop, .modal-close').forEach(el => {
            el.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this._closeModal(modal.id);
            });
        });

        document.getElementById('saveApiKey').addEventListener('click', () => this._saveApiKey());
        document.getElementById('saveKoiosProxy')?.addEventListener('click', () => this._saveKoiosProxy());

        this.elements.modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this._onModeChange(e.target.value));
        });

        this.elements.themeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const theme = btn.dataset.theme;
                this._applyTheme(theme);
                this.settings.theme = theme;
                this._saveSettings();
            });
        });

        document.querySelector('[data-tab="standard"]')?.addEventListener('click', () => this._switchTab('standard'));
        document.querySelector('[data-tab="legacy"]')?.addEventListener('click', () => this._switchTab('legacy'));
        document.getElementById('loadCustomScroll')?.addEventListener('click', () => this._loadCustomScroll());

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal.active').forEach(m => this._closeModal(m.id));
            }
        });
    }

    _initParticles() {
        const container = document.getElementById('particles');
        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.animationDelay = `${Math.random() * 15}s`;
            particle.style.animationDuration = `${15 + Math.random() * 10}s`;
            container.appendChild(particle);
        }
    }

    // =========================================================================
    // Connection Management
    // =========================================================================

    async _connect() {
        const mode = this.settings.mode;
        const apiKey = this.settings.apiKey;

        if (mode.startsWith('blockfrost') && !apiKey) {
            this._toast('error', 'Please enter a Blockfrost API key in Settings');
            this._openModal('settingsModal');
            return;
        }

        this._setConnectionStatus('connecting', 'Connecting...');
        this._log('info', `Connecting to Cardano via ${mode}...`);
        if (mode === 'koios') {
            this._log('info', `Koios proxy: ${this.settings.koiosProxy || '(none)'}`);
        }

        try {
            this.client = new BlockchainClient(mode, apiKey, this.settings.koiosProxy);
            if (!window.ScrollReconstructor) {
                await this._loadScript(`js/reconstruct.js?cb=${Date.now()}`);
            }
            if (!window.ScrollReconstructor) {
                throw new Error('ScrollReconstructor missing (reconstruct.js failed to load)');
            }
            this.reconstructor = new ScrollReconstructor(this.client);

            const result = await this.client.testConnection();
            
            if (result.success) {
                this.connected = true;
                this._setConnectionStatus('connected', `Connected (${mode})`);
                this._log('success', `Successfully connected to Cardano blockchain`);
                this._toast('success', 'Connected to Cardano blockchain!');
                
                const tip = await this.client.getTip();
                if (tip) {
                    const slot = tip.slot || tip.abs_slot;
                    const epoch = tip.epoch || tip.epoch_no;
                    this._log('info', `Chain tip: Epoch ${epoch}, Slot ${slot}`);
                }
            } else {
                throw new Error(result.error || 'Connection failed');
            }
        } catch (e) {
            this.connected = false;
            this._setConnectionStatus('disconnected', 'Connection failed');
            this._log('error', `Connection failed: ${e.message}`, this._formatErrorDetails(e));
            this._toast('error', `Connection failed: ${e.message}`);
        }
    }

    _setConnectionStatus(status, text) {
        this.elements.statusDot.className = `status-dot ${status}`;
        this.elements.statusText.textContent = text;
        this.elements.connectBtn.textContent = status === 'connected' ? 'Reconnect' : 'Connect to Cardano';
    }

    // =========================================================================
    // Library Rendering
    // =========================================================================

    _renderScrollLibrary() {
        const categories = ScrollLibrary.getCategoriesWithCounts();
        this.elements.scrollCategories.innerHTML = categories.map(cat => `
            <button class="category-btn ${cat.id === this.currentCategory ? 'active' : ''}" 
                    data-category="${cat.id}">
                ${cat.icon} ${cat.name} (${cat.count})
            </button>
        `).join('');

        this.elements.scrollCategories.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentCategory = btn.dataset.category;
                this._renderScrollLibrary();
            });
        });

        const scrolls = ScrollLibrary.getScrollsByCategory(this.currentCategory);
        this._renderScrollGrid(scrolls);
    }

    _renderScrollGrid(scrolls) {
        this.elements.scrollGrid.innerHTML = scrolls.map(scroll => `
            <div class="scroll-card" data-scroll-id="${scroll.id}">
                <div class="scroll-card-icon">${scroll.icon}</div>
                <div class="scroll-card-title">${scroll.title}</div>
                <div class="scroll-card-meta">${scroll.metadata?.size || 'Unknown'}</div>
                <div class="scroll-card-type">${
                    scroll.type === ScrollLibrary.SCROLL_TYPES.STANDARD ? 'Standard' : 'Legacy'
                }</div>
            </div>
        `).join('');

        this.elements.scrollGrid.querySelectorAll('.scroll-card').forEach(card => {
            card.addEventListener('click', () => {
                const scrollId = card.dataset.scrollId;
                const scroll = ScrollLibrary.getScrollById(scrollId);
                if (scroll) this._loadScroll(scroll);
            });
        });
    }

    _onSearch(query) {
        const scrolls = ScrollLibrary.searchScrolls(query);
        this._renderScrollGrid(scrolls);
    }

    // =========================================================================
    // Scroll Loading & Display
    // =========================================================================

    async _loadScroll(scroll) {
        if (!this.connected) {
            this._toast('warning', 'Please connect to Cardano first');
            return;
        }

        this.currentScroll = scroll;
        this.loadedContent = null;

        this.elements.viewerTitle.textContent = `📖 ${scroll.title}`;
        this.elements.viewerContent.classList.remove('active');
        this.elements.viewerContent.innerHTML = '';
        this.elements.scrollMetadata.classList.remove('active');
        this.elements.viewerLoading.classList.remove('hidden');
        this.elements.progressBar.classList.add('active');
        this.elements.progressFill.style.width = '0%';
        this.elements.downloadBtn.disabled = true;
        this.elements.verifyBtn.disabled = true;

        this._log('info', `Loading scroll: ${scroll.title}`);

        this.reconstructor.setProgressCallback((message, percent) => {
            this.elements.loadingText.textContent = message;
            if (percent !== null) {
                this.elements.progressFill.style.width = `${percent}%`;
            }
            this._log('info', message);
        });

        try {
            const result = await this.reconstructor.reconstruct(scroll);
            this.loadedContent = result;
            this._displayContent(result, scroll);
            this._displayMetadata(result, scroll);
            this.elements.downloadBtn.disabled = false;
            this.elements.verifyBtn.disabled = false;
            this._log('success', `Successfully loaded ${scroll.title} (${this._formatSize(result.size)})`);
            this._toast('success', `${scroll.title} loaded successfully!`);
        } catch (e) {
            this._log('error', `Failed to load scroll: ${e.message}`, this._formatErrorDetails(e));
            this._toast('error', `Failed to load: ${e.message}`);
            this.elements.loadingText.textContent = `❌ Error: ${e.message}`;
        } finally {
            this.elements.progressBar.classList.remove('active');
        }
    }

    _displayContent(result, scroll) {
        revokeActiveObjectUrl();

        this.elements.viewerLoading.classList.add('hidden');
        this.elements.viewerContent.classList.add('active');

        const contentType = result.contentType.split(';')[0].trim();
        const filename = scroll.file_name || scroll.id || scroll.title;

        window.__LS_OPEN = renderScrollBytesIntoViewer(
            { bytes: result.data, contentType, filename },
            this.elements.viewerContent
        );
    }

    _displayMetadata(result, scroll) {
        this.elements.scrollMetadata.classList.add('active');
        
        const metadata = {
            'Content Type': result.contentType,
            'Size': this._formatSize(result.size),
            'SHA-256': result.hash,
            'Method': result.method,
            ...(result.pages && { 'Pages': result.pages }),
            ...(scroll.pointer.lock_txin && { 'Lock TxIn': scroll.pointer.lock_txin }),
            ...(scroll.pointer.policy_id && { 'Policy ID': scroll.pointer.policy_id })
        };

        this.elements.scrollMetadata.innerHTML = `
            <div class="metadata-grid">
                ${Object.entries(metadata).map(([label, value]) => `
                    <div class="metadata-item">
                        <span class="metadata-label">${label}</span>
                        <span class="metadata-value ${label === 'SHA-256' ? 'hash' : ''}">${value}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    _closeViewer() {
        revokeActiveObjectUrl();
        window.__LS_OPEN = null;

        this.currentScroll = null;
        this.loadedContent = null;
        this.elements.viewerTitle.textContent = '📖 Select a Scroll';
        this.elements.viewerContent.classList.remove('active');
        this.elements.viewerContent.innerHTML = '';
        this.elements.scrollMetadata.classList.remove('active');
        this.elements.viewerLoading.classList.remove('hidden');
        this.elements.loadingText.textContent = 'Ready to explore the eternal library...';
        this.elements.progressBar.classList.remove('active');
        this.elements.downloadBtn.disabled = true;
        this.elements.verifyBtn.disabled = true;
    }

    // =========================================================================
    // Download & Verification
    // =========================================================================

    _downloadCurrentScroll() {
        const open = window.__LS_OPEN;
        if (open?.blob) {
            downloadBlob(open.blob, open.filename);
            this._log('info', `Downloaded: ${open.filename}`);
            this._toast('success', `Downloaded ${open.filename}`);
            return;
        }
        if (!this.loadedContent || !this.currentScroll) return;

        const contentType = this.loadedContent.contentType.split(';')[0].trim();
        const extension = this._getExtension(contentType);
        const filename = `${this.currentScroll.title.replace(/[^a-z0-9]/gi, '_')}${extension}`;

        const blob = new Blob([this.loadedContent.data], { type: contentType });
        downloadBlob(blob, filename);
        this._log('info', `Downloaded: ${filename}`);
        this._toast('success', `Downloaded ${filename}`);
    }

    _verifyCurrentScroll() {
        if (!this.loadedContent || !this.currentScroll) return;

        const expected = this.currentScroll.pointer?.sha256 || 
                        this.currentScroll.pointer?.sha256_original;
        const computed = this.loadedContent.hash;
        const noHash = !expected;
        const verified = !noHash && expected.toLowerCase() === computed.toLowerCase();

        const resultDiv = document.getElementById('verificationResult');
        resultDiv.innerHTML = `
            <div class="verification-icon">${noHash ? '⚠️' : (verified ? '✅' : '❌')}</div>
            <div class="verification-status ${noHash ? 'no-hash' : (verified ? 'verified' : 'failed')}">
                ${noHash ? 'NO EXPECTED HASH' : (verified ? 'VERIFIED' : 'VERIFICATION FAILED')}
            </div>
            <div class="hash-comparison">
                ${expected ? `
                    <div class="hash-row">
                        <span class="hash-label">Expected Hash</span>
                        <span class="hash-value">${expected}</span>
                    </div>
                ` : ''}
                <div class="hash-row">
                    <span class="hash-label">Computed Hash</span>
                    <span class="hash-value">${computed}</span>
                </div>
            </div>
        `;

        this._openModal('verifyModal');
        this._log(verified ? 'success' : 'error', `Hash verification: ${verified ? 'PASSED' : 'FAILED'}`);
    }

    // =========================================================================
    // Custom Scroll Loading
    // =========================================================================

    _switchTab(tabId) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.toggle('active', tab.id === `tab-${tabId}`);
        });
    }

    async _loadCustomScroll() {
        const activeTab = document.querySelector('.tab-content.active');
        
        if (activeTab.id === 'tab-standard') {
            const scroll = {
                id: 'custom',
                title: 'Custom Scroll',
                description: 'Custom scroll',
                icon: '🔧',
                category: 'all',
                type: ScrollLibrary.SCROLL_TYPES.STANDARD,
                pointer: {
                    lock_address: document.getElementById('customLockAddr').value.trim(),
                    lock_txin: document.getElementById('customTxIn').value.trim(),
                    content_type: document.getElementById('customContentType').value,
                    codec: document.getElementById('customCodec').value,
                    sha256: document.getElementById('customSha256').value.trim() || null
                },
                metadata: {}
            };

            if (!scroll.pointer.lock_address || !scroll.pointer.lock_txin) {
                this._toast('error', 'Please fill in Lock Address and Transaction Input');
                return;
            }

            this._closeModal('customScrollModal');
            await this._loadScroll(scroll);
        } else {
            const scroll = {
                id: 'custom-legacy',
                title: 'Custom Legacy Scroll',
                description: 'Custom legacy scroll',
                icon: '🔧',
                category: 'all',
                type: ScrollLibrary.SCROLL_TYPES.LEGACY,
                pointer: {
                    policy_id: document.getElementById('customPolicyId').value.trim(),
                    content_type: document.getElementById('customLegacyContentType').value,
                    codec: document.getElementById('customLegacyCodec').value
                },
                metadata: {}
            };

            if (!scroll.pointer.policy_id) {
                this._toast('error', 'Please enter a Policy ID');
                return;
            }

            this._closeModal('customScrollModal');
            await this._loadScroll(scroll);
        }
    }

    // =========================================================================
    // Settings
    // =========================================================================

    _saveApiKey() {
        const key = this.elements.apiKeyInput.value.trim();
        this.settings.apiKey = key;
        this._saveSettings();
        this._toast('success', 'API key saved');
        this._log('info', 'Blockfrost API key updated');
        if (key) this._connect();
    }

    _saveKoiosProxy() {
        const value = this.elements.koiosProxyInput?.value?.trim() || '';
        this.settings.koiosProxy = value;
        this._saveSettings();
        if (this.client && typeof this.client.setKoiosProxy === 'function') {
            this.client.setKoiosProxy(value);
        }
        if (this.elements.koiosProxyStatus) {
            this.elements.koiosProxyStatus.textContent = `Current: ${value || '(none)'}`;
        }
        this._log('info', value ? `Koios proxy updated: ${value}` : 'Koios proxy cleared');
        this._toast('success', value ? 'Koios proxy saved' : 'Koios proxy cleared');
    }

    _onModeChange(mode) {
        this.settings.mode = mode;
        this._saveSettings();
        const blockfrostSettings = document.getElementById('blockfrostSettings');
        blockfrostSettings.style.display = mode.startsWith('blockfrost') ? 'block' : 'none';
        this._log('info', `Connection mode changed to: ${mode}`);
    }

    _applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.elements.themeBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === theme);
        });
    }

    // =========================================================================
    // Modal Management
    // =========================================================================

    _openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            if (modalId === 'customScrollModal') this._switchTab('standard');
        }
    }

    _closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');
    }

    // =========================================================================
    // Logging & Toasts
    // =========================================================================

    _log(type, message, details = null) {
        const time = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        const detailsHtml = details
            ? `<details class="log-details"><summary>Details</summary><pre>${this._escapeHtml(details)}</pre></details>`
            : '';
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-message">${this._escapeHtml(message)}</span>
            ${detailsHtml}
        `;
        this.elements.logEntries.appendChild(entry);
        this.elements.logEntries.scrollTop = this.elements.logEntries.scrollHeight;
        while (this.elements.logEntries.children.length > 100) {
            this.elements.logEntries.removeChild(this.elements.logEntries.firstChild);
        }
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    _clearLog() {
        this.elements.logEntries.innerHTML = '';
        this._log('info', 'Log cleared');
    }

    _toast(type, message) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${this._escapeHtml(message)}</span>
        `;
        this.elements.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    _formatSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    _formatErrorDetails(error) {
        const parts = [];
        if (!error) return '';
        if (error.name) parts.push(`name: ${error.name}`);
        if (error.message) parts.push(`message: ${error.message}`);
        if (error.stack) parts.push(`stack:\n${error.stack}`);
        if (error.cause) parts.push(`cause: ${JSON.stringify(error.cause, null, 2)}`);
        return parts.join('\n');
    }

    _loadScript(src) {
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = src;
            s.async = true;
            s.onload = () => resolve();
            s.onerror = (e) => reject(e);
            document.head.appendChild(s);
        });
    }

    // _loadScriptText removed

    _getExtension(contentType) {
        const map = {
            'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif',
            'text/html': '.html', 'text/plain': '.txt',
            'application/pdf': '.pdf', 'application/json': '.json',
            'audio/opus': '.opus', 'audio/mpeg': '.mp3',
            'video/mp4': '.mp4'
        };
        const key = (contentType || '').split(';')[0].trim();
        return map[key] || '.bin';
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.app) return;
    console.log('Init: ScrollReconstructor present?', !!window.ScrollReconstructor);
    window.app = new LedgerScrollsApp();
});
