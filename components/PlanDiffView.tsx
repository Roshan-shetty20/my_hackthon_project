"use client";

import React from "react";
import { PlanDiff, Incident } from "@/lib/api";

interface PlanDiffViewProps {
  diff: PlanDiff;
  incidents: Incident[];
}

export default function PlanDiffView({ diff, incidents }: PlanDiffViewProps) {
  const fromPlan = diff.before_plan_id.replace("plan_", "").toUpperCase();
  const toPlan = diff.after_plan_id.replace("plan_", "").toUpperCase();

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col gap-4 text-sm font-sans">
      <div className="flex justify-between items-center border-b border-slate-800 pb-2">
        <h3 className="text-slate-100 font-semibold">
          PLAN DIFF: {fromPlan} → {toPlan}
        </h3>
        {diff.trigger && (
          <span className="bg-slate-800 text-slate-300 text-xs px-2 py-1 rounded border border-slate-700">
            {diff.trigger}
          </span>
        )}
      </div>

      {diff.changed_units.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-500 mb-2">REASSIGNMENTS</div>
          <div className="flex flex-col gap-2">
            {diff.changed_units.map((c, i) => (
              <div key={i} className="flex flex-col bg-slate-950/50 p-2 rounded border border-slate-800">
                <div className="text-slate-300 font-medium mb-1">{c.incident}</div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-red-400 line-through">{c.before_unit}</span>
                  <span className="text-slate-500">→</span>
                  <span className="text-emerald-400">{c.after_unit}</span>
                  <span className="text-slate-500 ml-auto">
                    ETA: {c.before_eta.toFixed(1)}m → {c.after_eta.toFixed(1)}m
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {(diff.added_assignments.length > 0 || diff.removed_assignments.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          {diff.added_assignments.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-2">ADDED</div>
              <div className="flex flex-col gap-1 text-xs">
                {diff.added_assignments.map((a, i) => (
                  <div key={i} className="text-emerald-400 flex items-center gap-1">
                    <span>+</span> {a.unit_id} → {a.incident_id} ({a.eta_minutes.toFixed(1)}m)
                  </div>
                ))}
              </div>
            </div>
          )}
          {diff.removed_assignments.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-2">REMOVED</div>
              <div className="flex flex-col gap-1 text-xs">
                {diff.removed_assignments.map((a, i) => (
                  <div key={i} className="text-red-400 flex items-center gap-1">
                    <span>-</span> {a.unit_id} → {a.incident_id}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {(diff.newly_uncovered.length > 0 || diff.newly_covered.length > 0) && (
        <div className="border-t border-slate-800 pt-3 flex flex-col gap-2">
          {diff.newly_uncovered.length > 0 && (
            <div className="text-red-400 text-xs">
              <span className="font-semibold">✗ NEWLY UNCOVERED:</span> {diff.newly_uncovered.join(", ")}
            </div>
          )}
          {diff.newly_covered.length > 0 && (
            <div className="text-emerald-400 text-xs">
              <span className="font-semibold">✓ NEWLY COVERED:</span> {diff.newly_covered.join(", ")}
            </div>
          )}
        </div>
      )}

      {diff.reallocation_reasons && diff.reallocation_reasons.length > 0 && (
        <div className="border-t border-slate-800 pt-3">
          <div className="text-xs font-semibold text-slate-500 mb-2">REALLOCATION REASONS</div>
          <div className="flex flex-col gap-2 text-xs">
            {diff.reallocation_reasons.map((r, i) => (
              <div key={i} className="bg-slate-950/50 p-2 rounded border border-slate-800 text-slate-300">
                <div className="font-medium text-slate-200 mb-1">{r.incident_id}</div>
                <div>{r.reason_for_change}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
