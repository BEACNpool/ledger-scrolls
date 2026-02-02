/**
 * Ledger Scrolls v2.0 - Blockchain Clients
 * 
 * Provides abstracted access to Cardano blockchain data.
 * Supports multiple backends:
 * - Blockfrost API (requires API key)
 * - Koios API (free, no key required)
 */

class BlockchainClient {
    constructor(mode = 'blockfrost', apiKey = null, koiosProxy = '') {
        this.mode = mode;
        this.apiKey = apiKey;
        this.koiosProxy = koiosProxy;
        this.baseUrl = this._getBaseUrl();
        this.koiosBaseUrls = [
            'https://api.koios.rest/api/v1',
            'https://corsproxy.io/?https://api.koios.rest/api/v1',
            'https://cors.isomorphic-git.org/https://api.koios.rest/api/v1'
        ];
        this.rateLimitDelay = 100; // ms between requests
        this.lastRequest = 0;
    }

    _getBaseUrl() {
        switch (this.mode) {
            case 'blockfrost':
                return 'https://cardano-mainnet.blockfrost.io/api/v0';
            case 'koios':
                return 'https://api.koios.rest/api/v1';
            default:
                throw new Error(`Unknown mode: ${this.mode}`);
        }
    }

    setApiKey(key) {
        this.apiKey = key;
    }

    setMode(mode) {
        this.mode = mode;
        this.baseUrl = this._getBaseUrl();
    }

    async _rateLimitedFetch(url, options = {}, retries = 0) {
        // Enforce rate limiting
        const now = Date.now();
        const elapsed = now - this.lastRequest;
        if (elapsed < this.rateLimitDelay) {
            await new Promise(r => setTimeout(r, this.rateLimitDelay - elapsed));
        }
        this.lastRequest = Date.now();

        const response = await fetch(url, options);
        
        if (response.status === 429) {
            // Rate limited - wait and retry (max 5 retries)
            if (retries >= 5) throw new Error('Rate limit exceeded after 5 retries');
            const retryAfter = parseInt(response.headers.get('Retry-After') || '2');
            await new Promise(r => setTimeout(r, retryAfter * 1000));
            return this._rateLimitedFetch(url, options, retries + 1);
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    async _request(endpoint, options = {}) {
        const headers = { ...options.headers };

        if (this.mode === 'blockfrost') {
            const url = `${this.baseUrl}${endpoint}`;
            if (this.apiKey) {
                headers['project_id'] = this.apiKey;
            }
            return this._rateLimitedFetch(url, { ...options, headers });
        }

        if (this.mode === 'koios') {
            return this._requestKoiosWithFallback(endpoint, options, headers);
        }

        const url = `${this.baseUrl}${endpoint}`;
        return this._rateLimitedFetch(url, { ...options, headers });
    }

    async _requestKoiosWithFallback(endpoint, options = {}, headers = {}) {
        const errors = [];
        const bases = [...this.koiosBaseUrls];
        if (this.koiosProxy) {
            bases.unshift(this.koiosProxy.replace(/\/$/, ''));
        }

        for (const base of bases) {
            try {
                const url = `${base}${endpoint}`;
                const resp = await this._rateLimitedFetch(url, {
                    ...options,
                    headers,
                    mode: 'cors',
                    credentials: 'omit'
                });
                this.baseUrl = base;
                return resp;
            } catch (e) {
                errors.push({ base, message: e.message || String(e) });
            }
        }
        throw new Error(`Koios request failed: ${errors.map(e => `${e.base} -> ${e.message}`).join(' | ')}`);
    }

    /**
     * Query UTxOs at an address
     */
    async queryUtxosAtAddress(address) {
        if (this.mode === 'blockfrost') {
            return this._blockfrostQueryUtxos(address);
        } else if (this.mode === 'koios') {
            return this._koiosQueryUtxos(address);
        }
    }

    async _blockfrostQueryUtxos(address) {
        const utxos = [];
        let page = 1;

        while (true) {
            try {
                const batch = await this._request(`/addresses/${address}/utxos?page=${page}`);
                if (!batch || batch.length === 0) break;
                utxos.push(...batch);
                if (batch.length < 100) break;
                page++;
            } catch (e) {
                if (e.message.includes('404')) break;
                throw e;
            }
        }

        return utxos;
    }

    async _koiosQueryUtxos(address) {
        const response = await this._request('/address_utxos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ _addresses: [address] })
        });

        // Convert to Blockfrost-like format
        return response.map(u => ({
            tx_hash: u.tx_hash,
            tx_index: u.tx_index,
            output_index: u.tx_index,
            amount: u.value ? [
                { unit: 'lovelace', quantity: u.value },
                ...(u.asset_list || []).map(a => ({
                    unit: a.policy_id + a.asset_name,
                    quantity: a.quantity
                }))
            ] : [],
            inline_datum: u.inline_datum?.bytes || null,
            address: address
        }));
    }

    /**
     * Query specific UTxO by txin
     */
    async queryUtxoByTxIn(txHash, txIndex) {
        if (this.mode === 'blockfrost') {
            const response = await this._request(`/txs/${txHash}/utxos`);
            const utxo = response.outputs?.find(o => o.output_index === txIndex);
            if (!utxo) throw new Error(`UTxO not found: ${txHash}#${txIndex}`);
            return {
                ...utxo,
                tx_hash: txHash,
                tx_index: txIndex
            };
        } else if (this.mode === 'koios') {
            const response = await this._request('/utxo_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ _utxo_refs: [`${txHash}#${txIndex}`] })
            });
            if (!response || response.length === 0) {
                throw new Error(`UTxO not found: ${txHash}#${txIndex}`);
            }
            return {
                tx_hash: txHash,
                tx_index: txIndex,
                output_index: txIndex,
                inline_datum: response[0].inline_datum?.bytes || null,
                amount: response[0].value ? [
                    { unit: 'lovelace', quantity: response[0].value }
                ] : []
            };
        }
    }

