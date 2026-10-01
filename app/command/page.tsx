"use client";

import { useState } from "react";
import { useSession } from "@/lib/session-context";
import StageProgress from "@/components/StageProgress";
import IncidentQueue from "@/components/IncidentQueue";
import AICommandBrief from "@/components/AICommandBrief";
import PlanDiffView from "@/components/PlanDiffView";
import OperationalMap from "@/components/OperationalMap";
import RouteAnalysisPanel from "@/components/RouteAnalysisPanel";
import EventTimeline from "@/components/EventTimeline";
import SimulationControls from "@/components/SimulationControls";
import DisruptionPanel from "@/components/DisruptionPanel";

export default function CommandPage() {
  const {
    state, explanation, loading, error,
    sessionId, createSession, isDemoMode, setDemoMode,
    generatePlans, approvePlan, replan, applyDisruptions
  } = useSession();

  const [approving, setApproving] = useState(false);
  const [disruptPanel, setDisruptPanel] = useState(false);
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("UNITS");

  // Build assignment map for incident queue
  const assignmentMap: Record<string, { unit_id: string; eta_minutes: number }[]> = {};
  const planToShow = state?.approved_plan ?? state?.recommended_plan ?? state?.candidate_plans?.[0];
  const assignmentMode = state?.approved_plan ? "APPROVED" : (state?.recommended_plan ? "RECOMMENDED" : (state?.candidate_plans?.length ? "CANDIDATE" : undefined));
  
  if (assignmentMode === "APPROVED" && state?.active_missions) {
    for (const mission of Object.values(state.active_missions)) {
      if (mission.status === "EN_ROUTE" || mission.status === "ON_SCENE") {
        if (!assignmentMap[mission.incident_id]) assignmentMap[mission.incident_id] = [];
        assignmentMap[mission.incident_id].push({ 
          unit_id: mission.unit_id, 
          eta_minutes: Math.max(0, Number(mission.eta_minutes.toFixed(1))) 
        });
      }
    }
  } else if (planToShow) {
    for (const a of planToShow.assignments) {
      if (!assignmentMap[a.incident_id]) assignmentMap[a.incident_id] = [];
      assignmentMap[a.incident_id].push({ unit_id: a.unit_id, eta_minutes: Math.max(0, Number(a.eta_minutes.toFixed(1))) });
    }
  }

  const handleApprove = async () => {
    const plan = state?.recommended_plan;
    if (!plan) return;
    setApproving(true);
    await approvePlan(plan.id);
    setApproving(false);
  };

  const availUnits = state?.units.filter(u => u.status === "AVAILABLE").length ?? 0;
  const critCount = state?.incidents.filter(i => i.urgency === "CRITICAL").length ?? 0;
  const rec = state?.recommended_plan;

  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center bg-slate-950">
        <div className="text-xl font-bold text-slate-200 mb-2 tracking-widest">CRISIS COMMAND</div>
        <div className="text-slate-400 mb-6 max-w-md">
          Launch an isolated operational command session.
        </div>
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => { setDemoMode(false); createSession(); }}
            disabled={loading}
            className="px-8 py-3 rounded border border-blue-500 bg-blue-950 text-blue-300 font-bold hover:bg-blue-900 transition-colors"
          >
            {loading ? "INITIALIZING..." : "START SESSION"}
          </button>
          
          <button
            onClick={() => { setDemoMode(true); createSession(); }}
            disabled={loading}
            className="px-8 py-3 rounded border border-purple-500 bg-purple-950 text-purple-300 font-bold hover:bg-purple-900 transition-colors"
          >
            GUIDED DEMO
          </button>
        </div>
      </div>
    );
  }

  // Define tabs
  const tabs = [
    { id: "UNITS", label: "UNITS" },
    { id: "ROUTES", label: "ROUTES" },
    { id: "ROADS", label: "ROADS" },
  ];
  if (state?.latest_impact_analysis) tabs.push({ id: "IMPACT", label: "IMPACT" });
  if (state?.plan_diffs && state.plan_diffs.length > 0) tabs.push({ id: "DIFF", label: "DIFF" });
  tabs.push({ id: "LOG", label: "LOG" });

  return (
    <div className="p-4 max-w-[1600px] mx-auto bg-slate-950 min-h-screen text-slate-200 font-sans">
      {error && (
        <div className="bg-red-950 border border-red-700 rounded p-3 mb-4 text-sm text-red-300 flex items-center gap-2">
          ▲ {error}
        </div>
      )}

      {/* Metrics strip */}
      {state && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mb-4">
          {[
            { label: "Active Incidents", val: state.incidents.length, warn: state.incidents.length > 3, indicator: false },
            { label: "Critical", val: critCount, warn: critCount > 0, indicator: true },
            { label: "Available Units", val: `${availUnits}/${state.units.length}`, warn: availUnits < 2, indicator: false },
            { label: "Reserve Units", val: rec?.metrics?.reserve_units ?? "—", warn: (rec?.metrics?.reserve_units ?? 1) < 1, indicator: false },
            { label: "Resilience", val: rec ? `${state.resilience_results[rec.id]?.resilience_score ?? "—"}/100` : "—", warn: false, indicator: false },
            { label: "Confidence", val: state.decision_confidence?.level ?? "—", warn: false, indicator: false },
          ].map(({ label, val, warn, indicator }) => (
            <div key={label} className="bg-slate-900 border border-slate-800 rounded p-3 text-center flex flex-col justify-center">
              <div className={`text-xl font-black flex items-center justify-center gap-2 ${warn ? "text-red-400" : "text-slate-100"}`}>
                {indicator && warn && <span className="text-[10px] text-red-500">●</span>}
                {val}
              </div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wide mt-1">{label}</div>
            </div>
          ))}
        </div>
      )}

      <StageProgress
        onGeneratePlans={generatePlans}
        onDisrupt={() => setDisruptPanel(true)}
      />

      {isDemoMode && (
        <div className="mb-4">
          <SimulationControls />
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_340px] gap-4">
        {/* LEFT */}
        <div className="flex flex-col gap-2">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 pl-1">Incident Queue</div>
          <IncidentQueue
            incidents={state?.incidents ?? []}
            assignmentMap={assignmentMap}
          />
        </div>

        {/* CENTER */}
        <div className="space-y-4">
          <div className="min-h-[400px] border border-slate-800 rounded-lg overflow-hidden bg-slate-900">
            <OperationalMap state={state} selectedMissionId={selectedMissionId} onSelectMission={setSelectedMissionId} />
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <div className="flex border-b border-slate-800 overflow-x-auto no-scrollbar">
              {tabs.map(t => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`px-4 py-2 text-xs font-bold whitespace-nowrap transition-colors ${activeTab === t.id ? "bg-slate-800 text-blue-400 border-b-2 border-blue-500" : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border-b-2 border-transparent"}`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="p-4">
              {activeTab === "UNITS" && (
                <div className="space-y-2">
                  {state?.units.map(u => {
                    const sc = u.status === "AVAILABLE" ? "text-emerald-400 border-emerald-800 bg-emerald-950/30" :
                               u.status === "ASSIGNED" || u.status === "EN_ROUTE" ? "text-blue-400 border-blue-800 bg-blue-950/30" :
                               u.status === "ON_SCENE" ? "text-purple-400 border-purple-800 bg-purple-950/30" :
                               u.status === "BROKEN_DOWN" ? "text-red-400 border-red-800 bg-red-950/30" : "text-slate-500 border-slate-700 bg-slate-800/30";
                    return (
                      <div key={u.id} className="flex items-center justify-between text-xs border-b border-slate-800/50 pb-2 last:border-0 last:pb-0">
                        <span className="font-mono text-slate-300 w-20">{u.id}</span>
                        <span className="text-slate-500 w-20 truncate">{u.type}</span>
                        <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${sc}`}>{u.status}</span>
                        <span className="text-slate-500 w-24 text-right truncate">
                          {u.current_incident ? `→ ${u.current_incident}` : "—"}
                        </span>
                      </div>
                    );
                  })}
                  {(!state?.units || state.units.length === 0) && <div className="text-xs text-slate-500 text-center py-4">No units available.</div>}
                </div>
              )}

              {activeTab === "ROUTES" && (
                <RouteAnalysisPanel state={state} selectedMissionId={selectedMissionId} />
              )}

              {activeTab === "ROADS" && (
                <div className="space-y-1">
                  {state?.road_conditions.map(r => (
                    <div key={r.id} className="flex items-center justify-between text-xs border-b border-slate-800/50 py-2 last:border-0">
                      <span className="text-slate-400">{r.name}</span>
                      <span className={`font-bold px-2 py-0.5 rounded text-[10px] border ${r.blocked ? "text-red-400 border-red-800 bg-red-950/30" : "text-emerald-400 border-emerald-800 bg-emerald-950/30"}`}>
                        {r.blocked ? "■ BLOCKED" : "✓ CLEAR"}
                      </span>
                    </div>
                  ))}
                  {(!state?.road_conditions || state.road_conditions.length === 0) && <div className="text-xs text-slate-500 text-center py-4">No road conditions reported.</div>}
                </div>
              )}

              {activeTab === "IMPACT" && state?.latest_impact_analysis && (
                <div className="space-y-4">
                  {state.latest_impact_analysis.trigger.includes("+") && (
                    <div className="bg-red-950/20 border border-red-900/50 p-3 rounded">
                      <div className="text-xs font-black text-red-500 uppercase tracking-widest flex items-center gap-2 mb-2">
                        ▲ SIMULTANEOUS CRISIS DETECTED
                      </div>
                      <div className="text-xs text-slate-300 flex items-center gap-2 flex-wrap">
                        <span className="bg-slate-900 px-2 py-1 rounded border border-slate-700 text-blue-300">
                          {state.latest_impact_analysis.trigger.split("+").length} simultaneous events
                        </span>
                        {Object.keys(state.latest_impact_analysis.resource_shortfalls || {}).length > 0 && (
                          <span className="bg-slate-900 px-2 py-1 rounded border border-red-900 text-red-400">
                            {Object.keys(state.latest_impact_analysis.resource_shortfalls).length} resource conflict(s)
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="text-xs font-bold text-amber-500 uppercase tracking-widest flex items-center justify-between pb-2 border-b border-slate-800">
                    <span>Impact Analysis</span>
                    <span className="px-2 py-0.5 bg-amber-950/50 text-amber-400 border border-amber-800/50 rounded text-[10px]">DETERMINISTIC</span>
                  </div>
                  
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-wider">Global Resource Demand</div>
                    <div className="bg-slate-950 rounded border border-slate-800 overflow-hidden">
                      <table className="w-full text-xs text-left text-slate-300">
                        <thead className="text-slate-500 bg-slate-900/50 border-b border-slate-800">
                          <tr>
                            <th className="font-normal px-3 py-2">Resource</th>
                            <th className="font-normal text-right px-3 py-2">Required</th>
                            <th className="font-normal text-right px-3 py-2">Available</th>
                            <th className="font-normal text-right px-3 py-2">Gap</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(state.latest_impact_analysis.global_demand || {}).map(([type, req]) => {
                            const avail = (state.latest_impact_analysis.global_available?.[type] as number) || 0;
                            const r = req as number;
                            const gap = avail - r;
                            return (
                              <tr key={type} className="border-b border-slate-800/50 last:border-0">
                                <td className="px-3 py-2 capitalize">{type.replace(/_/g, ' ')}</td>
                                <td className="px-3 py-2 text-right">{r}</td>
                                <td className="px-3 py-2 text-right">{avail}</td>
                                <td className={`px-3 py-2 text-right font-bold ${gap < 0 ? "text-red-400" : "text-emerald-400"}`}>{gap}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-wider">Impact Consequences</div>
                    <div className="space-y-1.5 bg-slate-950 p-3 rounded border border-slate-800">
                      {state.latest_impact_analysis.replan_required && (
                        <div className="text-xs text-red-400 font-bold flex items-center gap-1.5">
                          ▲ Current plan invalidated
                        </div>
                      )}
                      {state.latest_impact_analysis.affected_incidents && state.latest_impact_analysis.affected_incidents.length > 0 && (
                        <div className="text-xs text-slate-300">
                          <span className="text-slate-500">Affected incidents:</span> {state.latest_impact_analysis.affected_incidents.join(", ")}
                        </div>
                      )}
                      {state.latest_impact_analysis.coverage_lost && state.latest_impact_analysis.coverage_lost.length > 0 && (
                        <div className="text-xs text-orange-400">
                          <span className="text-orange-500/70">Coverage lost for:</span> {state.latest_impact_analysis.coverage_lost.join(", ")}
                        </div>
                      )}
                      {!state.latest_impact_analysis.replan_required && 
                       (!state.latest_impact_analysis.affected_incidents || state.latest_impact_analysis.affected_incidents.length === 0) &&
                       (!state.latest_impact_analysis.coverage_lost || state.latest_impact_analysis.coverage_lost.length === 0) && (
                         <div className="text-xs text-slate-500 italic">No significant consequences detected.</div>
                       )}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "DIFF" && state?.plan_diffs && state.plan_diffs.length > 0 && (
                <PlanDiffView
                  diff={state.plan_diffs[state.plan_diffs.length - 1]}
                  incidents={state.incidents}
                />
              )}

              {activeTab === "LOG" && (
                <EventTimeline state={state} />
              )}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              System Recommendation
            </div>
            {state?.recommended_plan ? (
              <>
                <div className="text-lg font-black text-blue-300 mb-1">
                  {state.recommended_plan.strategy_name === "NEAREST_FIRST" && "Plan A"}
                  {state.recommended_plan.strategy_name === "SEVERITY_FIRST" && "Plan B"}
                  {state.recommended_plan.strategy_name === "BALANCED" && "Plan C"}
                  {" — "}
                  {state.recommended_plan.strategy_name === "NEAREST_FIRST" && "Fastest Response"}
                  {state.recommended_plan.strategy_name === "SEVERITY_FIRST" && "Critical-First"}
                  {state.recommended_plan.strategy_name === "BALANCED" && "Resilient Balance"}
                  {!["NEAREST_FIRST", "SEVERITY_FIRST", "BALANCED"].includes(state.recommended_plan.strategy_name) && state.recommended_plan.strategy_name}
                </div>
                {state.recommended_plan.metrics && (
                  <div className="text-xs text-slate-400 space-y-2 mb-4 bg-slate-950 p-3 rounded border border-slate-800/50">
                    <div className="flex justify-between items-center"><span className="uppercase text-[10px] tracking-wider">Coverage</span> <span className="text-slate-200 font-mono">{state.recommended_plan.metrics.total_covered}/{state.recommended_plan.metrics.total_incidents}</span></div>
                    <div className="flex justify-between items-center"><span className="uppercase text-[10px] tracking-wider">Avg ETA</span> <span className="text-slate-200 font-mono">{state.recommended_plan.metrics.average_eta} min</span></div>
                    <div className="flex justify-between items-center"><span className="uppercase text-[10px] tracking-wider">Reserve</span> <span className="text-slate-200 font-mono">{state.recommended_plan.metrics.reserve_units} units</span></div>
                    <div className="flex justify-between items-center"><span className="uppercase text-[10px] tracking-wider">Score</span> <span className="text-emerald-400 font-mono font-bold">{Math.round(state.recommended_plan.score ?? 0)}</span></div>
                  </div>
                )}

                {!state.approved_plan ? (
                  <div className="border-t border-slate-800 pt-4">
                    <div className="text-[10px] text-slate-500 mb-3 text-center uppercase tracking-widest flex items-center justify-center gap-2">
                      <span className="w-8 h-px bg-slate-800"></span>
                      Commander Decision
                      <span className="w-8 h-px bg-slate-800"></span>
                    </div>
                    <button
                      onClick={handleApprove}
                      disabled={approving || loading}
                      className="w-full py-2.5 rounded border border-emerald-600/50 bg-emerald-950/30 text-emerald-400 text-xs font-black tracking-widest hover:bg-emerald-900/50 transition-colors disabled:opacity-50 mb-2 flex items-center justify-center gap-2"
                    >
                      {approving ? "⟳ APPROVING…" : "✓ APPROVE PLAN"}
                    </button>
                    <button
                      onClick={replan}
                      disabled={loading}
                      className="w-full py-2 rounded border border-slate-700 bg-slate-800/30 text-slate-400 text-[10px] font-bold tracking-widest uppercase hover:bg-slate-800/80 transition-colors flex items-center justify-center gap-2"
                    >
                      ✗ REVIEW & REPLAN
                    </button>
                  </div>
                ) : (
                  <div className="border-t border-slate-800 pt-4 mt-2">
                    <div className="text-center bg-emerald-950/20 border border-emerald-900/30 rounded py-2.5 mb-3 flex flex-col items-center justify-center">
                      <div className="text-emerald-400 text-sm font-black flex items-center gap-1.5">✓ APPROVED</div>
                      <div className="text-[10px] text-emerald-500/70 uppercase tracking-widest mt-1">Plan Active</div>
                    </div>
                    
                    <button
                      onClick={() => setDisruptPanel(!disruptPanel)}
                      className={`w-full py-2.5 rounded border text-[10px] font-bold tracking-widest uppercase transition-colors mb-2 flex items-center justify-center gap-2 ${disruptPanel ? "border-orange-500/50 bg-orange-950/50 text-orange-400" : "border-orange-900/50 bg-orange-950/20 text-orange-500 hover:bg-orange-900/40"}`}
                    >
                      ▲ SIMULATE DISRUPTION
                    </button>
                    
                    {disruptPanel && (
                      <div className="mb-3 p-1">
                        <DisruptionPanel
                          units={state?.units ?? []}
                          roads={state?.road_conditions ?? []}
                          onApply={async (events) => {
                            await applyDisruptions(events);
                            setDisruptPanel(false);
                          }}
                          onCancel={() => setDisruptPanel(false)}
                          loading={loading}
                        />
                      </div>
                    )}

                    <button
                      onClick={replan}
                      disabled={loading}
                      className="w-full py-2 rounded border border-blue-900/50 bg-blue-950/20 text-blue-400 text-[10px] font-bold tracking-widest uppercase hover:bg-blue-900/40 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      ⟳ REVIEW & REPLAN
                    </button>
                  </div>
                )}
              </>
            ) : state?.candidate_plans?.length ? (
              <div className="text-xs text-slate-500 py-4 text-center">Plans generated. Scoring in progress…</div>
            ) : (
              <div className="text-xs text-slate-500 italic py-4 text-center">
                Generate plans to view system recommendation.
              </div>
            )}
          </div>

          <AICommandBrief explanation={explanation} />

          {state?.decision_debts && state.decision_debts.length > 0 && (
            <div className="bg-amber-950/10 border border-amber-900/30 rounded-lg p-4">
              <div className="text-[10px] font-bold text-amber-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                ▲ Decision Dependencies
              </div>
              <div className="space-y-3">
                {state.decision_debts.map((d, i) => (
                  <div key={i} className="text-xs text-slate-300 bg-slate-950/50 p-2.5 rounded border border-slate-800/50">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-amber-400/90 bg-amber-950/30 px-1.5 py-0.5 rounded text-[10px]">{d.unit_id}</span>
                      {d.is_spof && <span className="text-[9px] bg-red-950/40 text-red-400/90 px-1.5 py-0.5 border border-red-900/30 rounded font-bold tracking-wider">SPOF</span>}
                    </div>
                    <div className="mb-1.5 leading-relaxed">{d.description}</div>
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider">{d.failure_impact}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
