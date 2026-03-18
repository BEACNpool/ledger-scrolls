import React from 'react';
import { motion } from 'framer-motion';

export default function LibraryDrawer({ library, onSelect }) {
  if (!library || library.length === 0) {
    return <div className="text-center text-[var(--text-muted)] py-8">No scrolls available</div>;
  }

  return (
    <div className="flex flex-col gap-3">
      {library.map((scroll, i) => (
        <motion.button
          key={scroll.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(scroll)}
          className="flex items-start text-left gap-4 p-4 rounded-xl border border-[var(--border-glass)] bg-white/5 hover:bg-white/10 hover:border-[var(--accent-gold)] transition-all group"
        >
          <div className="text-2xl mt-1">{scroll.icon || '📜'}</div>
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-lg text-white group-hover:text-[var(--accent-gold)] transition-colors truncate">
              {scroll.title}
            </h4>
            <p className="text-sm text-[var(--text-muted)] mt-1 line-clamp-2 leading-snug">
              {scroll.description}
            </p>
            {scroll.metadata && (
               <div className="flex items-center gap-2 mt-3 text-xs font-mono text-white/40">
                 {scroll.metadata.size && <span>{scroll.metadata.size}</span>}
                 {scroll.metadata.pages && <span>• {scroll.metadata.pages} pages</span>}
               </div>
            )}
          </div>
        </motion.button>
      ))}
    </div>
  );
}
