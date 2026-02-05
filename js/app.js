/**
 * Ledger Scrolls v2.1 - Main Application
 * 
 * "A Library That Cannot Burn"
 * 
 * Mobile-first viewer for immutable documents stored on Cardano.
 */

// --- Binary rendering helpers ---
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
    if (ct.includes("audio/")) return ct.includes("mpeg") ? "mp3" : "opus";
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

    // Video
    if (ct.startsWith("video/") || ct.includes("video/mp4")) {
        const vid = document.createElement("video");
        vid.controls = true;
        vid.playsInline = true;
        vid.preload = "metadata";
        vid.src = url;
        viewerContentEl.appendChild(vid);
        return { blob, url, filename: finalName, kind: "video" };
    }

    // Audio
    if (ct.startsWith("audio/")) {
        const audio = document.createElement("audio");
        audio.controls = true;
        audio.src = url;
        viewerContentEl.appendChild(audio);
        return { blob, url, filename: finalName, kind: "audio" };
    }

    // Image
    if (ct.startsWith("image/")) {
        const img = document.createElement("img");
        img.src = url;
        img.alt = finalName;
        viewerContentEl.appendChild(img);
        return { blob, url, filename: finalName, kind: "image" };
    }

    // PDF
    if (ct.includes("application/pdf")) {
        const iframe = document.createElement("iframe");
        iframe.src = url;
        viewerContentEl.appendChild(iframe);
        return { blob, url, filename: finalName, kind: "pdf" };
    }

    // Text / HTML
    if (ct.startsWith("text/") || ct.includes("application/json")) {
        const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
        const text = new TextDecoder("utf-8", { fatal: false }).decode(u8);
        
        if (ct.includes("text/html")) {
            const iframe = document.createElement("iframe");
            iframe.setAttribute("sandbox", "allow-same-origin");
            viewerContentEl.appendChild(iframe);
            const doc = iframe.contentDocument;
            doc.open();
            doc.write(text);
            doc.close();
            return { blob, url, filename: finalName, kind: "html" };
        }
        
        const pre = document.createElement("pre");
        pre.textContent = text.length > 50000 ? text.substring(0, 50000) + "\n\n... (truncated)" : text;
        viewerContentEl.appendChild(pre);
        return { blob, url, filename: finalName, kind: "text" };
    }

    // Binary fallback
    const p = document.createElement("p");
    p.textContent = `Binary content (${ct}). Use Download button to save.`;
    viewerContentEl.appendChild(p);
    return { blob, url, filename: finalName, kind: "binary" };
}

// =============================================================================
// Main Application Class
// =============================================================================
class LedgerScrollsApp {
    constructor() {
        // State
        this.client = null;
        this.reconstructor = null;
        this.connected = false;
        this.currentScroll = null;
        this.currentCategory = 'all';
        this.loadedContent = null;
        this.hasError = false;
        this.errorCount = 0;

        // Settings
        this.settings = this._loadSettings();

        // Initialize
        this._initializeUI();
        this._bindEvents();
        this._initParticles();
        this._applyTheme(this.settings.theme);
        this._renderScrollLibrary();
        this._updateModeUI();

        // Auto-connect with Koios by default
        this._connect();

        this._log('info', 'Ledger Scrolls v2.1 initialized');
    }

    // =========================================================================
    // Settings Management
    // =========================================================================

