import pako from 'pako';
import { SCROLL_TYPES } from './scrolls.js';
import CBOR from 'cbor-web';

export class ScrollReconstructor {
    constructor(client) {
        this.client = client;
        this.progressCallback = null;
        this.aborted = false;
    }

    setProgressCallback(callback) {
        this.progressCallback = callback;
    }

    abort() {
        this.aborted = true;
    }

    _progress(message, percent = null) {
        if (this.progressCallback) {
            this.progressCallback(message, percent);
        }
    }

    async reconstruct(scroll) {
        this.aborted = false;
        if (scroll.type === SCROLL_TYPES.STANDARD) {
            return this.reconstructStandard(scroll);
        } else if (scroll.type === SCROLL_TYPES.LEGACY) {
            return this.reconstructLegacy(scroll);
        } else if (scroll.type === SCROLL_TYPES.CHAIN) {
            return this.reconstructChain(scroll);
        } else {
            throw new Error(`Unknown scroll type: ${scroll.type}`);
        }
    }

    // LS-CHAIN v2: manifest inline datum -> explicit page tx list -> bytes.
    // Spec: registry/spec/manifest-chain-v2.md
    async reconstructChain(scroll) {
        const pointer = scroll.pointer;
        this._progress('🔍 Fetching manifest datum...', 5);
        const [txHash, txIndexStr] = pointer.manifest_txin.split('#');
        const utxo = await this.client.queryUtxoByTxIn(txHash, parseInt(txIndexStr));
        if (!utxo?.inline_datum) throw new Error('Manifest UTxO has no inline datum');

        const toBytes = (x) => x instanceof Uint8Array ? x : new Uint8Array(x);
        const td = new TextDecoder();
        const parseManifest = (datumHex) => {
            const decoded = CBOR.decode(this._hexToBytes(datumHex).buffer);
            const tag = decoded?.tag;
            const fields = decoded?.value ?? decoded?.contents;
            if (tag !== 121 || !fields) throw new Error('Not an LS-CHAIN manifest (expected constructor 0)');
            const f = Array.from(fields);
            if (Number(f[0]) !== 2) throw new Error(`Unsupported LS-CHAIN version: ${f[0]}`);
            const nxt = f[7];
            const nxtFields = nxt?.value ?? nxt?.contents;
            return {
                contentType: td.decode(toBytes(f[1])),
                codec: td.decode(toBytes(f[2])),
                sizeDecoded: Number(f[3]),
                sha256Decoded: this._bytesToHex(toBytes(f[4])),
                sha256Encoded: this._bytesToHex(toBytes(f[5])),
                pageTxHashes: Array.from(f[6]).map(h => this._bytesToHex(toBytes(h))),
                next: nxt?.tag === 122 && nxtFields
                    ? `${this._bytesToHex(toBytes(Array.from(nxtFields)[0]))}#${Number(Array.from(nxtFields)[1])}`
                    : null
            };
        };

        this._progress('📜 Decoding manifest...', 10);
        const manifest = parseManifest(utxo.inline_datum);
        const pageHashes = [...manifest.pageTxHashes];
        let next = manifest.next;
        while (next) {
            const [nh, ni] = next.split('#');
            const nu = await this.client.queryUtxoByTxIn(nh, parseInt(ni));
            if (!nu?.inline_datum) throw new Error('Continuation manifest has no inline datum');
            const nm = parseManifest(nu.inline_datum);
            pageHashes.push(...nm.pageTxHashes);
            next = nm.next;
        }

        this._progress(`✓ Manifest lists ${pageHashes.length} pages, fetching...`, 15);
        const metaByTx = await this.client.queryTxMetadataBatch(
            pageHashes,
            (msg, frac) => this._progress(msg, 15 + Math.floor((frac || 0) * 55))
        );

        let allHex = '';
        for (let i = 0; i < pageHashes.length; i++) {
            if (this.aborted) throw new Error('Aborted');
            const meta = metaByTx.get(pageHashes[i]);
            const page = meta?.['22025'] ?? meta?.[22025];
            if (!page?.p) throw new Error(`Page ${i + 1} metadata missing (tx ${pageHashes[i]})`);
            const pageHex = page.p.map(s => this._extractPayloadHex(s)).join('');
            if (page.sha) {
                const got = await this._sha256(this._hexToBytes(pageHex));
                const want = this._extractPayloadHex(page.sha);
                if (got !== want.toLowerCase()) throw new Error(`Page ${i + 1} hash mismatch (tx ${pageHashes[i]})`);
            }
            allHex += pageHex;
        }

        this._progress('🔗 Verifying encoded stream...', 75);
        let rawBytes = this._hexToBytes(allHex);
        if (await this._sha256(rawBytes) !== manifest.sha256Encoded) {
            throw new Error('Encoded stream hash mismatch — refusing to render');
        }
        if (manifest.codec === 'gzip') {
            this._progress('📂 Decompressing (gzip)...', 85);
            rawBytes = pako.inflate(rawBytes);
        }
        this._progress('🔐 Verifying file hash...', 92);
        const hash = await this._sha256(rawBytes);
        if (hash !== manifest.sha256Decoded) {
            throw new Error('Decoded file hash mismatch — refusing to render');
        }

        this._progress('✅ Reconstruction complete!', 100);
        return {
            data: rawBytes,
            contentType: manifest.contentType || pointer.content_type,
            size: rawBytes.length,
            hash: hash,
            verified: true,
            pages: pageHashes.length,
            method: 'Chain Scroll (LS-CHAIN v2)'
        };
    }

