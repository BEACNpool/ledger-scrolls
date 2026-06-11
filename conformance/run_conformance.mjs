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

// Decode a CBOR byte string (definite or indefinite length).
function decodeCborBytestring(raw) {
    const readLen = (pos, ai) => {
        if (ai < 24) return [ai, pos];
        const widths = { 24: 1, 25: 2, 26: 4, 27: 8 };
        const w = widths[ai];
        let len = 0n;
        for (let i = 0; i < w; i++) len = (len << 8n) | BigInt(raw[pos + i]);
        return [Number(len), pos + w];
    };
    const mt = raw[0] >> 5, ai = raw[0] & 0x1f;
    if (mt !== 2) throw new Error('not a CBOR byte string');
    if (ai === 31) {
        const chunks = [];
        let pos = 1;
        while (raw[pos] !== 0xff) {
            const cmt = raw[pos] >> 5, cai = raw[pos] & 0x1f;
            if (cmt !== 2 || cai === 31) throw new Error('invalid chunk');
            const [clen, next] = readLen(pos + 1, cai);
            chunks.push(raw.subarray(next, next + clen));
            pos = next + clen;
        }
        return Buffer.concat(chunks);
    }
    const [blen, pos] = readLen(1, ai);
    return raw.subarray(pos, pos + blen);
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
    check(`${v.file} decoded sha256`, sha256Hex(decodeCborBytestring(raw)) === v.decodedSha256);
}

console.log('== cip25 page reconstruction ==');
for (const v of vectors.cip25) {
    const meta = JSON.parse(readFileSync(join(ROOT, v.file), 'utf8'));
    const [decoded, gzRaw] = reconstructCip25Pages(meta, v.policyId);
    check(`${v.file} reconstructed sha256`, sha256Hex(decoded) === v.reconstructedSha256);
    check(`${v.file} gzip sha256`, sha256Hex(gzRaw) === v.gzipSha256);
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
