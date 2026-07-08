#!/usr/bin/env node
// Ledger Scrolls conformance runner (Node, stdlib only).
// Runs the same fixture corpus as run_conformance.py so the JS and Python
// implementations stay byte-compatible.
//
// Usage: node conformance/run_conformance.mjs

import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(fileURLToPath(import.meta.url));

let passes = 0;
const failures = [];

function check(label, ok, detail = '') {
    if (ok) {
        passes++;
        console.log(`  PASS  ${label}`);
    } else {
        failures.push(label);
        console.log(`  FAIL  ${label}  ${detail}`);
    }
}

const sha256Hex = (buf) => createHash('sha256').update(buf).digest('hex');

// Canonical JSON: stable key ordering, no insignificant whitespace.
function canonicalJson(value) {
    if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
    if (value !== null && typeof value === 'object') {
        const keys = Object.keys(value).sort();
        return `{${keys.map(k => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(',')}}`;
    }
    return JSON.stringify(value);
}

function readCborLen(raw, pos, ai) {
    if (ai < 24) return [ai, pos];
    const widths = { 24: 1, 25: 2, 26: 4, 27: 8 };
    const w = widths[ai];
    let len = 0n;
    for (let i = 0; i < w; i++) len = (len << 8n) | BigInt(raw[pos + i]);
    return [Number(len), pos + w];
}

// Decode a CBOR byte string (definite or indefinite length) at pos.
function decodeCborBytestringAt(raw, pos = 0) {
    const mt = raw[pos] >> 5, ai = raw[pos] & 0x1f;
    pos++;
    if (mt !== 2) throw new Error('not a CBOR byte string');
    if (ai === 31) {
        const chunks = [];
        while (raw[pos] !== 0xff) {
            const cmt = raw[pos] >> 5, cai = raw[pos] & 0x1f;
            if (cmt !== 2 || cai === 31) throw new Error('invalid chunk');
            const [clen, next] = readCborLen(raw, pos + 1, cai);
            chunks.push(raw.subarray(next, next + clen));
            pos = next + clen;
        }
        return [Buffer.concat(chunks), pos + 1];
    }
    const [blen, next] = readCborLen(raw, pos, ai);
    return [raw.subarray(next, next + blen), next + blen];
}

function decodeStandardDatumBytes(raw) {
    // Bare CBOR bytestring, or Plutus constructor-0/tag-121 with one bytes
    // field from cardano-cli ScriptData JSON.
    if (raw[0] === 0xd8 && raw[1] === 0x79) {
        let pos = 2;
        if (raw[pos] !== 0x9f) throw new Error('expected indefinite constructor field array');
        const [decoded, next] = decodeCborBytestringAt(raw, pos + 1);
        if (raw[next] !== 0xff) throw new Error('expected constructor array break');
        return decoded;
    }
    return decodeCborBytestringAt(raw, 0)[0];
}

const cleanSegment = (seg) => {
    // Segments appear as plain hex strings or as {"bytes": "<hex>"} objects
    if (seg !== null && typeof seg === 'object') seg = seg.bytes ?? seg.seg ?? '';
    seg = String(seg).trim();
    return seg.toLowerCase().startsWith('0x') ? seg.slice(2) : seg;
};

function reconstructCip25Pages(metadata721, policyId) {
    const policyMeta = metadata721['721'][policyId];
    const pages = [];
    for (const [assetName, meta] of Object.entries(policyMeta)) {
        if (meta.role === 'manifest' || assetName.toUpperCase().includes('MANIFEST')) continue;
        if (meta.payload === undefined || meta.i === undefined) continue;
        pages.push([Number(meta.i), meta.payload]);
    }
    pages.sort((a, b) => a[0] - b[0]);
    const hexBlob = pages.flatMap(([, payload]) => payload.map(cleanSegment)).join('');
    const raw = Buffer.from(hexBlob, 'hex');
    if (raw[0] === 0x1f && raw[1] === 0x8b) return [gunzipSync(raw), raw];
    return [raw, raw];
}