    async reconstructStandard(scroll) {
        const pointer = scroll.pointer;
        this._progress('🔍 Querying locked UTxO...', 10);
        const [txHash, txIndexStr] = pointer.lock_txin.split('#');
        const txIndex = parseInt(txIndexStr);

        let utxo;
        try {
            utxo = await this.client.queryUtxoByTxIn(txHash, txIndex);
        } catch {
            this._progress('📍 Querying lock address...', 15);
            const utxos = await this.client.queryUtxosAtAddress(pointer.lock_address);
            utxo = utxos.find(u => u.tx_hash === txHash && u.output_index === txIndex);
        }

        if (!utxo) throw new Error(`UTxO not found: ${pointer.lock_txin}`);
        this._progress('✓ UTxO found, extracting datum...', 30);

        let inlineDatum = utxo.inline_datum;
        let datumHash = utxo.datum_hash;
        if (!inlineDatum) {
            const fresh = await this.client.queryUtxoByTxIn(txHash, txIndex);
            inlineDatum = fresh.inline_datum;
            datumHash = datumHash || fresh.datum_hash;
        }
        if (!inlineDatum && datumHash && this.client.queryDatumByHash) {
            const datumInfo = await this.client.queryDatumByHash(datumHash);
            inlineDatum = datumInfo?.value?.fields?.[0]?.bytes || datumInfo?.value?.bytes || datumInfo?.bytes || null;
        }
        if (!inlineDatum) throw new Error('UTxO does not contain inline datum');

        this._progress('📦 Decoding datum bytes...', 50);
        const hexData = this._extractBytesFromDatum(inlineDatum);
        this._progress('🔄 Converting to binary...', 70);
        let rawBytes = this._hexToBytes(hexData);

        if (pointer.codec === 'gzip') {
            this._progress('📂 Decompressing (gzip)...', 80);
            rawBytes = pako.inflate(rawBytes);
        }

        this._progress('🔐 Verifying integrity...', 90);
        if (pointer.sha256) {
            const computedHash = await this._sha256(rawBytes);
            if (computedHash !== pointer.sha256.toLowerCase()) {
                throw new Error(`Hash mismatch!\nExpected: ${pointer.sha256}\nGot: ${computedHash}`);
            }
        }

        this._progress('✅ Reconstruction complete!', 100);
        return {
            data: rawBytes,
            contentType: pointer.content_type,
            size: rawBytes.length,
            hash: await this._sha256(rawBytes),
            verified: pointer.sha256 ? true : null,
            method: 'Standard Scroll (Locked UTxO)'
        };
    }

