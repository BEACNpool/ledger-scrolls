import React from 'react';
import { Download, ShieldCheck, ArrowLeft, Loader2, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ViewerArea({ 
  currentScroll, 
  onBack,
  loadingScroll,
  scrollData,
  scrollProgress,
  scrollError,
  cancelLoading
}) {
  if (!currentScroll) {
    return (
      <main className="flex-1 mt-16 mb-16 md:mb-0 flex flex-col items-center justify-center min-h-screen">
        <div className="text-center p-8 max-w-md">
          <div className="text-6xl mb-6 opacity-80">📜</div>
          <h2 className="text-3xl font-serif text-[var(--accent-gold)] mb-4">A Library That Cannot Burn</h2>
          <p className="text-[var(--text-muted)] leading-relaxed text-lg">
            Select a scroll from the definitive archive to witness immutable truths stored forever on the blockchain.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 mt-16 mb-16 md:mb-0 relative flex flex-col items-center">
      {/* Scroll Title Bar */}
      <div className="w-full glass-panel border-b sticky top-16 z-30 px-4 py-3 flex items-center justify-between">
        <button 
          onClick={onBack}
          className="p-2 hover:bg-white/10 rounded-full transition-colors text-[var(--text-muted)] hover:text-[var(--accent-gold)]"
        >
          <ArrowLeft size={20} />
        </button>
        <h2 className="text-xl font-serif text-[var(--accent-gold)] mx-4 truncate flex-1 text-center font-medium tracking-wide">
          {currentScroll.title}
        </h2>
        <div className="flex gap-2">
          <button className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/50 hover:text-white" title="Download">
            <Download size={20} />
          </button>
          <button className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/50 hover:text-green-400" title="Verify">
            <ShieldCheck size={20} />
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {loadingScroll ? (
          <motion.div 
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 flex flex-col items-center justify-center min-h-[60vh] p-8 w-full max-w-md mx-auto"
          >
            <div className="relative w-32 h-32 mb-8 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-white/5 border-t-[var(--accent-gold)] animate-spin"></div>
              <div className="text-4xl animate-pulse">📜</div>
            </div>
            <h3 className="text-2xl font-serif text-white mb-2">Unfurling Scroll...</h3>
            <p className="text-[var(--accent-gold)] font-mono text-sm h-6">
              {scrollProgress.message}
            </p>
            
            {/* Progress Bar */}
            <div className="w-full h-1 bg-white/10 rounded-full mt-6 overflow-hidden">
               <motion.div 
                 className="h-full bg-[var(--accent-gold)]"
                 initial={{ width: 0 }}
                 animate={{ width: `${scrollProgress.percent || 0}%` }}
               />
            </div>
            
            <button 
              onClick={cancelLoading}
              className="mt-8 px-6 py-2 rounded-full border border-white/20 text-white/60 hover:text-white hover:border-white/40 transition-colors"
            >
              Cancel
            </button>
          </motion.div>
        ) : scrollError ? (
          <motion.div 
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex-1 flex flex-col items-center justify-center min-h-[60vh] p-8 text-center"
          >
             <XCircle size={48} className="text-red-500 mb-4" />
             <h3 className="text-xl text-white mb-2">Scroll Unreadable</h3>
             <p className="text-red-400 font-mono text-sm max-w-lg bg-red-500/10 p-4 rounded-xl border border-red-500/20 break-words">
                {scrollError}
             </p>
             <button 
               onClick={onBack}
               className="mt-8 px-6 py-2 rounded-full border border-white/20 hover:bg-white/10 transition-colors"
             >
               Return to Library
             </button>
          </motion.div>
        ) : scrollData ? (
          <motion.div 
            key="content"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full flex-1 flex flex-col max-w-[1200px]"
          >
            {scrollData.contentType === 'text/html' ? (
               <iframe 
                 src={scrollData.renderUrl} 
                 className="w-full h-[80vh] border-0 bg-white" 
                 title="Document Content"
               />
            ) : scrollData.contentType.startsWith('image/') ? (
               <div className="p-8 flex justify-center">
                 <img src={scrollData.renderUrl} alt={currentScroll.title} className="max-w-full h-auto rounded shadow-2xl" />
               </div>
            ) : scrollData.contentType.startsWith('video/') ? (
               <div className="p-8 flex justify-center">
                 <video src={scrollData.renderUrl} controls className="max-w-full rounded shadow-2xl" />
               </div>
            ) : (
               <div className="w-full max-w-4xl mx-auto p-6 md:p-12 min-h-screen bg-[#F4F1E1] text-[#2C2825] font-serif shadow-2xl my-8 whitespace-pre-wrap">
                 {scrollData.renderText}
               </div>
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </main>
  );
}
