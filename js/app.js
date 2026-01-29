/**
 * Ledger Scrolls v2.0 - Main Application
 * 
 * "A Library That Cannot Burn"
 * 
 * This file orchestrates the entire application:
 * - UI state management
 * - Event handling
 * - Scroll loading and display
 * - Settings management
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 *                               🎮 SECRET 🎮
 *                          ↑↑↓↓←→←→BA unlocks magic
 * ═══════════════════════════════════════════════════════════════════════════
 */

class LedgerScrollsApp {
    constructor() {
        // State
        this.client = null;
        this.reconstructor = null;
        this.connected = false;
        this.currentScroll = null;
        this.currentCategory = 'all';
        this.loadedContent = null;

        // Easter egg state
        this.konamiProgress = 0;
        this.konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'KeyB', 'KeyA'];

        // Settings
        this.settings = this._loadSettings();

        // Initialize
        this._initializeUI();
        this._bindEvents();
        this._initParticles();
        this._applyTheme(this.settings.theme);
        this._renderScrollLibrary();
        
        // Check if vault was previously unlocked
        if (this.settings.vaultUnlocked) {
            this._silentUnlockVault();
        }

        // Auto-connect if we have an API key
        if (this.settings.apiKey) {
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
            return saved ? JSON.parse(saved) : {
                mode: 'blockfrost',
                apiKey: '',
                theme: 'dark',
                vaultUnlocked: false
            };
        } catch {
            return { mode: 'blockfrost', apiKey: '', theme: 'dark', vaultUnlocked: false };
        }
    }

    _saveSettings() {
        localStorage.setItem('ledgerScrollsSettings', JSON.stringify(this.settings));
    }

    // =========================================================================
    // UI Initialization
    // =========================================================================

    _initializeUI() {
        // Cache DOM elements
        this.elements = {
            // Connection
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            connectBtn: document.getElementById('connectBtn'),

            // Library
            scrollGrid: document.getElementById('scrollGrid'),
            scrollCategories: document.getElementById('scrollCategories'),
            searchInput: document.getElementById('searchScrolls'),

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

            // Log
            logEntries: document.getElementById('logEntries'),
            activityLog: document.getElementById('activityLog'),

            // Modals
            settingsModal: document.getElementById('settingsModal'),
            aboutModal: document.getElementById('aboutModal'),
            verifyModal: document.getElementById('verifyModal'),
            customScrollModal: document.getElementById('customScrollModal'),

            // Settings
            apiKeyInput: document.getElementById('apiKeyInput'),
            modeRadios: document.querySelectorAll('input[name="connectionMode"]'),
            themeBtns: document.querySelectorAll('.theme-btn'),

            // Toast
            toastContainer: document.getElementById('toastContainer')
        };

        // Set initial values
        if (this.settings.apiKey) {
            this.elements.apiKeyInput.value = this.settings.apiKey;
        }
    }

    _bindEvents() {
        // Header buttons
        document.getElementById('settingsBtn').addEventListener('click', () => this._openModal('settingsModal'));
        document.getElementById('infoBtn').addEventListener('click', () => this._openModal('aboutModal'));
        
        // Connection
        this.elements.connectBtn.addEventListener('click', () => this._connect());

        // Search
        this.elements.searchInput.addEventListener('input', (e) => this._onSearch(e.target.value));

        // Library refresh
        document.getElementById('refreshLibrary').addEventListener('click', () => this._renderScrollLibrary());

        // Viewer controls
        this.elements.downloadBtn.addEventListener('click', () => this._downloadCurrentScroll());
        this.elements.verifyBtn.addEventListener('click', () => this._verifyCurrentScroll());
        document.getElementById('closeViewerBtn').addEventListener('click', () => this._closeViewer());

        // Log toggle
        document.getElementById('logToggle').addEventListener('click', () => {
            this.elements.activityLog.classList.toggle('collapsed');
        });
        document.getElementById('clearLogBtn').addEventListener('click', () => this._clearLog());

        // Modal closes
        document.querySelectorAll('.modal-backdrop, .modal-close').forEach(el => {
            el.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this._closeModal(modal.id);
            });
        });

        // Settings: API Key
        document.getElementById('saveApiKey').addEventListener('click', () => this._saveApiKey());

        // Settings: Mode
        this.elements.modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this._onModeChange(e.target.value));
        });

        // Settings: Theme
        this.elements.themeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const theme = btn.dataset.theme;
                this._applyTheme(theme);
                this.settings.theme = theme;
                this._saveSettings();
            });
        });

        // Custom scroll dialog
        document.querySelector('[data-tab="standard"]')?.addEventListener('click', () => this._switchTab('standard'));
        document.querySelector('[data-tab="legacy"]')?.addEventListener('click', () => this._switchTab('legacy'));
        document.getElementById('loadCustomScroll')?.addEventListener('click', () => this._loadCustomScroll());

        // Keyboard shortcuts & Easter Egg
        document.addEventListener('keydown', (e) => {
            // Escape closes modals
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal.active').forEach(m => this._closeModal(m.id));
            }
            
            // Konami code detection
            this._checkKonamiCode(e.code);
        });
    }

    _initParticles() {
        const container = document.getElementById('particles');
        const particleCount = 30;

        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.animationDelay = `${Math.random() * 15}s`;
            particle.style.animationDuration = `${15 + Math.random() * 10}s`;
            container.appendChild(particle);
        }
    }

    // =========================================================================
    // 🎮 EASTER EGG - Konami Code
    // =========================================================================

    _checkKonamiCode(code) {
        if (ScrollLibrary.isVaultUnlocked()) return; // Already unlocked

        if (code === this.konamiCode[this.konamiProgress]) {
            this.konamiProgress++;
            
            if (this.konamiProgress === this.konamiCode.length) {
                this._unlockVault();
            }
        } else {
            this.konamiProgress = 0;
        }
    }

    _unlockVault() {
        // Unlock in the library
        ScrollLibrary.unlockVault();
        
        // Save state
        this.settings.vaultUnlocked = true;
        this._saveSettings();
        
        // Epic reveal animation
        this._vaultRevealAnimation();
        
        // Log it
        this._log('success', '🔮 THE ARCHITECT\'S VAULT HAS BEEN UNLOCKED!');
        
        // Refresh library to show new category
        setTimeout(() => {
            this._renderScrollLibrary();
        }, 2000);
    }

    _silentUnlockVault() {
        ScrollLibrary.unlockVault();
    }

    _vaultRevealAnimation() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'vault-reveal-overlay';
        overlay.innerHTML = `
            <div class="vault-reveal-content">
                <div class="vault-icon">🔮</div>
                <h2 class="vault-title">The Architect's Vault</h2>
                <p class="vault-subtitle">You know the old ways...</p>
                <p class="vault-message">Hidden scrolls have been revealed.</p>
            </div>
        `;
        document.body.appendChild(overlay);

        // Add styles dynamically
        const style = document.createElement('style');
        style.textContent = `
            .vault-reveal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: radial-gradient(ellipse at center, rgba(139, 69, 255, 0.3) 0%, rgba(0, 0, 0, 0.95) 70%);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: vault-fade-in 0.5s ease;
            }
            
            @keyframes vault-fade-in {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            .vault-reveal-content {
                text-align: center;
                color: white;
                animation: vault-content-reveal 1s ease 0.3s both;
            }
            
            @keyframes vault-content-reveal {
                from { 
                    opacity: 0; 
                    transform: scale(0.8) translateY(20px);
                }
                to { 
                    opacity: 1; 
                    transform: scale(1) translateY(0);
                }
            }
            
            .vault-icon {
                font-size: 6rem;
                animation: vault-icon-pulse 2s ease-in-out infinite;
                filter: drop-shadow(0 0 30px rgba(139, 69, 255, 0.8));
            }
            
            @keyframes vault-icon-pulse {
                0%, 100% { transform: scale(1); filter: drop-shadow(0 0 30px rgba(139, 69, 255, 0.8)); }
                50% { transform: scale(1.1); filter: drop-shadow(0 0 50px rgba(212, 168, 85, 1)); }
            }
            
            .vault-title {
                font-family: 'Cinzel', serif;
                font-size: 2.5rem;
                margin: 1rem 0;
                background: linear-gradient(135deg, #d4a855, #f0d78c, #d4a855);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .vault-subtitle {
                font-family: 'Cormorant Garamond', serif;
                font-size: 1.5rem;
                font-style: italic;
                color: #a0a8b8;
                margin-bottom: 0.5rem;
            }
            
            .vault-message {
                font-family: 'Cormorant Garamond', serif;
                font-size: 1.2rem;
                color: #60a5fa;
            }
        `;
        document.head.appendChild(style);

        // Play sound effect if available
        this._playUnlockSound();

        // Remove after animation
        setTimeout(() => {
            overlay.style.animation = 'vault-fade-in 0.5s ease reverse';
            setTimeout(() => {
                overlay.remove();
                style.remove();
            }, 500);
        }, 4000);
    }

    _playUnlockSound() {
        // Create a simple unlock sound using Web Audio API
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            
            // Create a sequence of tones (magical sound)
            const notes = [392, 523.25, 659.25, 783.99]; // G4, C5, E5, G5
            const duration = 0.3;
            
            notes.forEach((freq, i) => {
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                
                oscillator.frequency.value = freq;
                oscillator.type = 'sine';
                
                gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime + i * duration);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + i * duration + duration);
                
                oscillator.start(audioCtx.currentTime + i * duration);
                oscillator.stop(audioCtx.currentTime + i * duration + duration);
            });
        } catch (e) {
            // Audio not available, that's fine
        }
    }

    // =========================================================================
    // Connection Management
    // =========================================================================

    async _connect() {
        const mode = this.settings.mode;
        const apiKey = this.settings.apiKey;

        if (mode === 'blockfrost' && !apiKey) {
            this._toast('error', 'Please enter a Blockfrost API key in Settings');
            this._openModal('settingsModal');
            return;
        }

        this._setConnectionStatus('connecting', 'Connecting...');
        this._log('info', `Connecting to Cardano via ${mode}...`);

        try {
            this.client = new BlockchainClient(mode, apiKey);
            this.reconstructor = new ScrollReconstructor(this.client);

            const result = await this.client.testConnection();
            
            if (result.success) {
                this.connected = true;
                this._setConnectionStatus('connected', `Connected (${mode})`);
                this._log('success', `Successfully connected to Cardano blockchain`);
                this._toast('success', 'Connected to Cardano blockchain!');
                
                // Get and display tip info
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
            this._log('error', `Connection failed: ${e.message}`);
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
        // Render categories
        const categories = ScrollLibrary.getCategoriesWithCounts();
        this.elements.scrollCategories.innerHTML = categories.map(cat => `
            <button class="category-btn ${cat.id === this.currentCategory ? 'active' : ''} ${cat.id === 'vault' ? 'vault-category' : ''}" 
                    data-category="${cat.id}">
                ${cat.icon} ${cat.name} (${cat.count})
            </button>
        `).join('');

        // Bind category clicks
        this.elements.scrollCategories.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentCategory = btn.dataset.category;
                this._renderScrollLibrary();
            });
        });

        // Render scrolls
        const scrolls = ScrollLibrary.getScrollsByCategory(this.currentCategory);
        this._renderScrollGrid(scrolls);
    }

    _renderScrollGrid(scrolls) {
        this.elements.scrollGrid.innerHTML = scrolls.map(scroll => `
            <div class="scroll-card ${scroll.category === 'vault' ? 'vault-scroll' : ''}" data-scroll-id="${scroll.id}">
                <div class="scroll-card-icon">${scroll.icon}</div>
                <div class="scroll-card-title">${scroll.title}</div>
                <div class="scroll-card-meta">${scroll.metadata?.size || scroll.metadata?.type || 'Special'}</div>
                <div class="scroll-card-type">${
                    scroll.type === ScrollLibrary.SCROLL_TYPES.STANDARD ? 'Standard' : 
                    scroll.type === ScrollLibrary.SCROLL_TYPES.LEGACY ? 'Legacy' : 
                    '✨ Embedded'
                }</div>
            </div>
        `).join('');

        // Bind scroll clicks
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
        // Handle embedded scrolls (vault scrolls with content)
        if (scroll.type === 'embedded') {
            this._loadEmbeddedScroll(scroll);
            return;
        }

        if (!this.connected) {
            this._toast('warning', 'Please connect to Cardano first');
            return;
        }

        this.currentScroll = scroll;
        this.loadedContent = null;

        // Update UI
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

        // Set up progress callback
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

            // Display the content
            this._displayContent(result, scroll);

            // Show metadata
            this._displayMetadata(result, scroll);

            // Enable buttons
            this.elements.downloadBtn.disabled = false;
            this.elements.verifyBtn.disabled = false;

            this._log('success', `Successfully loaded ${scroll.title} (${this._formatSize(result.size)})`);
            this._toast('success', `${scroll.title} loaded successfully!`);

        } catch (e) {
            this._log('error', `Failed to load scroll: ${e.message}`);
            this._toast('error', `Failed to load: ${e.message}`);
            this.elements.loadingText.textContent = `❌ Error: ${e.message}`;
        } finally {
            this.elements.progressBar.classList.remove('active');
        }
    }

    _loadEmbeddedScroll(scroll) {
        this.currentScroll = scroll;
        
        // Create result object similar to reconstructed scrolls
        const content = scroll.content.trim();
        const encoder = new TextEncoder();
        const data = encoder.encode(content);
        
        this.loadedContent = {
            data: data,
            contentType: 'text/plain',
            size: data.length,
            hash: 'embedded',
            method: 'Embedded (Local)'
        };

        // Update UI
        this.elements.viewerTitle.textContent = `${scroll.icon} ${scroll.title}`;
        this.elements.viewerLoading.classList.add('hidden');
        this.elements.viewerContent.classList.add('active');
        this.elements.progressBar.classList.remove('active');

        // Display with special styling for vault scrolls
        this.elements.viewerContent.innerHTML = `
            <div class="embedded-scroll-content vault-text">
                <pre>${this._escapeHtml(content)}</pre>
            </div>
        `;

        // Show metadata
        this._displayEmbeddedMetadata(scroll);

        // Enable download (disable verify for embedded)
        this.elements.downloadBtn.disabled = false;
        this.elements.verifyBtn.disabled = true;

        this._log('info', `Opened embedded scroll: ${scroll.title}`);
    }

    _displayEmbeddedMetadata(scroll) {
        this.elements.scrollMetadata.classList.add('active');
        
        const metadata = {
            'Type': scroll.metadata?.type || 'Embedded',
            'Author': scroll.metadata?.author || 'Unknown',
            'Created': scroll.metadata?.created || scroll.metadata?.ratified || 'Unknown',
            'Status': scroll.metadata?.status || 'Active',
            'Unlocked By': scroll.metadata?.unlocked_by || 'Easter Egg'
        };

        this.elements.scrollMetadata.innerHTML = `
            <div class="metadata-grid">
                ${Object.entries(metadata).map(([label, value]) => `
                    <div class="metadata-item">
                        <span class="metadata-label">${label}</span>
                        <span class="metadata-value">${value}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    _displayContent(result, scroll) {
        this.elements.viewerLoading.classList.add('hidden');
        this.elements.viewerContent.classList.add('active');

        const contentType = result.contentType.split(';')[0].trim();

        if (contentType.startsWith('image/')) {
            // Display image
            const blob = new Blob([result.data], { type: contentType });
            const url = URL.createObjectURL(blob);
            this.elements.viewerContent.innerHTML = `
                <img src="${url}" alt="${scroll.title}" style="max-width: 100%; height: auto;">
            `;
        } else if (contentType === 'text/html') {
            // Display HTML in iframe (sandboxed)
            const blob = new Blob([result.data], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            this.elements.viewerContent.innerHTML = `
                <iframe src="${url}" sandbox="allow-same-origin" style="width: 100%; height: 600px; border: none; border-radius: 12px; background: white;"></iframe>
            `;
        } else if (contentType.startsWith('text/')) {
            // Display plain text
            const text = new TextDecoder().decode(result.data);
            const preview = text.length > 50000 ? text.substring(0, 50000) + '\n\n... (truncated)' : text;
            this.elements.viewerContent.innerHTML = `
                <div class="text-content">${this._escapeHtml(preview)}</div>
            `;
        } else {
            // Unknown type - show download prompt
            this.elements.viewerContent.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <p style="font-size: 3rem; margin-bottom: 20px;">📦</p>
                    <p>This scroll contains binary data (${contentType})</p>
                    <p style="color: var(--color-text-muted);">Click Download to save the file</p>
                </div>
            `;
        }
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
        if (!this.loadedContent || !this.currentScroll) return;

        const contentType = this.loadedContent.contentType.split(';')[0].trim();
        const extension = this._getExtension(contentType);
        const filename = `${this.currentScroll.title.replace(/[^a-z0-9]/gi, '_')}${extension}`;

        const blob = new Blob([this.loadedContent.data], { type: contentType });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();

        URL.revokeObjectURL(url);
        this._log('info', `Downloaded: ${filename}`);
        this._toast('success', `Downloaded ${filename}`);
    }

    _verifyCurrentScroll() {
        if (!this.loadedContent || !this.currentScroll) return;

        const expected = this.currentScroll.pointer?.sha256 || 
                        this.currentScroll.pointer?.sha256_original;
        const computed = this.loadedContent.hash;
        const verified = !expected || expected.toLowerCase() === computed.toLowerCase();

        const modal = document.getElementById('verifyModal');
        const resultDiv = document.getElementById('verificationResult');

        resultDiv.innerHTML = `
            <div class="verification-icon">${verified ? '✅' : '❌'}</div>
            <div class="verification-status ${verified ? 'verified' : 'failed'}">
                ${verified ? 'VERIFIED' : 'VERIFICATION FAILED'}
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
            <p style="margin-top: 20px; color: var(--color-text-secondary); font-size: 0.9rem;">
                ${verified 
                    ? 'The scroll content matches the on-chain record exactly.' 
                    : 'The computed hash does not match the expected hash!'}
            </p>
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
            // Standard scroll
            const scroll = {
                id: 'custom',
                title: 'Custom Scroll',
                description: 'Custom scroll loaded by user',
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
            // Legacy scroll
            const scroll = {
                id: 'custom-legacy',
                title: 'Custom Legacy Scroll',
                description: 'Custom legacy scroll loaded by user',
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
        
        // Auto-connect with new key
        if (key) {
            this._connect();
        }
    }

    _onModeChange(mode) {
        this.settings.mode = mode;
        this._saveSettings();
        
        // Show/hide API key section
        const blockfrostSettings = document.getElementById('blockfrostSettings');
        blockfrostSettings.style.display = mode === 'blockfrost' ? 'block' : 'none';

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
            
            // Handle custom scroll modal special case
            if (modalId === 'customScrollModal') {
                this._switchTab('standard');
            }
        }
    }

    _closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
        }
    }

    // =========================================================================
    // Logging & Toasts
    // =========================================================================

    _log(type, message) {
        const time = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-message">${message}</span>
        `;
        
        this.elements.logEntries.appendChild(entry);
        this.elements.logEntries.scrollTop = this.elements.logEntries.scrollHeight;

        // Keep only last 100 entries
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
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${message}</span>
        `;

        this.elements.toastContainer.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // =========================================================================
    // Utility Functions
    // =========================================================================

    _formatSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    _getExtension(contentType) {
        const map = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'text/html': '.html',
            'text/plain': '.txt',
            'application/pdf': '.pdf',
            'application/json': '.json'
        };
        return map[contentType] || '.bin';
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new LedgerScrollsApp();
});
