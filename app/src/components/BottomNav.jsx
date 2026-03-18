import React from 'react';
import { BookOpen, Settings, Info } from 'lucide-react';

export default function BottomNav({ onOpenDrawer }) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 h-16 glass-panel border-t flex justify-around items-center px-4 z-40">
      <button
        onClick={() => onOpenDrawer('about')}
        className="flex flex-col items-center justify-center w-16 h-full text-[var(--text-muted)] hover:text-[var(--accent-gold)] transition-colors"
        aria-label="About"
      >
        <Info size={24} />
      </button>

      <button
        onClick={() => onOpenDrawer('library')}
        className="flex flex-col items-center justify-center px-6 h-12 bg-white/5 border border-[var(--border-glass)] rounded-2xl text-[var(--text-primary)] hover:bg-white/10 hover:border-[var(--accent-gold)] transition-all"
        aria-label="Open Library"
      >
        <div className="flex items-center gap-2">
          <BookOpen size={20} className="text-[var(--accent-gold)]" />
          <span className="font-semibold tracking-wide">Library</span>
        </div>
      </button>

      <button
        onClick={() => onOpenDrawer('settings')}
        className="flex flex-col items-center justify-center w-16 h-full text-[var(--text-muted)] hover:text-[var(--accent-gold)] transition-colors"
        aria-label="Settings"
      >
        <Settings size={24} />
      </button>
    </nav>
  );
}
