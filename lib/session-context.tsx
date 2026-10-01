"use client";

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { api, CrisisStateResponse, DemoStage, ExplanationResponse, HealthResponse } from "@/lib/api";

interface SessionCtx {
  sessionId: string | null;
  state: CrisisStateResponse | null;
  health: HealthResponse | null;
  explanation: ExplanationResponse | null;
  loading: boolean;
  error: string | null;
  isDemoMode: boolean;
  setDemoMode: (val: boolean) => void;
  // Actions
  createSession: () => Promise<void>;
  resetSession: () => Promise<void>;
  generatePlans: () => Promise<void>;
  replan: () => Promise<void>;
  approvePlan: (planId: string) => Promise<void>;
  rejectPlan: () => Promise<void>;
  triggerBreakdown: (unitId: string) => Promise<void>;
  triggerRoadBlock: (roadId: string) => Promise<void>;
  simulateStep: () => Promise<string>;
  applyDisruptions: (events: Array<{event_type: string; payload: Record<string, unknown>}>) => Promise<void>;

  tickTime: () => Promise<void>;

  refreshState: (sid?: string) => Promise<void>;
  fetchExplanation: () => Promise<void>;
}

const Ctx = createContext<SessionCtx | null>(null);

const SESSION_KEY = "cc_session_id";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isDemoMode, setDemoMode] = useState<boolean>(false);
  const [state, setState] = useState<CrisisStateResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    // Fetch health on mount
    api.health().then(setHealth).catch(() => {});

    // Restore session from localStorage
    const saved = typeof window !== "undefined" ? localStorage.getItem(SESSION_KEY) : null;
    if (saved) {
      setSessionId(saved);
      api.getState(saved)
        .then(s => { if (mounted.current) setState(s); })
        .catch(() => {
          // Session expired — clear it
          localStorage.removeItem(SESSION_KEY);
          setSessionId(null);
        });
    }

    return () => { mounted.current = false; };
  }, []);

  const wrap = async (fn: () => Promise<void>) => {
    setLoading(true);
    setError(null);
    try {
      await fn();
    } catch (e: unknown) {
      if (mounted.current) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  const refreshState = useCallback(async (sid?: string) => {
    const targetId = sid || sessionId;
    if (!targetId) return;
    const s = await api.getState(targetId);
    if (mounted.current) setState(s);
  }, [sessionId]);

  const createSession = async () =>
    wrap(async () => {
      const r = await api.createSession();
      if (mounted.current) {
        setSessionId(r.session_id);
        localStorage.setItem(SESSION_KEY, r.session_id);
        setExplanation(null);
      }
      await refreshState(r.session_id);
      await api.health().then(setHealth).catch(() => {});
    });

  const resetSession = async () =>
    wrap(async () => {
      const sid = sessionId;
      if (!sid) { await createSession(); return; }
      await api.resetSession(sid);
      setExplanation(null);
      await refreshState();
    });

  const replan = async () =>
    wrap(async () => {
      if (!sessionId) return;
      await api.replan(sessionId);
      await refreshState();
      try {
        const expl = await api.getExplanation(sessionId);
        if (mounted.current) setExplanation(expl);
      } catch { /* non-fatal */ }
    });

  const generatePlans = async () =>
    wrap(async () => {
      if (!sessionId) return;
      await api.generatePlans(sessionId);
      await refreshState();
      // Auto-fetch explanation after plans generated
      try {
        const expl = await api.getExplanation(sessionId);
        if (mounted.current) setExplanation(expl);
      } catch { /* non-fatal */ }
    });

  const approvePlan = async (planId: string) =>
    wrap(async () => {
      if (!sessionId) return;
      await api.approvePlan(sessionId, planId);
      await refreshState();
    });

  const rejectPlan = async () =>
    wrap(async () => {
      if (!sessionId) return;
      await api.rejectPlan(sessionId);
      await refreshState();
    });

  const triggerBreakdown = async (unitId: string) =>
    wrap(async () => {
      if (!sessionId) return;
      await api.breakdown(sessionId, unitId);
      await refreshState();
      try {
        const expl = await api.getExplanation(sessionId);
        if (mounted.current) setExplanation(expl);
      } catch { /* non-fatal */ }
    });

  const triggerRoadBlock = async (roadId: string) =>
    wrap(async () => {
      if (!sessionId) return;
      await api.roadBlock(sessionId, roadId);
      await refreshState();
      try {
        const expl = await api.getExplanation(sessionId);
        if (mounted.current) setExplanation(expl);
      } catch { /* non-fatal */ }
    });

  const applyDisruptions = async (events: Array<{event_type: string; payload: Record<string, unknown>}>) =>
    wrap(async () => {
      if (!sessionId) return;
      await api.batchEvents(sessionId, events);
      await refreshState();
      try {
        const expl = await api.getExplanation(sessionId);
        if (mounted.current) setExplanation(expl);
      } catch { /* non-fatal */ }
    });

  const tickTime = async (): Promise<void> => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await api.tickTime(sessionId);
      if (mounted.current) setState(data);
    } catch (e: any) {
      if (mounted.current) setError(e.message);
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  const simulateStep = async (): Promise<string> => {
    if (!sessionId) return "";
    setLoading(true);
    setError(null);
    try {
      const r = await api.simulateStep(sessionId);
      await refreshState();
      if (r.event) {
        const desc = r.event.event_type.replace(/_/g, " ").toUpperCase();
        return desc;
      }
      return "Event processed";
    } catch (e: unknown) {
      if (mounted.current) setError(e instanceof Error ? e.message : String(e));
      return "";
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  const fetchExplanation = async () =>
    wrap(async () => {
      if (!sessionId) return;
      const expl = await api.getExplanation(sessionId);
      if (mounted.current) setExplanation(expl);
    });

  return (
    <Ctx.Provider value={{
      sessionId, state, health, explanation, loading, error, isDemoMode, setDemoMode,
      createSession, resetSession, generatePlans, replan,
      approvePlan, rejectPlan, triggerBreakdown, triggerRoadBlock,
      tickTime,
    simulateStep, applyDisruptions, refreshState, fetchExplanation,
    }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSession() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
