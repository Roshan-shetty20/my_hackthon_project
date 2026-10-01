'use client';

import React from 'react';
import { useSession } from '@/lib/session-context';
import { DemoStage } from '@/lib/api';

interface StageProgressProps {
  onGeneratePlans: () => void;
  onDisrupt: () => void;
}

export default function StageProgress({ onGeneratePlans, onDisrupt }: StageProgressProps) {
  const { state, replan } = useSession();

  const STAGES: DemoStage[] = [
    'RECEIVE',
    'ALLOCATE',
    'COMPARE',
    'RECOMMEND',
    'ACTIVE',
    'POST_DISRUPTION',
    'REPLAN_REVIEW'
  ];

  const currentStage = state?.stage || 'RECEIVE';
  const currentIndex = STAGES.indexOf(currentStage);

  const getStageStatus = (stageIndex: number) => {
    if (stageIndex < currentIndex) return 'done';
    if (stageIndex === currentIndex) return 'active';
    return 'pending';
  };

  const getStageDescription = (stage: DemoStage) => {
    switch (stage) {
      case 'RECEIVE': return 'Receiving incident reports and assessing severity.';
      case 'ALLOCATE': return 'Generating candidate response plans.';
      case 'COMPARE': return 'Evaluating plans against resilience metrics.';
      case 'RECOMMEND': return 'Recommending optimal plan for approval.';
      case 'ACTIVE': return 'Executing approved plan. Monitoring operations.';
      case 'POST_DISRUPTION': return 'Disruption detected. Re-evaluating operational state.';
      case 'REPLAN_REVIEW': return 'Reviewing new plan recommendations post-disruption.';
      default: return '';
    }
  };

  const renderActionButton = () => {
    if (!state) return null;
    
    switch (currentStage) {
      case 'RECEIVE':
        return (
          <button
            onClick={onGeneratePlans}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors"
          >
            Generate Plans →
          </button>
        );
      case 'ACTIVE':
        return (
          <button
            onClick={onDisrupt}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors"
          >
            Trigger Disruption
          </button>
        );
      case 'POST_DISRUPTION':
        return (
          <button
            onClick={() => replan()}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded text-sm font-medium transition-colors"
          >
            Replan Operations →
          </button>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-slate-900 border-b border-slate-800 p-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        
        <div className="flex-1 w-full">
          <div className="flex items-center justify-between mb-2">
            {STAGES.map((stage, idx) => {
              const status = getStageStatus(idx);
              return (
                <div key={stage} className="flex flex-col items-center relative flex-1">
                  {/* Connecting Line */}
                  {idx < STAGES.length - 1 && (
                    <div className={`absolute top-3 left-[50%] right-[-50%] h-0.5 ${
                      idx < currentIndex ? 'bg-emerald-500' : 'bg-slate-700'
                    }`} />
                  )}
                  
                  {/* Node */}
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center z-10 text-xs ${
                    status === 'done' ? 'bg-emerald-500 text-white' :
                    status === 'active' ? 'bg-blue-500 text-white animate-pulse' :
                    'bg-slate-800 text-slate-500 border border-slate-700'
                  }`}>
                    {status === 'done' ? '✓' : (idx + 1)}
                  </div>
                  
                  {/* Label */}
                  <div className={`text-[10px] mt-2 uppercase tracking-wider font-semibold text-center hidden md:block ${
                    status === 'active' ? 'text-blue-400' :
                    status === 'done' ? 'text-slate-300' :
                    'text-slate-600'
                  }`}>
                    {stage.replace('_', ' ')}
                  </div>
                </div>
              );
            })}
          </div>
          
          <div className="text-sm text-slate-300 mt-4 bg-slate-950 p-3 rounded border border-slate-800">
            <span className="font-semibold text-blue-400 uppercase text-xs mr-2">{currentStage.replace('_', ' ')}</span>
            {getStageDescription(currentStage)}
          </div>
        </div>

        <div className="flex flex-col items-end gap-2 min-w-[200px]">
          <div className="text-xs text-slate-400 font-mono bg-slate-950 px-2 py-1 rounded border border-slate-800">
            State Version: {state?.version || 0}
          </div>
          {renderActionButton()}
        </div>
      </div>
    </div>
  );
}