    _loadSettings() {
        try {
            const saved = localStorage.getItem('ledgerScrollsSettings');
            const fallback = {
                mode: window.LS_DEFAULT_MODE || 'koios',
                apiKey: '',
                koiosProxy: '',
                theme: 'dark'
            };
            const settings = saved ? JSON.parse(saved) : fallback;
            if (!settings.koiosProxy) settings.koiosProxy = '';
            if (window.LS_OVERRIDE_MODE) settings.mode = window.LS_OVERRIDE_MODE;
            return settings;
        } catch {
            return { mode: 'koios', apiKey: '', koiosProxy: '', theme: 'dark' };
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
            // Status
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            errorBanner: document.getElementById('errorBanner'),
            errorMessage: document.getElementById('errorMessage'),
            
            // Library
            scrollGrid: document.getElementById('scrollGrid'),
            scrollCategories: document.getElementById('scrollCategories'),
            searchInput: document.getElementById('searchScrolls'),
            libraryPanel: document.getElementById('libraryPanel'),
            
            // Viewer
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
            
            // Activity Log
            logEntries: document.getElementById('logEntries'),
            activityLog: document.getElementById('activityLog'),
            logBadge: document.getElementById('logBadge'),
            
            // Modals
            settingsModal: document.getElementById('settingsModal'),
            aboutModal: document.getElementById('aboutModal'),
            verifyModal: document.getElementById('verifyModal'),
            customScrollModal: document.getElementById('customScrollModal'),
            troubleshootModal: document.getElementById('troubleshootModal'),
            
            // Settings inputs
            apiKeyInput: document.getElementById('apiKeyInput'),
            koiosProxyInput: document.getElementById('koiosProxyInput'),
            koiosProxyStatus: document.getElementById('koiosProxyStatus'),
            modeRadios: document.querySelectorAll('input[name="connectionMode"]'),
            themeBtns: document.querySelectorAll('.theme-btn'),
            blockfrostSettings: document.getElementById('blockfrostSettings'),
            blockfrostSection: document.getElementById('blockfrostSection'),
            troubleshootStatus: document.getElementById('troubleshootStatus'),
            troubleshootApiKey: document.getElementById('troubleshootApiKey'),
            
            toastContainer: document.getElementById('toastContainer')
        };

        // Load saved values into inputs
        if (this.settings.apiKey && this.elements.apiKeyInput) {
            this.elements.apiKeyInput.value = this.settings.apiKey;
        }
        if (this.elements.koiosProxyInput) {
            this.elements.koiosProxyInput.value = this.settings.koiosProxy || '';
        }
        if (this.elements.koiosProxyStatus) {
            this.elements.koiosProxyStatus.textContent = this.settings.koiosProxy 
                ? `Using: ${this.settings.koiosProxy}` 
                : 'Using default Koios endpoints';
        }
    }