// Minimal generic CBOR decoder (uint/nint/bytes/text/array/tag) for
// LS-CHAIN manifests. Returns [value, nextPos]; tags -> {tag, value}.
function decodeCbor(raw, pos = 0) {
    const readLen = (ai, p) => {
        if (ai < 24) return [ai, p];
        const w = { 24: 1, 25: 2, 26: 4, 27: 8 }[ai];
        let n = 0;
        for (let i = 0; i < w; i++) n = n * 256 + raw[p + i];
        return [n, p + w];
    };
    const mt = raw[pos] >> 5, ai = raw[pos] & 0x1f;
    if (mt === 0) return readLen(ai, pos + 1);
    if (mt === 1) { const [n, p] = readLen(ai, pos + 1); return [-1 - n, p]; }
    if (mt === 2 || mt === 3) {
        const [n, p] = readLen(ai, pos + 1);
        const v = raw.subarray(p, p + n);
        return [mt === 2 ? v : Buffer.from(v).toString('utf8'), p + n];
    }
    if (mt === 4) {
        let [n, p] = readLen(ai, pos + 1);
        const out = [];
        for (let i = 0; i < n; i++) { const [v, q] = decodeCbor(raw, p); out.push(v); p = q; }
        return [out, p];
    }
    if (mt === 6) {
        const [n, p] = readLen(ai, pos + 1);
        const [v, q] = decodeCbor(raw, p);
        return [{ tag: n, value: v }, q];
    }
    throw new Error(`unsupported CBOR major type ${mt}`);
}

/* Reconstruct a scroll from its head manifest, following `next` pointers
   (field 7: Constr 0 [] = end, Constr 1 [txHash, ix] = continuation).
   manifestsByPtr maps "txhash#ix" -> manifest hex for continuation parts. */
function reconstructChain(manifestHex, pagesByTx, manifestsByPtr = {}) {
    let info = null;
    const hashes = [];
    let cur = manifestHex;
    let parts = 0;
    for (;;) {
        const [m] = decodeCbor(Buffer.from(cur, 'hex'));
        if (m.tag !== 121) throw new Error('manifest must be Constr 0');
        const f = m.value;
        parts++;
        if (!info) {
            info = {
                version: f[0],
                contentType: Buffer.from(f[1]).toString('utf8'),
                codec: Buffer.from(f[2]).toString('utf8'),
                sizeDecoded: f[3],
                sha256Decoded: Buffer.from(f[4]).toString('hex'),
                sha256Encoded: Buffer.from(f[5]).toString('hex'),
            };
        } else if (f[0] !== info.version
            || Buffer.from(f[1]).toString('utf8') !== info.contentType
            || Buffer.from(f[4]).toString('hex') !== info.sha256Decoded) {
            throw new Error('continuation file fields mismatch');
        }
        for (const h of f[6]) hashes.push(Buffer.from(h).toString('hex'));
        const nxt = f.length > 7 ? f[7] : null;
        if (nxt && nxt.tag === 122 && Array.isArray(nxt.value) && nxt.value.length) {
            const key = `${Buffer.from(nxt.value[0]).toString('hex')}#${nxt.value[1]}`;
            if (!manifestsByPtr[key]) throw new Error('continuation manifest missing: ' + key);
            cur = manifestsByPtr[key];
            if (parts > 32) throw new Error('manifest chain too long');
        } else break;
    }
    info.pageTxHashes = hashes;
    info.parts = parts;
    const chunks = [];
    for (const tx of info.pageTxHashes) {
        const page = pagesByTx[tx]['22025'];
        const payload = Buffer.concat(page.p.map(s => Buffer.from(cleanSegment(s), 'hex')));
        if (sha256Hex(payload) !== cleanSegment(page.sha)) throw new Error('page sha mismatch');
        chunks.push(payload);
    }
    const encoded = Buffer.concat(chunks);
    const decoded = info.codec === 'gzip' ? gunzipSync(encoded) : encoded;
    return [info, encoded, decoded];
}

