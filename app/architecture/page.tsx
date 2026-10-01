import React from "react";

export default function ArchitecturePage() {
  const steps = [
    { id: 1, type: "input", name: "Incident Ingestion", desc: "Receive crisis signal & telemetry" },
    { id: 2, type: "deterministic", name: "Severity Assessment", desc: "Rule-based triage & priority scoring" },
    { id: 3, type: "ai", name: "Context Enrichment", desc: "LLM analyzes unstructured risk factors" },
    { id: 4, type: "deterministic", name: "Resource Constraint Check", desc: "Available units vs required capabilities" },
    { id: 5, type: "deterministic", name: "Route Optimization", desc: "Dijkstra over current road network" },
    { id: 6, type: "deterministic", name: "Plan Generation", desc: "Combinatorial allocation search" },
    { id: 7, type: "ai", name: "Plan Summarization", desc: "Generate plain-english strategy brief" },
    { id: 8, type: "deterministic", name: "Validation Pipeline", desc: "Check hard constraints & logic violations" },
    { id: 9, type: "deterministic", name: "Resilience Stress-Test", desc: "Simulate SPOFs & worst-case failures" },
    { id: 10, type: "ai", name: "Fragility Analysis", desc: "Identify cascading risks in plans" },
    { id: 11, type: "deterministic", name: "Scoring & Ranking", desc: "Rank plans by ETA, coverage, and resilience" },
    { id: 12, type: "ai", name: "Recommendation Rationale", desc: "Explain why top plan was selected" },
    { id: 13, type: "human", name: "Human Review", desc: "Commander reviews options & tradeoffs" },
    { id: 14, type: "human", name: "Plan Approval", desc: "Final authorization & dispatch" },
    { id: 15, type: "input", name: "Disruption Event", desc: "Roadblock or unit breakdown occurs" },
    { id: 16, type: "ai", name: "Diff & Replan Trigger", desc: "Explain what changed and auto-replan" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12">
          <h1 className="text-3xl font-bold text-white mb-2">Decision Architecture</h1>
          <p className="text-slate-400">16-Step Pipeline for Resilient Emergency Response</p>
        </header>

        <div className="flex flex-col lg:flex-row gap-12">
          
          {/* Left Column: Flowchart */}
          <div className="flex-1 relative">
            <div className="absolute left-6 top-4 bottom-4 w-0.5 bg-slate-800 -z-10"></div>
            
            <div className="space-y-4">
              {steps.map(step => {
                let border = "border-slate-700";
                let bg = "bg-slate-900";
                let iconColor = "text-slate-500";
                let symbol = "○";
                
                if (step.type === "deterministic") {
                  border = "border-blue-800/50";
                  bg = "bg-blue-950/20";
                  iconColor = "text-blue-400";
                  symbol = "⚙";
                } else if (step.type === "ai") {
                  border = "border-purple-800/50";
                  bg = "bg-purple-950/20";
                  iconColor = "text-purple-400";
                  symbol = "✧";
                } else if (step.type === "human") {
                  border = "border-emerald-800/50";
                  bg = "bg-emerald-950/20";
                  iconColor = "text-emerald-400";
                  symbol = "✓";
                } else if (step.type === "input") {
                  border = "border-slate-700";
                  bg = "bg-slate-800/50";
                  iconColor = "text-slate-300";
                  symbol = "→";
                }

                return (
                  <div key={step.id} className={`flex items-center gap-6 p-4 rounded-lg border ${border} ${bg} backdrop-blur-sm relative`}>
                    <div className="w-12 h-12 flex-shrink-0 flex items-center justify-center bg-slate-950 border border-slate-800 rounded-full font-mono text-sm shadow-xl z-10">
                      {step.id}
                    </div>
                    <div>
                      <h3 className="text-white font-medium flex items-center gap-2 mb-1">
                        <span className={iconColor}>{symbol}</span>
                        {step.name}
                      </h3>
                      <p className="text-sm text-slate-400">{step.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Legend & Details */}
          <div className="w-full lg:w-80 flex-shrink-0 space-y-6">
            
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
              <h3 className="text-sm font-semibold text-white mb-4 uppercase tracking-wider">Legend</h3>
              <ul className="space-y-3 text-sm">
                <li className="flex items-center gap-3">
                  <span className="text-blue-400 w-4 text-center">⚙</span>
                  <span className="text-slate-300">Deterministic Core</span>
                </li>
                <li className="flex items-center gap-3">
                  <span className="text-purple-400 w-4 text-center">✧</span>
                  <span className="text-slate-300">AI / LLM Node</span>
                </li>
                <li className="flex items-center gap-3">
                  <span className="text-emerald-400 w-4 text-center">✓</span>
                  <span className="text-slate-300">Human Approval</span>
                </li>
                <li className="flex items-center gap-3">
                  <span className="text-slate-400 w-4 text-center">→</span>
                  <span className="text-slate-300">External Input</span>
                </li>
              </ul>
            </div>

            <div className="bg-red-950/20 border border-red-900/50 rounded-lg p-5">
              <h3 className="text-sm font-semibold text-red-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                <span>⚠</span> What Gemini CANNOT Do
              </h3>
              <ul className="space-y-2 text-sm text-slate-300 list-disc list-inside">
                <li>Cannot approve final dispatches</li>
                <li>Cannot alter strict ETAs</li>
                <li>Cannot override resource constraints</li>
                <li>Cannot ignore worst-case stress tests</li>
              </ul>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
              <h3 className="text-sm font-semibold text-white mb-3 uppercase tracking-wider">Tech Stack</h3>
              <div className="space-y-2 text-sm text-slate-400">
                <p>Frontend: Next.js 16, React 19, Tailwind CSS v4</p>
                <p>Backend: FastAPI, Python 3.12</p>
                <p>Routing: OpenRouteService / Dijkstra</p>
                <p>LLM: Gemini 1.5 Pro</p>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