    _bindEvents() {
        // Header buttons
        document.getElementById('settingsBtn')?.addEventListener('click', () => this._openModal('settingsModal'));
        document.getElementById('infoBtn')?.addEventListener('click', () => this._openModal('aboutModal'));
        document.getElementById('troubleshootBtn')?.addEventListener('click', () => this._openTroubleshoot());
        
        // Search
        this.elements.searchInput?.addEventListener('input', (e) => this._onSearch(e.target.value));
        
        // Viewer controls
        this.elements.downloadBtn?.addEventListener('click', () => this._downloadCurrentScroll());
        this.elements.verifyBtn?.addEventListener('click', () => this._verifyCurrentScroll());
        document.getElementById('backToLibraryBtn')?.addEventListener('click', () => this._closeViewer());
        
        // Activity log
        document.getElementById('logToggle')?.addEventListener('click', () => {
            this.elements.activityLog.classList.toggle('collapsed');
            if (this.elements.logBadge) this.elements.logBadge.style.display = 'none';
        });
        document.getElementById('clearLogBtn')?.addEventListener('click', () => this._clearLog());
        document.getElementById('copyLogBtn')?.addEventListener('click', () => this._copyLog());
        
        // Error banner
        document.getElementById('showTroubleshootBtn')?.addEventListener('click', () => this._openTroubleshoot());
        
        // Modal close handlers
        document.querySelectorAll('.modal-backdrop, .modal-close').forEach(el => {
            el.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this._closeModal(modal.id);
            });
        });

        // Settings modal
        document.getElementById('saveApiKey')?.addEventListener('click', () => this._saveApiKey());
        document.getElementById('saveKoiosProxy')?.addEventListener('click', () => this._saveKoiosProxy());
        
        this.elements.modeRadios?.forEach(radio => {
            radio.addEventListener('change', (e) => this._onModeChange(e.target.value));
        });

        this.elements.themeBtns?.forEach(btn => {
            btn.addEventListener('click', () => {
                const theme = btn.dataset.theme;
                this._applyTheme(theme);
                this.settings.theme = theme;
                this._saveSettings();
            });
        });

        // Troubleshoot modal
        document.getElementById('retryConnectionBtn')?.addEventListener('click', () => {
            this._closeModal('troubleshootModal');
            this._connect();
        });
        document.getElementById('switchToKoiosBtn')?.addEventListener('click', () => this._switchMode('koios'));
        document.getElementById('switchToBlockfrostBtn')?.addEventListener('click', () => {
            if (this.elements.blockfrostSection) {
                this.elements.blockfrostSection.style.display = 'block';
            }
        });
        document.getElementById('saveTroubleshootApiKey')?.addEventListener('click', () => {
            const key = this.elements.troubleshootApiKey?.value?.trim();
            if (key) {
                this.settings.apiKey = key;
                this.settings.mode = 'blockfrost';
                this._saveSettings();
                this._updateModeUI();
                this._closeModal('troubleshootModal');
                this._connect();
            }
        });
        document.getElementById('viewFullLogBtn')?.addEventListener('click', () => {
            this._closeModal('troubleshootModal');
            this.elements.activityLog.classList.remove('collapsed');
            this.elements.activityLog.scrollIntoView({ behavior: 'smooth' });
        });

        // Custom scroll modal
        document.querySelector('[data-tab="standard"]')?.addEventListener('click', () => this._switchTab('standard'));
        document.querySelector('[data-tab="legacy"]')?.addEventListener('click', () => this._switchTab('legacy'));
        document.getElementById('loadCustomScroll')?.addEventListener('click', () => this._loadCustomScroll());

        // Keyboard
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal.active').forEach(m => this._closeModal(m.id));
                if (this.elements.viewerPanel.classList.contains('active') && window.innerWidth < 768) {
                    this._closeViewer();
                }
            }
        });
    }

    _initParticles() {
        const container = document.getElementById('particles');
        if (!container) return;
        const count = window.innerWidth < 768 ? 15 : 25;
        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.animationDelay = `${Math.random() * 20}s`;
            particle.style.animationDuration = `${20 + Math.random() * 15}s`;
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
            this._setConnectionStatus('disconnected', 'API key required');
            this._showError('Blockfrost requires an API key. Tap Fix It to configure.');
            this._log('warning', 'Blockfrost mode selected but no API key configured');
            return;
        }

        this._setConnectionStatus('connecting', 'Connecting...');
        this._hideError();
        this._log('info', `Connecting via ${mode}...`);

        try {
            this.client = new BlockchainClient(mode, apiKey, this.settings.koiosProxy);
            
            if (!window.ScrollReconstructor) {
                await this._loadScript(`js/reconstruct.js?cb=${Date.now()}`);
            }
            if (!window.ScrollReconstructor) {
                throw new Error('Failed to load scroll reconstructor');
            }
            
            this.reconstructor = new ScrollReconstructor(this.client);
            const result = await this.client.testConnection();
            
            if (result.success) {
                this.connected = true;
                this.errorCount = 0;
                this._setConnectionStatus('connected', `Connected (${mode})`);
                this._hideError();
                this._log('success', 'Connected to Cardano blockchain');
                this._toast('success', 'Connected!');
                
                // Get chain tip info
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
            this.errorCount++;
            this._setConnectionStatus('disconnected', 'Connection failed');
            this._showError(`Connection failed: ${e.message}`);
            this._log('error', `Connection failed: ${e.message}`, this._formatErrorDetails(e));
            
            // Auto-suggest troubleshooting after multiple failures
            if (this.errorCount >= 2) {
                this._toast('warning', 'Having trouble? Tap 🔧 for help');
            }
        }
    }

    _switchMode(mode) {
        this.settings.mode = mode;
        this._saveSettings();
        this._updateModeUI();
        this._closeModal('troubleshootModal');
        this._connect();
    }

    _updateModeUI() {
        const mode = this.settings.mode;
        
        // Update radio buttons
        this.elements.modeRadios?.forEach(radio => {
            radio.checked = radio.value === mode;
        });
        
        // Show/hide Blockfrost settings
        if (this.elements.blockfrostSettings) {
            this.elements.blockfrostSettings.style.display = mode === 'blockfrost' ? 'block' : 'none';
        }
    }

    _setConnectionStatus(status, text) {
        if (this.elements.statusDot) {
            this.elements.statusDot.className = `status-dot ${status}`;
        }
        if (this.elements.statusText) {
            this.elements.statusText.textContent = text;
        }
        
        // Update troubleshoot modal status
        if (this.elements.troubleshootStatus) {
            const icons = { connected: '✅', connecting: '⏳', disconnected: '❌' };
            this.elements.troubleshootStatus.innerHTML = `
                <span class="check-icon">${icons[status] || '❓'}</span>
                <span class="check-text">${text}</span>
            `;
        }
    }

    _showError(message) {
        this.hasError = true;
        if (this.elements.errorBanner) {
            this.elements.errorBanner.style.display = 'flex';
        }
        if (this.elements.errorMessage) {
            this.elements.errorMessage.textContent = message;
        }
    }

    _hideError() {
        this.hasError = false;
        if (this.elements.errorBanner) {
            this.elements.errorBanner.style.display = 'none';
        }
    }

    // =========================================================================
    // Library Rendering
    // =========================================================================

    _renderScrollLibrary() {
        const categories = ScrollLibrary.getCategoriesWithCounts();
        
        if (this.elements.scrollCategories) {
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
        }

        const scrolls = ScrollLibrary.getScrollsByCategory(this.currentCategory);
        this._renderScrollGrid(scrolls);
    }

    _renderScrollGrid(scrolls) {
        if (!this.elements.scrollGrid) return;
        
        this.elements.scrollGrid.innerHTML = scrolls.map(scroll => `
            <div class="scroll-card" data-scroll-id="${scroll.id}">
                <div class="scroll-card-icon">${scroll.icon}</div>
                <div class="scroll-card-info">
                    <div class="scroll-card-title">${scroll.title}</div>
                    <div class="scroll-card-meta">${scroll.metadata?.size || 'Unknown size'}</div>
                </div>
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
            this._toast('warning', 'Please wait for connection...');
            if (!this.hasError) this._connect();
            return;
        }

        this.currentScroll = scroll;
        this.loadedContent = null;

        // Show viewer
        this.elements.viewerPanel.classList.add('active');
        this.elements.viewerTitle.textContent = scroll.title;
        this.elements.viewerContent.classList.remove('active');
        this.elements.viewerContent.innerHTML = '';
        this.elements.scrollMetadata.classList.remove('active');
        this.elements.viewerLoading.classList.remove('hidden');
        this.elements.progressBar.classList.add('active');
        this.elements.progressFill.style.width = '0%';
        this.elements.downloadBtn.disabled = true;
        this.elements.verifyBtn.disabled = true;

        this._log('info', `Loading: ${scroll.title}`);

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
            this._log('success', `Loaded ${scroll.title} (${this._formatSize(result.size)})`);
            this._toast('success', 'Scroll loaded!');
        } catch (e) {
            this._log('error', `Failed: ${e.message}`, this._formatErrorDetails(e));
            this._toast('error', `Failed: ${e.message}`);
            this.elements.loadingText.textContent = `❌ Error: ${e.message}`;
            this._showLogBadge();
        } finally {
            this.elements.progressBar.classList.remove('active');
        }
    }

    _displayContent(result, scroll) {
        revokeActiveObjectUrl();
        this.elements.viewerLoading.classList.add('hidden');
        this.elements.viewerContent.classList.add('active');

        const rendered = renderScrollBytesIntoViewer({
            bytes: result.bytes,
            contentType: result.contentType,
            filename: `${scroll.id}${this._getExtension(result.contentType)}`
        }, this.elements.viewerContent);

        this.loadedContent = { ...result, ...rendered };
    }

    _displayMetadata(result, scroll) {
        this.elements.scrollMetadata.classList.add('active');
        
        const items = [
            { label: 'Type', value: scroll.type === ScrollLibrary.SCROLL_TYPES.STANDARD ? 'Standard Scroll' : 'Legacy Scroll' },
            { label: 'Size', value: this._formatSize(result.size) },
            { label: 'Content', value: result.contentType }
        ];

        if (scroll.metadata?.pages) items.push({ label: 'Pages', value: scroll.metadata.pages });
        if (scroll.metadata?.author) items.push({ label: 'Author', value: scroll.metadata.author });
        if (scroll.metadata?.minted) items.push({ label: 'Minted', value: scroll.metadata.minted });

        if (scroll.pointer?.sha256 || scroll.pointer?.sha256_original) {
            items.push({ 
                label: 'Hash', 
                value: (scroll.pointer.sha256 || scroll.pointer.sha256_original).substring(0, 16) + '...', 
                isHash: true 
            });
        }

        this.elements.scrollMetadata.innerHTML = `
            <div class="metadata-grid">
                ${items.map(item => `
                    <div class="metadata-item">
                        <span class="metadata-label">${item.label}</span>
                        <span class="metadata-value ${item.isHash ? 'hash' : ''}">${item.value}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    _closeViewer() {
        this.elements.viewerPanel.classList.remove('active');
        revokeActiveObjectUrl();
    }

    _downloadCurrentScroll() {
        if (!this.loadedContent?.blob) {
            this._toast('error', 'No content to download');
            return;
        }
        downloadBlob(this.loadedContent.blob, this.loadedContent.filename);
        this._log('info', `Downloaded: ${this.loadedContent.filename}`);
        this._toast('success', 'Download started!');
    }

    async _verifyCurrentScroll() {
        if (!this.currentScroll || !this.loadedContent) {
            this._toast('error', 'No scroll loaded');
            return;
        }

        const pointer = this.currentScroll.pointer;
        const expectedHash = pointer.sha256 || pointer.sha256_original;
        
        if (!expectedHash) {
            this._toast('info', 'No hash to verify for this scroll');
            return;
        }

        this._log('info', 'Computing SHA256 hash...');
        
        try {
            const hashBuffer = await crypto.subtle.digest('SHA-256', this.loadedContent.bytes);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const computedHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            
            const verified = computedHash === expectedHash;
            
            this.elements.verifyModal.querySelector('#verificationResult').innerHTML = `
                <div class="verification-icon">${verified ? '✅' : '❌'}</div>
                <div class="verification-status ${verified ? 'verified' : 'failed'}">
                    ${verified ? 'VERIFIED' : 'MISMATCH'}
                </div>
                <div class="hash-comparison">
                    <div class="hash-row">
                        <div class="hash-label">Expected</div>
                        <div class="hash-value">${expectedHash}</div>
                    </div>
                    <div class="hash-row">
                        <div class="hash-label">Computed</div>
                        <div class="hash-value">${computedHash}</div>
                    </div>
                </div>
            `;
            
            this._openModal('verifyModal');
            this._log(verified ? 'success' : 'error', `Hash ${verified ? 'verified' : 'mismatch'}`);
        } catch (e) {
            this._toast('error', 'Hash verification failed');
            this._log('error', `Verification error: ${e.message}`);
        }
    }

    // =========================================================================
    // Custom Scroll Loading
    // =========================================================================

    _switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tab}`);
        });
    }

    async _loadCustomScroll() {
        const activeTab = document.querySelector('.tab-content.active')?.id;
        
        if (activeTab === 'tab-standard') {
            const scroll = {
                id: 'custom-standard',
                title: 'Custom Scroll',
                description: 'Custom standard scroll',
                icon: '🔧',
                category: 'all',
                type: ScrollLibrary.SCROLL_TYPES.STANDARD,
                pointer: {
                    lock_address: document.getElementById('customLockAddr')?.value?.trim(),
                    lock_txin: document.getElementById('customTxIn')?.value?.trim(),
                    content_type: document.getElementById('customContentType')?.value,
                    codec: document.getElementById('customCodec')?.value,
                    sha256: document.getElementById('customSha256')?.value?.trim() || null
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
                    policy_id: document.getElementById('customPolicyId')?.value?.trim(),
                    content_type: document.getElementById('customLegacyContentType')?.value,
                    codec: document.getElementById('customLegacyCodec')?.value
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
        const key = this.elements.apiKeyInput?.value?.trim();
        this.settings.apiKey = key;
        this._saveSettings();
        this._toast('success', 'API key saved');
        this._log('info', 'Blockfrost API key updated');
        if (key && this.settings.mode === 'blockfrost') {
            this._connect();
        }
    }

    _saveKoiosProxy() {
        const value = this.elements.koiosProxyInput?.value?.trim() || '';
        this.settings.koiosProxy = value;
        this._saveSettings();
        
        if (this.client?.setKoiosProxy) {
            this.client.setKoiosProxy(value);
        }
        
        if (this.elements.koiosProxyStatus) {
            this.elements.koiosProxyStatus.textContent = value 
                ? `Using: ${value}` 
                : 'Using default Koios endpoints';
        }
        
        this._log('info', value ? `Koios proxy: ${value}` : 'Koios proxy cleared');
        this._toast('success', 'Proxy settings saved');
    }

    _onModeChange(mode) {
        this.settings.mode = mode;
        this._saveSettings();
        this._updateModeUI();
        this._log('info', `Mode changed to: ${mode}`);
        
        if (mode === 'koios' || (mode === 'blockfrost' && this.settings.apiKey)) {
            this._connect();
        }
    }

    _applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.elements.themeBtns?.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === theme);
        });
    }

    // =========================================================================
    // Modal & Troubleshoot
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

    _openTroubleshoot() {
        // Update status in troubleshoot modal
        const status = this.connected ? 'connected' : 'disconnected';
        const text = this.connected 
            ? `Connected via ${this.settings.mode}` 
            : 'Not connected';
        
        if (this.elements.troubleshootStatus) {
            const icons = { connected: '✅', disconnected: '❌' };
            this.elements.troubleshootStatus.innerHTML = `
                <span class="check-icon">${icons[status]}</span>
                <span class="check-text">${text}</span>
            `;
        }
        
        // Reset blockfrost section
        if (this.elements.blockfrostSection) {
            this.elements.blockfrostSection.style.display = 'none';
        }
        
        this._openModal('troubleshootModal');
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
        
        this.elements.logEntries?.appendChild(entry);
        if (this.elements.logEntries) {
            this.elements.logEntries.scrollTop = this.elements.logEntries.scrollHeight;
        }
        
        // Keep log size reasonable
        while (this.elements.logEntries?.children?.length > 100) {
            this.elements.logEntries.removeChild(this.elements.logEntries.firstChild);
        }
        
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // Show badge for errors when log is collapsed
        if (type === 'error' && this.elements.activityLog?.classList.contains('collapsed')) {
            this._showLogBadge();
        }
    }

    _showLogBadge() {
        if (this.elements.logBadge) {
            this.elements.logBadge.style.display = 'inline-flex';
        }
    }

    _clearLog() {
        if (this.elements.logEntries) {
            this.elements.logEntries.innerHTML = '';
        }
        this._log('info', 'Log cleared');
    }

    _copyLog() {
        const entries = this.elements.logEntries?.querySelectorAll('.log-entry');
        if (!entries?.length) {
            this._toast('info', 'Log is empty');
            return;
        }
        
        const text = Array.from(entries).map(entry => {
            const time = entry.querySelector('.log-time')?.textContent || '';
            const msg = entry.querySelector('.log-message')?.textContent || '';
            return `[${time}] ${msg}`;
        }).join('\n');
        
        navigator.clipboard.writeText(text).then(() => {
            this._toast('success', 'Log copied to clipboard');
        }).catch(() => {
            this._toast('error', 'Failed to copy log');
        });
    }

    _toast(type, message) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${this._escapeHtml(message)}</span>
        `;
        this.elements.toastContainer?.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
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

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.app) return;
    window.app = new LedgerScrollsApp();
});
