"use client";

import React from "react";
import { ExplanationResponse } from "@/lib/api";

interface AICommandBriefProps {
  explanation: ExplanationResponse | null;
}

export default function AICommandBrief({ explanation }: AICommandBriefProps) {
  if (!explanation) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-center text-sm text-slate-500 font-sans">
        Generate plans to see AI analysis
      </div>
    );
  }

  const isGemini = explanation.explanation_source === "gemini";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col gap-4 text-sm font-sans">
      <div className="flex justify-between items-center border-b border-slate-800 pb-2">
        <h3 className="text-slate-100 font-semibold flex items-center gap-2">
          ◆ AI COMMAND BRIEF
        </h3>
        <div className="flex items-center gap-2">
          {explanation.gemini_status === "connected" ? (
            <span className="text-emerald-400 text-xs">● Connected</span>
          ) : (
            <span className="text-amber-400 text-xs">● Degraded</span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded border ${isGemini ? 'bg-purple-900/30 text-purple-400 border-purple-800' : 'bg-slate-800 text-slate-400 border-slate-700'}`}>
            {isGemini ? 'Gemini' : 'Deterministic Fallback'}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div>
          <div className="text-xs font-semibold text-slate-500 mb-1">WHY THIS PLAN</div>
          <div className="text-slate-300">{explanation.why}</div>
        </div>

        {explanation.tradeoff && (
          <div>
            <div className="text-xs font-semibold text-slate-500 mb-1">TRADE-OFF</div>
            <div className="text-amber-400/90">{explanation.tradeoff}</div>
          </div>
        )}

        {explanation.risk && (
          <div>
            <div className="text-xs font-semibold text-slate-500 mb-1">RISK</div>
            <div className="text-red-400/90">{explanation.risk}</div>
          </div>
        )}

        {explanation.what_changed && (
          <div>
            <div className="text-xs font-semibold text-slate-500 mb-1">WHAT CHANGED</div>
            <div className="text-blue-400/90">{explanation.what_changed}</div>
          </div>
        )}

        <div>
          <div className="text-xs font-semibold text-slate-500 mb-1">SUMMARY</div>
          <div className="text-slate-300 font-medium">{explanation.summary}</div>
        </div>
      </div>

      <div className="mt-4 pt-2 border-t border-slate-800 text-[10px] text-slate-600 uppercase tracking-wider text-right">
        {explanation.boundary_note}
      </div>
    </div>
  );
}
