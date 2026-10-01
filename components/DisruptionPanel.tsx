"use client";

import React, { useState } from "react";
import { Unit, RoadCondition } from "@/lib/api";

interface DisruptionPanelProps {
  units: Unit[];
  roads: RoadCondition[];
  onApply: (events: {event_type: string, payload: Record<string, unknown>}[]) => void;
  onCancel: () => void;
  loading: boolean;
}

export default function DisruptionPanel({ units, roads, onApply, onCancel, loading }: DisruptionPanelProps) {
  const [breakdownUnit, setBreakdownUnit] = useState<string>("");
  const [blockRoad, setBlockRoad] = useState<string>("");
  
  const [incType, setIncType] = useState<string>("FIRE");
  const [incLoc, setIncLoc] = useState<string>("");
  const [incThreat, setIncThreat] = useState<boolean>(false);
  const [showInc, setShowInc] = useState<boolean>(false);

  const availableUnits = units.filter((u) => u.status !== "BROKEN_DOWN");
  const unblockedRoads = roads.filter((r) => !r.blocked);

  const selectedCount = (breakdownUnit ? 1 : 0) + (blockRoad ? 1 : 0) + (showInc && incType && incLoc ? 1 : 0);

  const handleApply = () => {
    const events: {event_type: string, payload: Record<string, unknown>}[] = [];
    if (breakdownUnit) {
      events.push({ event_type: "UNIT_BREAKDOWN", payload: { unit_id: breakdownUnit } });
    }
    if (blockRoad) {
      events.push({ event_type: "ROAD_BLOCK", payload: { road_id: blockRoad } });
    }
    if (showInc && incType && incLoc) {
      events.push({
        event_type: "NEW_INCIDENT",
        payload: {
          id: `INC-${Math.floor(Math.random() * 10000)}`,
          type: incType,
          location: incLoc,
          latitude: 37.7749 + (Math.random() - 0.5) * 0.1,
          longitude: -122.4194 + (Math.random() - 0.5) * 0.1,
          life_threat: incThreat,
        }
      });
    }
    if (events.length > 0) {
      onApply(events);
    }
  };

  return (
    <div className="absolute inset-0 bg-slate-950/80 flex items-center justify-center z-50 backdrop-blur-sm p-4 font-sans">
      <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-full max-w-md flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            ■ SIMULATE DISRUPTION
          </h2>
        </div>

        <div className="p-4 flex flex-col gap-6 text-sm">
          {/* Unit Breakdown */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-slate-300 font-medium">
              <input type="checkbox" checked={!!breakdownUnit} onChange={(e) => setBreakdownUnit(e.target.checked ? (availableUnits[0]?.id || "") : "")} className="rounded border-slate-700 bg-slate-950" />
              Unit Breakdown
            </label>
            {breakdownUnit !== "" && (
              <select value={breakdownUnit} onChange={(e) => setBreakdownUnit(e.target.value)} className="bg-slate-950 border border-slate-700 text-slate-300 rounded p-2 ml-6 outline-none focus:border-amber-500">
                {availableUnits.map((u) => (
                  <option key={u.id} value={u.id}>{u.id} ({u.type})</option>
                ))}
              </select>
            )}
          </div>

          {/* Road Block */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-slate-300 font-medium">
              <input type="checkbox" checked={!!blockRoad} onChange={(e) => setBlockRoad(e.target.checked ? (unblockedRoads[0]?.id || "") : "")} className="rounded border-slate-700 bg-slate-950" />
              Road Block
            </label>
            {blockRoad !== "" && (
              <select value={blockRoad} onChange={(e) => setBlockRoad(e.target.value)} className="bg-slate-950 border border-slate-700 text-slate-300 rounded p-2 ml-6 outline-none focus:border-amber-500">
                {unblockedRoads.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            )}
          </div>

          {/* New Incident */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-slate-300 font-medium">
              <input type="checkbox" checked={showInc} onChange={(e) => setShowInc(e.target.checked)} className="rounded border-slate-700 bg-slate-950" />
              New Incident
            </label>
            {showInc && (
              <div className="flex flex-col gap-3 ml-6 bg-slate-950/50 p-3 rounded border border-slate-800">
                <input type="text" placeholder="Type (e.g. FIRE, MEDICAL)" value={incType} onChange={(e) => setIncType(e.target.value)} className="bg-slate-950 border border-slate-700 text-slate-300 rounded p-2 outline-none focus:border-amber-500 uppercase" />
                <input type="text" placeholder="Location Name" value={incLoc} onChange={(e) => setIncLoc(e.target.value)} className="bg-slate-950 border border-slate-700 text-slate-300 rounded p-2 outline-none focus:border-amber-500" />
                <label className="flex items-center gap-2 text-slate-400 text-xs mt-1">
                  <input type="checkbox" checked={incThreat} onChange={(e) => setIncThreat(e.target.checked)} className="rounded border-slate-700 bg-slate-950" />
                  Life Threatening
                </label>
              </div>
            )}
          </div>
        </div>

        <div className="p-4 border-t border-slate-800 flex items-center justify-between bg-slate-900/50">
          <span className="text-slate-400 text-xs">{selectedCount} events selected</span>
          <div className="flex gap-2">
            <button onClick={onCancel} disabled={loading} className="px-4 py-2 text-sm text-slate-300 hover:text-white disabled:opacity-50 cursor-pointer">
              CANCEL
            </button>
            <button onClick={handleApply} disabled={loading || selectedCount === 0} className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded text-sm font-semibold transition-colors cursor-pointer">
              {loading ? "APPLYING..." : "APPLY DISRUPTIONS"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
