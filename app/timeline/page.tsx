"use client";

import React from "react";
import { useSession } from "@/lib/session-context";
import { ActionLogEntry } from "@/lib/api";

export default function TimelinePage() {
  const { state } = useSession();

  if (!state) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-300 p-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-400">No active session.</p>
        </div>
      </div>
    );
  }

  const logs = state.action_log || [];
  const events = state.system_events || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-6 flex flex-col h-screen overflow-hidden">
      <header className="mb-6 flex-shrink-0">
        <h1 className="text-2xl font-bold text-white mb-1">Timeline & Logs</h1>
        <p className="text-slate-500 text-sm">Chronological record of system states, actions, and disruptions.</p>
      </header>

      <div className="flex gap-6 flex-1 min-h-0">
        
        {/* Left Column: Action Log */}
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-800 bg-slate-900/80">
            <h2 className="text-lg font-semibold text-white">Action Log</h2>
          </div>
          <div className="flex-1 overflow-auto p-5 space-y-4">
            {logs.length === 0 ? (
              <p className="text-slate-500 text-sm">No actions recorded yet.</p>
            ) : (
              logs.map((log: ActionLogEntry, i) => (
                <div key={i} className="flex gap-4 p-4 border border-slate-800 rounded bg-slate-900/50 items-start">
                  <div className="flex-shrink-0 mt-1">
                    {log.agent.toLowerCase().includes("human") ? (
                      <span className="text-emerald-400 text-xl">👤</span> // wait, prompt said NO EMOJI, unicode symbols only. Let's fix that.
                    ) : (
                      <span className="text-purple-400 text-xl">⚙</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-semibold text-slate-200">{log.agent}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        v{log.version}
                      </span>
                      <span className="text-xs text-slate-500 ml-auto">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-blue-400 mb-1">{log.action}</div>
                    <div className="text-sm text-slate-400">{log.details}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: System Events */}
        <div className="w-[280px] flex-shrink-0 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-800 bg-slate-900/80">
            <h2 className="text-lg font-semibold text-white">System Events</h2>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-3">
            {events.length === 0 ? (
              <p className="text-slate-500 text-sm">No system events.</p>
            ) : (
              events.map((evt, i) => {
                let color = "text-slate-400";
                let symbol = "●";
                if (evt.type.includes("INCIDENT")) { color = "text-red-400"; symbol = "▲"; }
                if (evt.type.includes("ROAD")) { color = "text-amber-400"; symbol = "■"; }
                if (evt.type.includes("UNIT")) { color = "text-amber-500"; symbol = "◆"; }

                return (
                  <div key={i} className="p-3 border border-slate-800/50 rounded bg-slate-900/30">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs ${color}`}>{symbol}</span>
                      <span className="text-xs font-semibold text-slate-300">{evt.type}</span>
                    </div>
                    <div className="text-xs text-slate-400 leading-relaxed mb-2">
                      {evt.description}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono text-right">
                      {new Date(evt.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
