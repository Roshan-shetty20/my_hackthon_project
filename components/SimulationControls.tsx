'use client';

import React, { useState, useEffect } from 'react';
import { useSession } from '@/lib/session-context';

export default function SimulationControls() {
  const { isDemoMode, tickTime, simulateStep, loading } = useSession();
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        if (!loading) {
          tickTime();
        }
      }, 3000); // Auto-tick every 3 seconds
    }
    return () => clearInterval(interval);
  }, [isPlaying, tickTime, loading]);

  return (
    <div className="flex items-center gap-2 p-2 bg-slate-900 border-t border-slate-800">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-4">Simulation</div>
      
      <button
        onClick={() => setIsPlaying(!isPlaying)}
        className={`px-3 py-1.5 rounded text-sm font-medium transition-colors border flex items-center gap-2 ${
          isPlaying 
            ? 'bg-amber-500/20 text-amber-400 border-amber-500/50 hover:bg-amber-500/30' 
            : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50 hover:bg-emerald-500/30'
        }`}
      >
        {isPlaying ? '■ PAUSE' : '▶ PLAY'}
      </button>

      <button
        onClick={() => tickTime()}
        disabled={loading}
        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-sm font-medium transition-colors disabled:opacity-50"
      >
        ADVANCE TICK
      </button>

      {isDemoMode && (
        <button
          onClick={() => simulateStep()}
          disabled={loading}
          className="px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 border border-purple-600/50 rounded text-sm font-medium transition-colors disabled:opacity-50 ml-auto"
        >
          NEXT SCENARIO EVENT
        </button>
      )}
    </div>
  );
}
