"use client";

import React, { useState } from "react";
import { useSession } from "@/lib/session-context";
import PlanCard from "@/components/PlanCard";
import AICommandBrief from "@/components/AICommandBrief";
import PlanDiffView from "@/components/PlanDiffView";
import { Plan } from "@/lib/api";

export default function PlansPage() {
  const { state, generatePlans, explanation } = useSession();
  const [sortMode, setSortMode] = useState<"NEAREST_FIRST" | "SEVERITY_FIRST" | "BALANCED">("BALANCED");

  if (!state) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-300 p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-slate-400">No active session.</p>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded">
            Start Session
          </button>
        </div>
      </div>
    );
  }

  const plans = state.candidate_plans || [];

  if (plans.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-300 p-8 flex items-center justify-center">
        <div className="text-center space-y-6">
          <p className="text-slate-400 text-lg">No response plans available.</p>
          <button 
            onClick={() => generatePlans()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium flex items-center gap-2 mx-auto"
          >
            <span>⚙</span> GENERATE RESPONSE PLANS
          </button>
        </div>
      </div>
    );
  }

  const sortedPlans = [...plans].sort((a, b) => {
    if (sortMode === "NEAREST_FIRST") {
      return (a.metrics?.average_eta || 0) - (b.metrics?.average_eta || 0);
    }
    if (sortMode === "SEVERITY_FIRST") {
      return (b.metrics?.critical_covered || 0) - (a.metrics?.critical_covered || 0);
    }
    return (b.score || 0) - (a.score || 0);
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-6">
      <header className="mb-8 flex justify-between items-end border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Plan Lab</h1>
          <p className="text-slate-500 text-sm">Evaluate and approve response strategies.</p>
        </div>
        <div className="flex items-center gap-2 text-sm bg-slate-900 border border-slate-800 p-1 rounded">
          {(["NEAREST_FIRST", "SEVERITY_FIRST", "BALANCED"] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setSortMode(mode)}
              className={`px-3 py-1.5 rounded transition-colors ${sortMode === mode ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              {mode.replace("_", " ")}
            </button>
          ))}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Main Grid: 3 Columns for Plans */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sortedPlans.map((plan: Plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isRecommended={state.recommended_plan?.id === plan.id}
              isApproved={state.approved_plan?.id === plan.id}
              incidents={state.incidents}
            />
          ))}
        </div>

        {/* Right Sidebar */}
        <div className="flex flex-col gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
            <h2 className="text-lg font-semibold text-white mb-4 border-b border-slate-800 pb-2">
              Why This Plan?
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed mb-4">
              {state.recommended_plan?.explanation || "The system recommends this plan based on an optimal balance of ETA and resource utilization, ensuring high-severity incidents are prioritized without causing excessive fragility."}
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
            <h2 className="text-lg font-semibold text-white mb-4 border-b border-slate-800 pb-2">
              Decision Confidence
            </h2>
            {state.decision_confidence ? (
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`font-bold ${
                    state.decision_confidence.level === "HIGH" ? "text-emerald-400" :
                    state.decision_confidence.level === "MEDIUM" ? "text-amber-400" : "text-red-400"
                  }`}>
                    {state.decision_confidence.level}
                  </span>
                  <span className="text-slate-500">
                    ({state.decision_confidence.passed_count}/{state.decision_confidence.total_count} criteria)
                  </span>
                </div>
                <ul className="space-y-2">
                  {state.decision_confidence.factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className={f.passed ? "text-emerald-500" : "text-red-500"}>
                        {f.passed ? "✓" : "✗"}
                      </span>
                      <span className="text-slate-300">{f.label}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Evaluating decision criteria...</p>
            )}
          </div>

          <AICommandBrief explanation={explanation} />

          {state.plan_diffs && state.plan_diffs.length > 0 && (
            <PlanDiffView diff={state.plan_diffs[0]} incidents={state.incidents} />
          )}
        </div>
      </div>
    </div>
  );
}
