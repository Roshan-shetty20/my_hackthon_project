"use client";

import React, { useMemo } from "react";
import { CrisisStateResponse } from "@/lib/api";

interface EventTimelineProps {
  state: CrisisStateResponse | null;
}

export default function EventTimeline({ state }: EventTimelineProps) {
  const mergedEvents = useMemo(() => {
    if (!state) return [];
    
    const actions = (state.action_log || []).map((a) => ({
      id: `${a.timestamp}-${a.action}-${a.agent}`,
      timestamp: new Date(a.timestamp).getTime(),
      timeStr: a.timestamp,
      version: a.version,
      agent: a.agent,
      type: 'action',
      title: a.action,
      details: a.details,
    }));

    const systems = (state.system_events || []).map((s) => ({
      id: s.id || `${s.timestamp}-${s.type}`,
      timestamp: new Date(s.timestamp).getTime(),
      timeStr: s.timestamp,
      version: state.version, // fallback
      agent: 'SYSTEM',
      type: 'system',
      title: s.type,
      details: s.description,
    }));

    return [...actions, ...systems].sort((a, b) => b.timestamp - a.timestamp);
  }, [state]);

  if (!state || mergedEvents.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-center text-sm text-slate-500 font-sans">
        No events recorded
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-sans flex flex-col h-full">
      <h3 className="text-slate-100 font-semibold mb-4 text-sm flex items-center gap-2">
        ▶ EVENT TIMELINE
      </h3>
      
      <div className="flex flex-col gap-3 overflow-y-auto max-h-[400px] pr-2 scrollbar-thin scrollbar-thumb-slate-700">
        {mergedEvents.map((ev, idx) => {
          let agentColor = "text-slate-400";
          let agentIcon = "■";
          let badgeColor = "bg-slate-800 text-slate-300 border-slate-700";

          if (ev.agent.includes("Commander") || ev.agent.includes("USER")) {
            agentColor = "text-emerald-400";
            agentIcon = "▲";
            badgeColor = "bg-emerald-950 text-emerald-400 border-emerald-900";
          } else if (ev.agent.includes("Planner")) {
            agentColor = "text-blue-400";
            agentIcon = "◆";
            badgeColor = "bg-blue-950 text-blue-400 border-blue-900";
          } else if (ev.type === 'system' || ev.title.includes("DISRUPTION")) {
            agentColor = "text-amber-400";
            agentIcon = "●";
            badgeColor = "bg-amber-950 text-amber-400 border-amber-900";
          }

          const timeFormatted = new Date(ev.timestamp).toLocaleTimeString([], { hour12: false });

          return (
            <div key={`${ev.id}-${idx}`} className="flex gap-3 text-sm border-l-2 border-slate-800 pl-3 py-1 relative">
              <div className={`absolute -left-[9px] top-1.5 w-4 h-4 bg-slate-900 rounded-full flex items-center justify-center ${agentColor} text-[10px]`}>
                {agentIcon}
              </div>
              <div className="flex flex-col gap-1 w-full">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 text-xs font-mono">{timeFormatted}</span>
                    <span className={`${agentColor} font-semibold text-xs`}>{ev.agent}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${badgeColor}`}>
                      v{ev.version}
                    </span>
                  </div>
                </div>
                <div className="text-slate-200 font-medium">{ev.title}</div>
                {ev.details && (
                  <div className="text-slate-400 text-xs leading-relaxed">{ev.details}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