    async reconstructLegacy(scroll) {
        const pointer = scroll.pointer;
        this._progress('🔍 Scanning policy assets...', 5);
        if (this.aborted) throw new Error('Aborted');

        const assets = await this.client.queryPolicyAssets(pointer.policy_id, (msg) => this._progress(msg, 10));
        if (!assets || assets.length === 0) throw new Error('No assets found under this policy');

        this._progress(`✓ Found ${assets.length} assets, fetching metadata...`, 20);
        const pages = [];
        const total = assets.length;

        // Track the learned codec and content type from the NFTs
        let activeCodec = pointer.codec;
        let activeContentType = pointer.content_type;

        const assetIds = assets.map(a => a.asset || a);
        const infoMap = await this.client.queryAssetInfos(
            assetIds,
            (msg, frac) => this._progress(msg, 20 + Math.floor((frac || 0) * 40))
        );

        for (let i = 0; i < assetIds.length; i++) {
            if (this.aborted) throw new Error('Aborted');
            const assetId = assetIds[i];
            const progress = 60 + Math.floor((i / total) * 10);
            this._progress(`📄 Processing asset ${i + 1}/${total}...`, progress);

            try {
                const assetNameHex = assetId.substring(56);
                const assetNameAscii = this._hexToAscii(assetNameHex);
                const assetInfo = infoMap.get(assetId) || await this.client.queryAssetInfo(assetId);
                let meta = assetInfo.onchain_metadata;
                
                if (!meta && assetInfo.initial_mint_tx_hash) {
                    const history = await this.client.queryAssetHistory(assetId);
                    const latestMint = history.find(h => h.action === 'minted');
                    const mintTx = latestMint?.tx_hash || assetInfo.initial_mint_tx_hash;
                    if (mintTx) {
                        const txMeta = await this.client.queryTxMetadata(mintTx);
                        const cip25 = txMeta.find(m => m.label === '721');
                        if (cip25) {
                            const policyMeta = cip25.json_metadata?.[pointer.policy_id];
                            if (policyMeta) meta = policyMeta[assetNameAscii] || policyMeta[assetNameHex];
                        }
                    }
                }

                if (!meta) continue;
                
                // Dynamically read compression and media type from any NFT that provides it
                if (meta.codec) activeCodec = meta.codec;
                else if (meta.compression) activeCodec = meta.compression;
                
                if (meta.mediaType) activeContentType = meta.mediaType;
                else if (meta.contentType) activeContentType = meta.contentType;
                else if (meta.mimeType) activeContentType = meta.mimeType;

                const isManifest = (
                    meta.role === 'manifest' ||
                    assetId.toLowerCase().includes('manifest') ||
                    (meta.pages && Array.isArray(meta.pages))
                );
                if (isManifest) continue;

                if (meta.payload !== undefined && meta.i !== undefined) {
                    if (pointer.manifest_asset) {
                        const pagePrefix = pointer.manifest_asset.replace(/_MANIFEST$/i, '_PAGE');
                        const assetName = assetNameAscii;
                        if (!assetName || !assetName.startsWith(pagePrefix)) continue;
                    }
                    pages.push({ index: parseInt(meta.i), payload: meta.payload, assetId: assetId });
                }
            } catch (e) {
                console.warn(`Failed to process asset ${assetId}:`, e);
            }
        }

        if (pages.length === 0) throw new Error('No page NFTs found with payload and index fields');
        this._progress(`✓ Found ${pages.length} pages, reconstructing...`, 75);

        pages.sort((a, b) => a.index - b.index);
        this._progress('🔗 Concatenating page payloads...', 80);
        let allHex = '';
        for (const page of pages) {
            allHex += this._extractPayloadHex(page.payload);
        }

        this._progress('🔄 Converting to binary...', 85);
        let rawBytes = this._hexToBytes(allHex);
        const isGzipped = rawBytes.length >= 2 && rawBytes[0] === 0x1f && rawBytes[1] === 0x8b;
        
        if (activeCodec === 'gzip' || (activeCodec === 'auto' && isGzipped) || isGzipped) {
            this._progress('📂 Decompressing (gzip detected)...', 90);
            try { rawBytes = pako.inflate(rawBytes); } catch (e) { console.warn('Decompression failed, using raw bytes:', e); }
        }

        let contentType = activeContentType;
        const textPreview = new TextDecoder().decode(rawBytes.slice(0, 100)).toLowerCase();
        if (textPreview.includes('<!doctype') || textPreview.includes('<html')) {
            contentType = 'text/html';
        }

        this._progress('🔐 Computing integrity hash...', 95);
        const hash = await this._sha256(rawBytes);

        const expectedHash = pointer.sha256_original || pointer.sha256 || null;
        let verified = null;
        if (expectedHash) {
            verified = hash === expectedHash.toLowerCase();
            if (!verified) {
                console.warn(`Hash mismatch!\nExpected: ${expectedHash}\nGot: ${hash}`);
            }
        }

        this._progress('✅ Reconstruction complete!', 100);
        return {
            data: rawBytes,
            contentType: contentType,
            size: rawBytes.length,
            hash: hash,
            verified: verified,
            pages: pages.length,
            method: 'Legacy Scroll (CIP-25 Pages)'
        };
    }