    /**
     * Query transaction metadata
     */
    async queryTxMetadata(txHash) {
        if (this.mode === 'blockfrost') {
            try {
                return await this._request(`/txs/${txHash}/metadata`);
            } catch (e) {
                if (e.message.includes('404')) return [];
                throw e;
            }
        } else if (this.mode === 'koios') {
            const response = await this._request('/tx_metadata', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ _tx_hashes: [txHash] })
            });
            return response?.[0]?.metadata || [];
        }
    }

    /**
     * Query all assets under a policy
     */
    async queryPolicyAssets(policyId, progressCallback = null) {
        if (this.mode === 'blockfrost') {
            return this._blockfrostQueryPolicyAssets(policyId, progressCallback);
        } else if (this.mode === 'koios') {
            return this._koiosQueryPolicyAssets(policyId, progressCallback);
        }
    }

    async _blockfrostQueryPolicyAssets(policyId, progressCallback) {
        const assets = [];
        let page = 1;

        while (true) {
            if (progressCallback) {
                progressCallback(`Scanning policy assets (page ${page})...`);
            }

            try {
                const batch = await this._request(`/assets/policy/${policyId}?page=${page}`);
                if (!batch || batch.length === 0) break;
                assets.push(...batch);
                if (batch.length < 100) break;
                page++;
            } catch (e) {
                if (e.message.includes('404')) break;
                throw e;
            }
        }

        return assets;
    }

    async _koiosQueryPolicyAssets(policyId, progressCallback) {
        if (progressCallback) {
            progressCallback('Querying policy assets...');
        }

        const response = await this._request('/policy_asset_list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ _policy_id: policyId })
        });

        return (response || []).map(a => ({
            asset: policyId + a.asset_name,
            asset_name: a.asset_name,
            quantity: a.total_supply
        }));
    }

    /**
     * Query asset info including on-chain metadata
     */
    async queryAssetInfo(assetId) {
        if (this.mode === 'blockfrost') {
            return this._request(`/assets/${assetId}`);
        } else if (this.mode === 'koios') {
            // Extract policy and asset name
            const policyId = assetId.substring(0, 56);
            const assetName = assetId.substring(56);

            const response = await this._request('/asset_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ _asset_list: [[policyId, assetName]] })
            });

            if (!response || response.length === 0) {
                throw new Error(`Asset not found: ${assetId}`);
            }

            const asset = response[0];
            return {
                asset: assetId,
                asset_name: assetName,
                policy_id: policyId,
                onchain_metadata: asset.minting_tx_metadata?.[721]?.[policyId]?.[asset.asset_name_ascii] || null,
                initial_mint_tx_hash: asset.creation_time ? null : asset.minting_tx_hash
            };
        }
    }

    /**
     * Query asset history to find latest mint
     */
    async queryAssetHistory(assetId, limit = 10) {
        if (this.mode === 'blockfrost') {
            try {
                return await this._request(`/assets/${assetId}/history?order=desc&count=${limit}`);
            } catch (e) {
                if (e.message.includes('404')) return [];
                throw e;
            }
        } else if (this.mode === 'koios') {
            // Koios doesn't have direct asset history, use different approach
            const policyId = assetId.substring(0, 56);
            const assetName = assetId.substring(56);

            const response = await this._request('/asset_history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ _asset_policy: policyId, _asset_name: assetName })
            });

            return (response || []).slice(0, limit).map(h => ({
                tx_hash: h.minting_txs?.[0]?.tx_hash,
                action: h.minting_txs?.[0]?.quantity > 0 ? 'minted' : 'burned'
            }));
        }
    }

    /**
     * Test connection and API key validity
     */
    async testConnection() {
        try {
            if (this.mode === 'blockfrost') {
                await this._request('/health');
            } else if (this.mode === 'koios') {
                const registryAddress = 'addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy';
                await this._request('/address_utxos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ _addresses: [registryAddress] })
                });
            }
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }

    /**
     * Get current blockchain tip
     */
    async getTip() {
        if (this.mode === 'blockfrost') {
            return this._request('/blocks/latest');
        } else if (this.mode === 'koios') {
            const response = await this._request('/tip');
            return response?.[0] || null;
        }
    }
}

// Export for use in other modules
window.BlockchainClient = BlockchainClient;
