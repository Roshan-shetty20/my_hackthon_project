'use client';

import React, { useMemo } from 'react';
import { Incident } from '@/lib/api';

interface IncidentQueueProps {
  incidents: Incident[];
  assignmentMap: Record<string, { unit_id: string; eta_minutes: number }[]>;
  assignmentMode?: "APPROVED" | "RECOMMENDED" | "CANDIDATE";
}

export default function IncidentQueue({ incidents, assignmentMap, assignmentMode }: IncidentQueueProps) {
  const sortedIncidents = useMemo(() => {
    return [...incidents].sort((a, b) => (b.severity ?? 0) - (a.severity ?? 0));
  }, [incidents]);

  const getUrgencyColor = (urgency: string | null) => {
    switch (urgency) {
      case 'CRITICAL': return 'border-l-red-500';
      case 'HIGH': return 'border-l-amber-500';
      case 'MEDIUM': return 'border-l-yellow-500';
      case 'LOW': return 'border-l-emerald-500';
      default: return 'border-l-slate-500';
    }
  };

  const getBadgeColor = (urgency: string | null) => {
    switch (urgency) {
      case 'CRITICAL': return 'bg-red-500/20 text-red-400';
      case 'HIGH': return 'bg-amber-500/20 text-amber-400';
      case 'MEDIUM': return 'bg-yellow-500/20 text-yellow-400';
      case 'LOW': return 'bg-emerald-500/20 text-emerald-400';
      default: return 'bg-slate-500/20 text-slate-400';
    }
  };

  return (
    <div className="flex flex-col gap-3 p-4 h-full overflow-y-auto bg-slate-950 text-slate-200">
      <h2 className="text-xl font-semibold mb-2">Incident Queue</h2>
      {sortedIncidents.map((incident) => {
        const assignments = assignmentMap[incident.id] || [];
        
        return (
          <div
            key={incident.id}
            className={`flex flex-col bg-slate-900 border border-slate-800 rounded shadow-sm border-l-4 p-3 ${getUrgencyColor(incident.urgency)}`}
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-slate-400">{incident.id}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${getBadgeColor(incident.urgency)}`}>
                    {incident.urgency || 'UNKNOWN'}
                  </span>
                </div>
                <h3 className="font-medium text-slate-100">{incident.type.replace(/_/g, ' ')}</h3>
                <p className="text-sm text-slate-400">{incident.location}</p>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold">Severity: {incident.severity?.toFixed(1) ?? 'N/A'}</div>
              </div>
            </div>

            <div className="text-sm space-y-1 mb-3">
              <div className="flex gap-4">
                <span>Affected: {incident.people_affected}</span>
                {incident.people_trapped > 0 && (
                  <span className="text-red-400 font-medium">Trapped: {incident.people_trapped}</span>
                )}
              </div>
              {incident.spreading_hazard && (
                <div className="text-amber-400 text-xs uppercase tracking-wider font-semibold">
                  ▲ Spreading Hazard Warning
                </div>
              )}
            </div>

            <div className="mt-auto pt-2 border-t border-slate-800">
              <div className="text-[10px] text-slate-500 mb-1 uppercase tracking-wider flex items-center justify-between">
                <span>Assignments</span>
                {assignmentMode === "RECOMMENDED" && <span className="text-blue-400 bg-blue-950/30 px-1.5 py-0.5 rounded border border-blue-900/50">RECOMMENDED</span>}
                {assignmentMode === "APPROVED" && <span className="text-emerald-400 bg-emerald-950/30 px-1.5 py-0.5 rounded border border-emerald-900/50">ACTIVE</span>}
                {assignmentMode === "CANDIDATE" && <span className="text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">CANDIDATE</span>}
              </div>
              {assignments.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {assignments.map((assignment, idx) => (
                    <div key={idx} className="bg-slate-800 text-slate-300 text-xs px-2 py-1 rounded flex items-center gap-2">
                      <span className="font-mono">{assignment.unit_id}</span>
                      <span className="text-emerald-400">ETA: {assignment.eta_minutes}m</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-red-400 text-sm font-medium">Unassigned</div>
              )}
            </div>
          </div>
        );
      })}
      {sortedIncidents.length === 0 && (
        <div className="text-slate-500 text-center py-8">No active incidents.</div>
      )}
    </div>
  );
}