    _extractBytesFromDatum(datum) {
        if (typeof datum === 'string') {
            try {
                const cborBytes = this._hexToBytes(datum);
                const decoded = CBOR.decode(cborBytes);
                
                const plutusField = this._extractPlutusConstructorField(decoded);
                if (plutusField) return this._bytesToHex(plutusField);

                if (Array.isArray(decoded) && decoded.length >= 2) {
                    const fields = decoded[1];
                    if (Array.isArray(fields) && fields.length > 0) {
                        const firstField = fields[0];
                        if (firstField instanceof Uint8Array) return this._bytesToHex(firstField);
                        else if (typeof firstField === 'string') return firstField;
                    }
                }
                
                if (decoded instanceof Uint8Array) return this._bytesToHex(decoded);
                throw new Error('Unexpected CBOR datum structure');
            } catch {
                return datum;
            }
        }

        if (typeof datum === 'object' && datum !== null) {
            if (datum.bytes) return datum.bytes;
            if (datum.value?.fields?.[0]?.bytes) return datum.value.fields[0].bytes;
            if (datum.value?.bytes) return datum.value.bytes;
            if (datum.fields && Array.isArray(datum.fields)) {
                const bytesField = datum.fields[0]?.bytes;
                if (bytesField) return bytesField;
            }
        }
        
        throw new Error(`Cannot extract bytes from datum: ${typeof datum}`);
    }

    _extractPlutusConstructorField(decoded) {
        const fields = decoded?.value;
        if (!Array.isArray(fields) || fields.length === 0) return null;
        const firstField = fields[0];
        if (firstField instanceof Uint8Array) return firstField;
        if (ArrayBuffer.isView(firstField)) return new Uint8Array(firstField.buffer, firstField.byteOffset, firstField.byteLength);
        return null;
    }

    _extractPayloadHex(payload) {
        let hex = '';
        if (Array.isArray(payload)) {
            for (const entry of payload) {
                if (typeof entry === 'object' && entry.bytes) hex += entry.bytes.replace(/^0x/i, '');
                else if (typeof entry === 'string') hex += entry.replace(/^0x/i, '');
            }
        } else if (typeof payload === 'string') {
            hex = payload.replace(/^0x/i, '');
        }
        return hex.replace(/\s/g, '');
    }

    _hexToBytes(hex) {
        hex = hex.replace(/^0x/i, '').replace(/\s/g, '');
        if (hex.length % 2 !== 0) throw new Error(`Invalid hex string length: ${hex.length}`);
        const bytes = new Uint8Array(hex.length / 2);
        for (let i = 0; i < hex.length; i += 2) {
            bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
        }
        return bytes;
    }

    _bytesToHex(bytes) {
        return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
    }

    _hexToAscii(hex) {
        let str = '';
        for (let i = 0; i < hex.length; i += 2) {
            str += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
        }
        return str;
    }

    async _sha256(data) {
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        return Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
    }
}