const POINTER_RULES = {
    'utxo-inline-datum-bytes-v1': { txHash: /^[0-9a-fA-F]{64}$/, txIx: 'number' },
    'cip25-pages-v1': { policyId: /^[0-9a-fA-F]{56}$/ },
    'url': { url: 'string' },
    // Deprecated aliases readers may still accept
    'utxo-locked-bytes': { txin: /^[0-9a-fA-F]{64}#[0-9]+$/ },
    'asset-manifest': { policyId: 'string', assetName: 'string' },
};

function pointerIsValid(pointer) {
    if (pointer === null || typeof pointer !== 'object') return false;
    const rules = POINTER_RULES[pointer.kind];
    if (!rules) return false;
    for (const [field, rule] of Object.entries(rules)) {
        const value = pointer[field];
        if (value === undefined || value === null) return false;
        if (rule instanceof RegExp) {
            if (typeof value !== 'string' || !rule.test(value)) return false;
        } else if (typeof value !== rule) {
            return false;
        }
    }
    return true;
}

const manifest = JSON.parse(readFileSync(join(ROOT, 'manifest.json'), 'utf8'));
const vectors = manifest.vectors;

console.log('== payload vectors ==');
for (const v of vectors.payloads) {
    const data = readFileSync(join(ROOT, v.file));
    check(`${v.file} sha256`, sha256Hex(data) === v.sha256);
    if (v.codec === 'gzip') {
        check(`${v.file} gunzip sha256`, sha256Hex(gunzipSync(data)) === v.decodedSha256);
    }
}

console.log('== standard scroll datums ==');
for (const v of vectors.datums) {
    const raw = Buffer.from(readFileSync(join(ROOT, v.file), 'utf8').trim(), 'hex');
    check(`${v.file} decoded sha256`, sha256Hex(decodeStandardDatumBytes(raw)) === v.decodedSha256);
}

console.log('== cip25 page reconstruction ==');
for (const v of vectors.cip25) {
    const meta = JSON.parse(readFileSync(join(ROOT, v.file), 'utf8'));
    const [decoded, gzRaw] = reconstructCip25Pages(meta, v.policyId);
    check(`${v.file} reconstructed sha256`, sha256Hex(decoded) === v.reconstructedSha256);
    check(`${v.file} gzip sha256`, sha256Hex(gzRaw) === v.gzipSha256);
}

console.log('== ls-chain v2 ==');
for (const v of vectors.chain ?? []) {
    const mhex = readFileSync(join(ROOT, v.manifest), 'utf8').trim();
    const pages = JSON.parse(readFileSync(join(ROOT, v.pages), 'utf8'));
    const conts = Object.fromEntries(Object.entries(v.manifests ?? {})
        .map(([ptr, path]) => [ptr, readFileSync(join(ROOT, path), 'utf8').trim()]));
    const [info, encoded, decoded] = reconstructChain(mhex, pages, conts);
    check(`${v.manifest} fields`, info.contentType === v.contentType
        && info.codec === v.codec && info.pageTxHashes.length === v.pageCount
        && info.parts === (v.parts ?? 1));
    check(`${v.manifest} encoded sha256`, sha256Hex(encoded) === v.encodedSha256
        && info.sha256Encoded === v.encodedSha256);
    check(`${v.manifest} decoded sha256`, sha256Hex(decoded) === v.reconstructedSha256
        && info.sha256Decoded === v.reconstructedSha256
        && decoded.length === info.sizeDecoded);
}

console.log('== pointers ==');
const validDir = join(ROOT, vectors.pointers.validDir);
for (const f of readdirSync(validDir).sort()) {
    const p = JSON.parse(readFileSync(join(validDir, f), 'utf8'));
    check(`valid pointer accepted: ${f}`, pointerIsValid(p));
}
const invalidDir = join(ROOT, vectors.pointers.invalidDir);
for (const f of readdirSync(invalidDir).sort()) {
    const p = JSON.parse(readFileSync(join(invalidDir, f), 'utf8'));
    check(`invalid pointer rejected: ${f}`, !pointerIsValid(p));
}

console.log('== registry canonical hashing ==');
for (const v of vectors.registry) {
    const obj = JSON.parse(readFileSync(join(ROOT, v.file), 'utf8'));
    check(`${v.file} canonical sha256`, sha256Hex(Buffer.from(canonicalJson(obj), 'utf8')) === v.canonicalSha256);
}

console.log();
console.log(`${passes} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
