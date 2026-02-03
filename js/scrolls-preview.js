/**
 * Ledger Scrolls v2.0 - Preview Testnet Scroll Definitions
 * 
 * Preview testnet PoC scrolls (Blockfrost-only).
 */

const SCROLL_TYPES = {
    STANDARD: 'utxo_datum_bytes_v1',
    LEGACY: 'cip25_pages_v1'
};

const CATEGORIES = {
    ALL: { id: 'all', name: 'All Scrolls', icon: '📚' },
    PREVIEW: { id: 'preview', name: 'Preview Testnet', icon: '🧪' },
    AUDIO: { id: 'audio', name: 'Audio', icon: '🔊' },
    VIDEO: { id: 'video', name: 'Video', icon: '🎬' }
};

const SCROLLS = [
    {
        id: 'epic-audio-preview',
        title: 'Epic Audio Scroll (Preview)',
        description: 'PoC epic audio scroll on Cardano preview testnet — a chain of evidence, for all time.',
        icon: '🔊',
        category: 'audio',
        type: SCROLL_TYPES.LEGACY,
        pointer: {
            policy_id: 'e41a8acf867853aa0a8989077790f05a80baf036c7303d0392c87077',
            manifest_tx_hash: 'e04078a270b8533c93da9fd32b213ad6c3e17f881ff38fbb88cb02f4ad7a705b',
            manifest_asset: 'EA_MANIFEST',
            content_type: 'audio/opus',
            codec: 'none',
            sha256: '7ed1eba42a179bae13d630dd0d8451734afe0cc67d5741e8a1176584a50c0f5e'
        },
        metadata: {
            network: 'Preview Testnet (magic: 2)',
            pages: 9,
            manifest_asset: 'EA_MANIFEST',
            minted_by: 'BEACNpool',
            policy_id: 'e41a8acf867853aa0a8989077790f05a80baf036c7303d0392c87077'
        }
    },
    {
        id: 'epic-video-preview',
        title: 'Epic Video Scroll (Preview)',
        description: 'PoC epic video scroll on Cardano preview testnet — CARDANO: A CHAIN OF EVIDENCE.',
        icon: '🎬',
        category: 'video',
        type: SCROLL_TYPES.LEGACY,
        pointer: {
            policy_id: 'e41a8acf867853aa0a8989077790f05a80baf036c7303d0392c87077',
            manifest_tx_hash: 'b3cd183fb48cc3a25927644e9424be61f69f23c9d37c63a6f67795043adfac4e',
            manifest_asset: 'EV_MANIFEST',
            content_type: 'video/mp4',
            codec: 'none',
            sha256: 'f33f690c66ea08bf00fd24cb9071af10ca59f4f70c15977d7b3c7a847786318b'
        },
        metadata: {
            network: 'Preview Testnet (magic: 2)',
            pages: 17,
            manifest_asset: 'EV_MANIFEST',
            minted_by: 'BEACNpool',
            policy_id: 'e41a8acf867853aa0a8989077790f05a80baf036c7303d0392c87077'
        }
    }
];

const REGISTRY = null;

function getAllScrolls() {
    return SCROLLS;
}

function getScrollById(id) {
    return SCROLLS.find(s => s.id === id);
}

function getScrollsByCategory(category) {
    if (category === 'all') return SCROLLS;
    return SCROLLS.filter(s => s.category === category);
}

function searchScrolls(query) {
    if (!query) return SCROLLS;
    const q = query.toLowerCase();
    return SCROLLS.filter(s =>
        s.title.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q)
    );
}

function getCategoriesWithCounts() {
    const counts = {};
    SCROLLS.forEach(s => { counts[s.category] = (counts[s.category] || 0) + 1; });
    return Object.values(CATEGORIES).map(cat => ({
        ...cat,
        count: cat.id === 'all' ? SCROLLS.length : (counts[cat.id] || 0)
    }));
}

window.ScrollLibrary = {
    SCROLL_TYPES,
    CATEGORIES,
    SCROLLS,
    REGISTRY,
    getAllScrolls,
    getScrollById,
    getScrollsByCategory,
    searchScrolls,
    getCategoriesWithCounts
};
