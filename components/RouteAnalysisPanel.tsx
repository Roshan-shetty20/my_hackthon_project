'use client';

import React from 'react';
import { CrisisStateResponse } from '@/lib/api';

interface RouteAnalysisPanelProps {
  state: CrisisStateResponse | null;
  selectedMissionId: string | null;
}

export default function RouteAnalysisPanel({ state, selectedMissionId }: RouteAnalysisPanelProps) {
  if (!state) {
    return <div className="p-4 bg-slate-950 text-slate-500 h-full">Waiting for data...</div>;
  }

  const mission = selectedMissionId ? state.active_missions[selectedMissionId] : null;

  if (!mission) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-950 text-slate-500 h-full text-center border-l border-slate-800">
        <p>Select a mission on the map</p>
      </div>
    );
  }

  const unit = state.units.find(u => u.id === mission.unit_id);
  const incident = state.incidents.find(i => i.id === mission.incident_id);
  const progress = Math.min(100, Math.max(0, mission.progress_percent));

  return (
    <div className="flex flex-col p-4 bg-slate-950 text-slate-200 h-full border-l border-slate-800 overflow-y-auto">
      <h2 className="text-lg font-semibold mb-4 text-slate-100">Route Analysis</h2>
      
      <div className="bg-slate-900 p-3 rounded border border-slate-800 mb-4">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-slate-400">Unit ID:</div>
          <div className="font-mono text-slate-200">{mission.unit_id}</div>
          
          <div className="text-slate-400">Type:</div>
          <div className="text-slate-200">{unit?.type || 'Unknown'}</div>
          
          <div className="text-slate-400">Destination:</div>
          <div className="font-mono text-slate-200">{mission.incident_id}</div>
          
          <div className="text-slate-400">Status:</div>
          <div className="text-slate-200">{mission.status}</div>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-slate-400">Progress</span>
          <span className="font-mono">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-2">
          <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${progress}%` }}></div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-slate-900 p-3 rounded border border-slate-800 text-center">
          <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">ETA</div>
          <div className="text-xl font-mono text-emerald-400">{mission.eta_minutes}m</div>
        </div>
        <div className="bg-slate-900 p-3 rounded border border-slate-800 text-center">
          <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Distance</div>
          <div className="text-xl font-mono text-blue-400">{mission.distance_remaining_km.toFixed(1)}km</div>
        </div>
      </div>

      {mission.route && (
        <>
          <div className="mb-4">
            <h3 className="text-sm font-medium text-slate-300 mb-2 uppercase tracking-wider">Route Status</h3>
            <div className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
              mission.route.status === 'FEASIBLE' ? 'bg-emerald-500/20 text-emerald-400' :
              mission.route.status === 'INTERRUPTED' ? 'bg-red-500/20 text-red-400' :
              mission.route.status === 'REROUTED' ? 'bg-amber-500/20 text-amber-400' :
              'bg-slate-500/20 text-slate-400'
            }`}>
              {mission.route.status}
            </div>
            {mission.route.blocked && (
              <div className="mt-2 text-sm text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20">
                Blocked: {mission.route.reason || 'Unknown reason'}
              </div>
            )}
          </div>

          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-2 uppercase tracking-wider">Route Segments</h3>
            <div className="flex flex-col gap-1">
              {mission.route.road_segments.map((seg, idx) => (
                <div key={idx} className="bg-slate-900 px-3 py-2 rounded text-sm text-slate-300 border border-slate-800 font-mono">
                  {seg}
                </div>
              ))}
              {mission.route.road_segments.length === 0 && (
                <div className="text-sm text-slate-500 italic">No segments data</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
