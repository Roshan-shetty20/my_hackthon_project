"use client";

import React from "react";
import { Plan, ResilienceResult, Incident } from "@/lib/api";

interface PlanCardProps {
  plan: Plan;
  resilience?: ResilienceResult;
  isRecommended: boolean;
  isApproved: boolean;
  incidents: Incident[];
  onApprove?: () => void;
  approving?: boolean;
}

export default function PlanCard({
  plan,
  resilience,
  isRecommended,
  isApproved,
  incidents,
  onApprove,
  approving,
}: PlanCardProps) {
  const planLetter = plan.id.replace("plan_", "").toUpperCase();
  const valid = plan.validation?.valid ?? false;
  const metrics = plan.metrics;

  let borderColor = "border-slate-800";
  let borderLeftColor = "border-l-slate-800";

  if (isApproved) {
    borderColor = "border-emerald-800";
    borderLeftColor = "border-l-emerald-500";
  } else if (isRecommended) {
    borderColor = "border-blue-800";
    borderLeftColor = "border-l-blue-500";
  }

  const survived = resilience?.scenario_results.filter((r) => r.plan_still_valid && r.severity_impact === "LOW").length || 0;
  const degraded = resilience?.scenario_results.filter((r) => r.plan_still_valid && r.severity_impact !== "LOW").length || 0;
  const failed = resilience?.scenario_results.filter((r) => !r.plan_still_valid).length || 0;

  return (
    <div className={`bg-slate-900 border ${borderColor} border-l-4 ${borderLeftColor} rounded-lg p-4 flex flex-col gap-4 text-sm text-slate-300 font-sans`}>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            PLAN {planLetter}
            {isRecommended && <span className="bg-blue-900/50 text-blue-400 text-xs px-2 py-0.5 rounded border border-blue-800">RECOMMENDED</span>}
            {isApproved && <span className="bg-emerald-900/50 text-emerald-400 text-xs px-2 py-0.5 rounded border border-emerald-800">APPROVED</span>}
          </h3>
          <p className="text-slate-400">{plan.strategy_name}</p>
        </div>
        <div>
          {valid ? (
            <span className="text-emerald-400 bg-emerald-950/50 px-2 py-1 rounded text-xs border border-emerald-900">✓ VALID</span>
          ) : (
            <span className="text-red-400 bg-red-950/50 px-2 py-1 rounded text-xs border border-red-900">✗ INVALID</span>
          )}
        </div>
      </div>

      {!valid && plan.validation?.violations && plan.validation.violations.length > 0 && (
        <div className="bg-red-950/30 border border-red-900/50 p-2 rounded text-red-400 text-xs flex flex-col gap-1">
          {plan.validation.violations.map((v, i) => (
            <span key={i}>● {v.message}</span>
          ))}
        </div>
      )}

      {metrics && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-slate-950/50 p-2 rounded border border-slate-800">
            <div className="text-slate-500">Coverage</div>
            <div className="text-slate-200">{metrics.total_covered} / {metrics.total_incidents}</div>
          </div>
          <div className="bg-slate-950/50 p-2 rounded border border-slate-800">
            <div className="text-slate-500">Score</div>
            <div className="text-slate-200">{plan.score?.toFixed(1) ?? "N/A"}</div>
          </div>
          <div className="bg-slate-950/50 p-2 rounded border border-slate-800">
            <div className="text-slate-500">Avg ETA</div>
            <div className="text-slate-200">{metrics.average_eta.toFixed(1)}m</div>
          </div>
          <div className="bg-slate-950/50 p-2 rounded border border-slate-800">
            <div className="text-slate-500">Max ETA</div>
            <div className="text-slate-200">{metrics.max_eta.toFixed(1)}m</div>
          </div>
          <div className="bg-slate-950/50 p-2 rounded border border-slate-800">
            <div className="text-slate-500">Reserve Units</div>
            <div className="text-slate-200">{metrics.reserve_units}</div>
          </div>
          <div className="bg-slate-950/50 p-2 rounded border border-slate-800">
            <div className="text-slate-500">Resilience</div>
            <div className="text-slate-200">{metrics.resilience_score.toFixed(1)}</div>
          </div>
        </div>
      )}

      {resilience && (
        <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
          <div className="text-xs font-semibold text-slate-400">STRESS TEST (1000 iter)</div>
          <div className="flex gap-4 text-xs">
            <span className="text-emerald-400">✓ Survived: {survived}</span>
            <span className="text-amber-400">▲ Degraded: {degraded}</span>
            <span className="text-red-400">✗ Failed: {failed}</span>
          </div>
          {resilience.single_points_of_failure.length > 0 && (
            <div className="text-amber-400 text-xs mt-1">
              <span className="font-semibold">SPOFs:</span> {resilience.single_points_of_failure.join(", ")}
            </div>
          )}
        </div>
      )}

      {metrics?.human_attention_required && (
        <div className="bg-amber-950/30 border border-amber-900/50 p-2 rounded text-amber-400 text-xs flex flex-col gap-1">
          <span className="font-semibold">▲ HUMAN ATTENTION REQUIRED</span>
          {metrics.attention_reasons.map((r, i) => (
            <span key={i}>● {r}</span>
          ))}
        </div>
      )}

      {metrics?.uncovered_incidents && metrics.uncovered_incidents.length > 0 && (
        <div className="bg-red-950/30 border border-red-900/50 p-2 rounded text-red-400 text-xs">
          <span className="font-semibold">✗ UNCOVERED:</span> {metrics.uncovered_incidents.join(", ")}
        </div>
      )}

      <div className="border-t border-slate-800 pt-3">
        <div className="text-xs font-semibold text-slate-400 mb-2">ASSIGNMENTS</div>
        <div className="flex flex-col gap-1 text-xs max-h-32 overflow-y-auto pr-1">
          {plan.assignments.map((a, i) => (
            <div key={i} className="flex justify-between border-b border-slate-800/50 pb-1">
              <span className="text-slate-300">{a.unit_id} → {a.incident_id}</span>
              <span className="text-slate-400">{a.eta_minutes.toFixed(1)}m</span>
            </div>
          ))}
        </div>
      </div>

      {!isApproved && valid && onApprove && (
        <button
          onClick={onApprove}
          disabled={approving}
          className="mt-2 w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white py-2 rounded text-sm font-semibold transition-colors flex items-center justify-center gap-2 cursor-pointer"
        >
          {approving ? "APPROVING..." : "APPROVE PLAN"}
        </button>
      )}
    </div>
  );
}
