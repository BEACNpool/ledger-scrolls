import React from 'react';
import { ScrollText } from 'lucide-react';

export default function Header({ isOnline }) {
  return (
    <header className="flex items-center justify-between p-4 glass-panel border-b z-50 fixed top-0 w-full h-16">
      <div className="flex items-center gap-3">
        <div className="text-[28px] leading-none mb-1">📜</div>
        <div className="flex flex-col justify-center">
          <h1 className="text-xl font-semibold tracking-wide m-0 leading-tight">Ledger Scrolls</h1>
          <div className="font-mono text-[10px] text-[var(--text-muted)] mt-[-2px]">v2.0 UI React</div>
        </div>
      </div>

      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-[var(--border-glass)]">
        <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`}></div>
        <span className="text-sm text-[var(--text-muted)] font-medium">
          {isOnline ? 'Connected' : 'Offline'}
        </span>
      </div>
    </header>
  );
}
