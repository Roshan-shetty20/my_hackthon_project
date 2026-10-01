'use client';

import React, { useMemo } from 'react';
import { CrisisStateResponse } from '@/lib/api';

interface OperationalMapProps {
  state: CrisisStateResponse | null;
  selectedMissionId: string | null;
  onSelectMission: (id: string) => void;
}

export default function OperationalMap({ state, selectedMissionId, onSelectMission }: OperationalMapProps) {
  // Surat bounding box
  const minLat = 21.14;
  const maxLat = 21.21;
  const minLon = 72.78;
  const maxLon = 72.86;
  const mapWidth = 800;
  const mapHeight = 600;

  const project = (lat: number, lon: number) => {
    const x = ((lon - minLon) / (maxLon - minLon)) * mapWidth;
    const y = mapHeight - ((lat - minLat) / (maxLat - minLat)) * mapHeight;
    return { x, y };
  };

  const getUrgencyColor = (urgency: string | null) => {
    switch (urgency) {
      case 'CRITICAL': return '#ef4444'; // red-500
      case 'HIGH': return '#f59e0b'; // amber-500
      case 'MEDIUM': return '#eab308'; // yellow-500
      case 'LOW': return '#10b981'; // emerald-500
      default: return '#64748b'; // slate-500
    }
  };

  const getUnitColor = (status: string) => {
    switch (status) {
      case 'AVAILABLE': return '#3b82f6'; // blue-500
      case 'EN_ROUTE': return '#0ea5e9'; // sky-500
      case 'ON_SCENE': return '#10b981'; // emerald-500
      case 'BROKEN_DOWN': return '#ef4444'; // red-500
      default: return '#94a3b8'; // slate-400
    }
  };

  const activeMissions = useMemo(() => {
    return state ? Object.values(state.active_missions) : [];
  }, [state]);

  if (!state) {
    return <div className="flex items-center justify-center h-full bg-slate-950 text-slate-500">No data available</div>;
  }

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden flex items-center justify-center p-4">
      <div className="absolute top-4 left-4 bg-slate-900 border border-slate-800 p-3 rounded shadow-lg text-xs text-slate-300 z-10">
        <h4 className="font-semibold mb-2 text-slate-100">Legend</h4>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500 inline-block"></span> Critical Incident</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> High Incident</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 bg-blue-500 inline-block"></span> Available Unit</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 bg-sky-500 inline-block"></span> En Route Unit</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 bg-emerald-500 inline-block"></span> On Scene Unit</div>
          <div className="flex items-center gap-2"><span className="w-8 border-b-2 border-slate-600 inline-block"></span> Road</div>
          <div className="flex items-center gap-2"><span className="w-8 border-b-2 border-dashed border-red-500 inline-block"></span> Blocked Road</div>
          <div className="flex items-center gap-2"><span className="w-8 border-b-2 border-blue-400 inline-block"></span> Mission Route</div>
        </div>
      </div>

      <svg viewBox={`0 0 ${mapWidth} ${mapHeight}`} className="w-full h-full max-w-full max-h-full bg-slate-900 border border-slate-800 rounded">
        {/* Roads */}
        {state.road_conditions.map(road => {
          const from = project(road.from_lat, road.from_lon);
          const to = project(road.to_lat, road.to_lon);
          return (
            <line
              key={road.id}
              x1={from.x} y1={from.y} x2={to.x} y2={to.y}
              stroke={road.blocked ? '#ef4444' : '#475569'}
              strokeWidth={road.blocked ? 2 : 1}
              strokeDasharray={road.blocked ? "4,4" : "none"}
            />
          );
        })}

        {/* Mission Routes */}
        {activeMissions.map(mission => {
          if (!mission.route?.waypoints || mission.route.waypoints.length === 0) return null;
          const isSelected = mission.mission_id === selectedMissionId;
          const points = mission.route.waypoints.map(wp => {
            const p = project(wp[1], wp[0]); // assuming [lon, lat] for waypoints usually, but let's assume standard [lat, lon] based on api types
            // If the waypoints are actually [lon, lat] from standard GeoJSON:
            return `${p.x},${p.y}`;
          }).join(' ');
          
          // Re-projecting assuming waypoints are [lon, lat] from standard routing engines, if it's [lat, lon] we swap.
          // Let's assume the standard [lon, lat] from openrouteservice.
          const polyPoints = mission.route.waypoints.map(wp => {
            const p = project(wp[1], wp[0]); // wp[1] = lat, wp[0] = lon
            return `${p.x},${p.y}`;
          }).join(' ');

          return (
            <g key={`route-${mission.mission_id}`} onClick={() => onSelectMission(mission.mission_id)} style={{cursor: 'pointer'}}>
              <polyline
                points={polyPoints}
                fill="none"
                stroke={isSelected ? '#60a5fa' : '#3b82f6'} // blue-400 / blue-500
                strokeWidth={isSelected ? 4 : 2}
                strokeOpacity={isSelected ? 0.9 : 0.5}
              />
            </g>
          );
        })}

        {/* Units */}
        {state.units.map(unit => {
          const p = project(unit.latitude, unit.longitude);
          return (
            <g key={unit.id} transform={`translate(${p.x}, ${p.y})`}>
              <rect x="-6" y="-6" width="12" height="12" fill={getUnitColor(unit.status)} />
              <text x="8" y="4" fontSize="10" fill="#cbd5e1" fontFamily="monospace">{unit.id}</text>
            </g>
          );
        })}

        {/* Unit Current Positions if En Route (active missions) */}
        {activeMissions.map(mission => {
          if (mission.status !== 'EN_ROUTE') return null;
          const p = project(mission.current_latitude, mission.current_longitude);
          return (
            <g key={`pos-${mission.mission_id}`} transform={`translate(${p.x}, ${p.y})`}>
              <circle cx="0" cy="0" r="4" fill="#38bdf8" /> {/* sky-400 */}
            </g>
          );
        })}

        {/* Incidents */}
        {state.incidents.map(incident => {
          const p = project(incident.latitude, incident.longitude);
          return (
            <g key={incident.id} transform={`translate(${p.x}, ${p.y})`}>
              <circle cx="0" cy="0" r="6" fill={getUrgencyColor(incident.urgency)} stroke="#1e293b" strokeWidth="2" />
              <text x="8" y="4" fontSize="10" fill="#cbd5e1" fontFamily="monospace">{incident.id}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
