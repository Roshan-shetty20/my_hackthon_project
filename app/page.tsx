import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
      <main className="max-w-6xl mx-auto px-6 py-20 flex flex-col items-center text-center">
        
        {/* SIMULATION MODE badge */}
        <div className="mb-8 inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-sm tracking-wide">
          <span className="text-xs">●</span> SIMULATION MODE
        </div>

        {/* Hero Section */}
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white mb-6">
          CRISIS COMMAND
        </h1>
        <p className="text-xl md:text-2xl text-slate-400 mb-4 font-light">
          Resilient Decision Intelligence for Emergency Response
        </p>
        <p className="text-lg text-slate-500 mb-12 italic">
          &quot;Can your response plan survive the next surprise?&quot;
        </p>

        {/* Decision pipeline breadcrumbs */}
        <div className="flex flex-wrap justify-center items-center gap-3 text-sm font-medium text-slate-500 mb-16 tracking-wider">
          <span className="text-slate-300">INCIDENT</span>
          <span>→</span>
          <span className="text-slate-300">ASSESS</span>
          <span>→</span>
          <span className="text-blue-400">ALLOCATE</span>
          <span>→</span>
          <span className="text-blue-400">VALIDATE</span>
          <span>→</span>
          <span className="text-purple-400">STRESS-TEST</span>
          <span>→</span>
          <span className="text-purple-400">RECOMMEND</span>
          <span>→</span>
          <span className="text-emerald-400">APPROVE</span>
          <span>→</span>
          <span className="text-slate-300">REPLAN</span>
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-4 mb-24">
          <Link 
            href="/command" 
            className="px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium tracking-wide transition-colors flex items-center justify-center gap-2"
          >
            LAUNCH COMMAND CENTER <span>▶</span>
          </Link>
          <Link 
            href="/architecture" 
            className="px-8 py-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded font-medium tracking-wide transition-colors"
          >
            HOW IT WORKS
          </Link>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 w-full mb-24 text-left">
          <div className="p-6 rounded-lg border border-slate-800 bg-slate-900/50">
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-blue-400">■</span> Incident Assessment
            </h3>
            <p className="text-slate-400 leading-relaxed text-sm">
              Rapid ingestion of emergency data with deterministic severity routing. Critical resources are immediately locked while AI processes edge cases.
            </p>
          </div>
          <div className="p-6 rounded-lg border border-slate-800 bg-slate-900/50">
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-purple-400">◆</span> Plan Survivability
            </h3>
            <p className="text-slate-400 leading-relaxed text-sm">
              Multiple response strategies are generated and stress-tested against worst-case disruptions. We don&apos;t just find the fastest route; we find the most resilient plan.
            </p>
          </div>
          <div className="p-6 rounded-lg border border-slate-800 bg-slate-900/50">
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-emerald-400">▲</span> Dynamic Replanning
            </h3>
            <p className="text-slate-400 leading-relaxed text-sm">
              When reality diverges from the plan, the system instantly recalculates resource allocations and explains exactly what changed and why.
            </p>
          </div>
        </div>

        {/* Three-column differentiator */}
        <div className="w-full pt-16 border-t border-slate-800/50">
          <h2 className="text-2xl font-bold text-white mb-12">The Hybrid Intelligence Approach</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-blue-900/30 border border-blue-500/30 flex items-center justify-center text-blue-400 text-2xl mb-4">
                ⚙
              </div>
              <h4 className="text-blue-400 font-semibold mb-2">Deterministic Core</h4>
              <p className="text-sm text-slate-500 text-center">
                Hard constraints, routing, ETAs, and assignments are handled by fast, provable optimization algorithms. Zero hallucination risk.
              </p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-purple-900/30 border border-purple-500/30 flex items-center justify-center text-purple-400 text-2xl mb-4">
                ✧
              </div>
              <h4 className="text-purple-400 font-semibold mb-2">Gemini Explanation</h4>
              <p className="text-sm text-slate-500 text-center">
                AI translates complex matrix state changes into plain-english tradeoffs, highlighting risks and single points of failure.
              </p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-emerald-900/30 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-2xl mb-4">
                ✓
              </div>
              <h4 className="text-emerald-400 font-semibold mb-2">Human Commander</h4>
              <p className="text-sm text-slate-500 text-center">
                The human remains in charge of final approvals, maintaining accountability and applying contextual judgment.
              </p>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
