"use client";

import { useSession } from "@/lib/session-context";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/command",      label: "COMMAND" },
  { href: "/plans",        label: "PLANS" },
  { href: "/resilience",   label: "RESILIENCE" },
  { href: "/timeline",     label: "TIMELINE" },
  { href: "/architecture", label: "ARCHITECTURE" },
];

export default function CommandHeader() {
  const { state, health, loading, sessionId, createSession, resetSession, isDemoMode, setDemoMode } = useSession();
  const path = usePathname();

  const geminiStatus = health?.integrations.gemini ?? "unknown";
  const isConnected  = geminiStatus === "connected";

  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-2">
        <div className="flex items-center gap-3">
          <span className="text-red-500 text-xl font-bold">&#9650;</span>
          <div>
            <div className="text-sm font-black text-slate-100 tracking-widest">CRISIS COMMAND</div>
            <div className="text-xs text-slate-400">Emergency Response Decision Intelligence</div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Gemini status */}
          <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded border ${
            isConnected
              ? "border-emerald-700 bg-emerald-950/30 text-emerald-300"
              : "border-slate-700 bg-slate-800 text-slate-400"
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
            GEMINI {isConnected ? "CONNECTED" : "DEGRADED"}
          </div>

          {/* State version */}
          {state && (
            <div className="text-xs font-mono px-2 py-1 rounded border border-blue-800 bg-blue-950/30 text-blue-300">
              STATE v{state.version}
            </div>
          )}

          {/* Sim mode badge */}
          <div className="text-xs px-2 py-1 rounded border border-amber-700 bg-amber-950/30 text-amber-300 font-bold">
            &#9650; SIMULATION
          </div>

          {/* Controls */}
          {!sessionId ? (
            <button
              onClick={() => { setDemoMode(false); createSession(); }}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded border border-blue-600 bg-blue-950 text-blue-300 hover:bg-blue-900 transition-colors"
            >
              <span>&#9654;</span> START SESSION
            </button>
          ) : (
            <>
              {isDemoMode && (
                <span className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded border border-purple-600 bg-purple-950 text-purple-300">
                  <span>&#9654;</span> GUIDED DEMO
                </span>
              )}
              <button
                onClick={() => { setDemoMode(false); resetSession(); }}
                disabled={loading}
                className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded border border-slate-600 bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                <span>&#9632;</span> RESET
              </button>
            </>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex items-center px-6 gap-0 border-t border-slate-800">
        {NAV.map(({ href, label }) => {
          const active = path === href || path?.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`
                text-xs font-bold tracking-widest px-4 py-2 border-b-2 transition-colors
                ${active
                  ? "border-blue-500 text-blue-300"
                  : "border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600"}
              `}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
