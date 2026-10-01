"use client";

import React from "react";
import { useSession } from "@/lib/session-context";

export default function ResiliencePage() {
  const { state } = useSession();

  if (!state || !state.resilience_results) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-300 p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-slate-400">No active session or plans to evaluate.</p>
        </div>
      </div>
    );
  }

  const recommendedPlanId = state.recommended_plan?.id;
  const result = recommendedPlanId ? state.resilience_results[recommendedPlanId] : Object.values(state.resilience_results)[0];

  if (!result) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-300 p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-slate-400">Resilience data not available for the current plan.</p>
        </div>
      </div>
    );
  }

  const survivedCount = result.scenario_results.filter(s => s.severity_impact === "NONE").length;
  const degradedCount = result.scenario_results.filter(s => s.severity_impact === "MODERATE").length;
  const failedCount = result.scenario_results.filter(s => s.severity_impact === "SEVERE").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-6 flex flex-col h-screen overflow-hidden">
      <header className="mb-6 flex-shrink-0">
        <h1 className="text-2xl font-bold text-white mb-1">Resilience Lab</h1>
        <p className="text-slate-500 text-sm">Stress-testing the active plan against theoretical disruptions.</p>
      </header>

      <div className="flex gap-6 flex-1 min-h-0">
        
        {/* Left Column: Summary */}
        <div className="w-[280px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto pr-2">
          
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
            <h3 className="text-sm font-medium text-slate-400 mb-2">Resilience Score</h3>
            <div className="text-4xl font-bold text-blue-400">
              {(result.resilience_score * 100).toFixed(0)}<span className="text-2xl text-blue-400/50">%</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
            <h3 className="text-sm font-medium text-slate-400 mb-2">Fragility Index</h3>
            <div className="text-3xl font-semibold text-purple-400">
              {result.fragility_index.toFixed(2)}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
            <h3 className="text-sm font-medium text-slate-400 mb-3">Scenario Summary</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-emerald-400 flex items-center gap-2"><span className="text-xs">●</span> Survived</span>
                <span className="text-white font-medium">{survivedCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-amber-400 flex items-center gap-2"><span className="text-xs">●</span> Degraded</span>
                <span className="text-white font-medium">{degradedCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-400 flex items-center gap-2"><span className="text-xs">●</span> Failed</span>
                <span className="text-white font-medium">{failedCount}</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
            <h3 className="text-sm font-medium text-slate-400 mb-3">Single Points of Failure</h3>
            {result.single_points_of_failure.length > 0 ? (
              <ul className="space-y-2 text-sm text-amber-300">
                {result.single_points_of_failure.map((spof, i) => (
                  <li key={i} className="flex gap-2 items-start">
                    <span className="mt-0.5">▲</span> {spof}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-emerald-500">No SPOFs detected.</p>
            )}
          </div>

          {result.worst_case_impact && (
            <div className="bg-slate-900 border border-red-900/50 rounded-lg p-5">
              <h3 className="text-sm font-medium text-red-400 mb-2">Worst Case</h3>
              <p className="text-sm text-slate-300 mb-2">{result.worst_case_impact.scenario.description}</p>
              <div className="text-xs text-slate-500">
                ETA Increase: +{result.worst_case_impact.eta_increase_minutes} min
              </div>
            </div>
          )}

        </div>

        {/* Right Column: Scenario Matrix */}
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-800 bg-slate-900/80">
            <h2 className="text-lg font-semibold text-white">Scenario Matrix</h2>
          </div>
          
          <div className="flex-1 overflow-auto p-5">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 uppercase bg-slate-900/50 border-b border-slate-800 sticky top-0">
                <tr>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Target</th>
                  <th className="px-4 py-3 font-medium">Result</th>
                  <th className="px-4 py-3 font-medium">Impact</th>
                  <th className="px-4 py-3 font-medium text-right">ETA Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {result.scenario_results.map((scenario, idx) => {
                  let badgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                  let label = "SURVIVED";
                  if (scenario.severity_impact === "SEVERE") {
                    badgeClass = "bg-red-500/10 text-red-400 border-red-500/20";
                    label = "FAILED";
                  } else if (scenario.severity_impact === "MODERATE") {
                    badgeClass = "bg-amber-500/10 text-amber-400 border-amber-500/20";
                    label = "DEGRADED";
                  }

                  return (
                    <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                      <td className="px-4 py-3 text-slate-300">{scenario.scenario.type}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-xs">{scenario.scenario.target_id}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 border rounded text-[10px] font-bold tracking-wider ${badgeClass}`}>
                          {label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 truncate max-w-xs" title={scenario.scenario.description}>
                        {scenario.scenario.description}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-300">
                        {scenario.eta_increase_minutes > 0 ? `+${scenario.eta_increase_minutes}m` : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
