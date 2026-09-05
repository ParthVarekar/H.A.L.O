import { useCallback, useEffect, useMemo, useState } from "react";

import TrainingStudio from "./TrainingStudio";

const EMPTY_STATUS = {
  running: false,
  source: "",
  frame_id: -1,
  fps: 0,
  state: "idle",
  current_step_id: "",
  current_step_description: "Waiting for a procedure plan",
  next_step_id: null,
  confidence: 0,
  detections: [],
  events: [],
  message: "Connecting to capture service",
  error: null,
  has_frame: false,
  buffer_segment_count: 0,
  device: "auto",
};

async function readJson(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function formatTime(value) {
  if (!value) return "--:--:--";
  return new Date(value).toLocaleTimeString([], { hour12: false });
}

function StateBadge({ state, running }) {
  const label = running ? state.replaceAll("_", " ") : "stopped";
  return <span className={`state-badge ${running ? "is-live" : "is-idle"}`}>{label}</span>;
}

function App() {
  const [plan, setPlan] = useState({ name: "BAS-HAR", id: "", steps: [] });
  const [status, setStatus] = useState(EMPTY_STATUS);
  const [events, setEvents] = useState([]);
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [workspace, setWorkspace] = useState("operations");

  const refresh = useCallback(async () => {
    try {
      const [nextPlan, nextStatus, nextEvents] = await Promise.all([
        readJson("/api/plan"),
        readJson("/api/status"),
        readJson("/api/events"),
      ]);
      setPlan(nextPlan);
      setStatus(nextStatus);
      setEvents(nextEvents);
      setSource((current) => current || nextStatus.source || "");
      setError(nextStatus.error || "");
    } catch (requestError) {
      setError(requestError.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 700);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const currentIndex = useMemo(
    () => plan.steps.findIndex((step) => step.id === status.current_step_id),
    [plan.steps, status.current_step_id],
  );
  const completed = status.state === "completed";
  const progress = completed ? plan.steps.length : Math.max(0, currentIndex + 1);
  const imageUrl = status.has_frame
    ? `/api/stream.mjpg?session=${encodeURIComponent(status.started_at || "current")}`
    : "";

  async function startCapture() {
    setBusy(true);
    setError("");
    try {
      await readJson("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source }),
      });
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function stopCapture() {
    setBusy(true);
    try {
      await readJson("/api/stop", { method: "POST" });
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function silenceAlerts() {
    try {
      await readJson("/api/silence", { method: "POST" });
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">BH</div>
          <div>
            <div className="eyebrow">ON-BOARD ACTIVITY RECOGNITION</div>
            <h1>bas-har</h1>
          </div>
        </div>
        <div className="header-meta">
          <nav className="workspace-nav" aria-label="Workspace">
            <button className={workspace === "operations" ? "active" : ""} onClick={() => setWorkspace("operations")} type="button">Operations</button>
            <button className={workspace === "studio" ? "active" : ""} onClick={() => setWorkspace("studio")} type="button">Training Studio</button>
          </nav>
          <span className="plan-chip">{plan.id || "plan loading"}</span>
          <span className="connection"><span className="connection-dot" /> localhost:5767</span>
        </div>
      </header>

      {workspace === "studio" ? <TrainingStudio /> : <>
      <section className="hero-grid">
        <article className="panel video-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">ASTRONAUT VIEW</span>
              <h2>Live procedure feed</h2>
            </div>
            <StateBadge state={status.state} running={status.running} />
          </div>
          <div className="video-frame">
            {imageUrl ? (
              <img src={imageUrl} alt="Current capture frame" />
            ) : (
              <div className="video-empty">
                <div className="pulse-ring" />
                <strong>{status.message || "Waiting for capture"}</strong>
                <span>Start a video, webcam, or RTSP source below</span>
              </div>
            )}
            <div className="video-overlay"><span className="rec-dot" /> {status.running ? "LIVE" : "STANDBY"}</div>
            <div className="video-stats">{status.fps.toFixed(1)} FPS <span>·</span> frame {Math.max(0, status.frame_id)}</div>
          </div>
          <div className="source-row">
            <label htmlFor="source">Capture source</label>
            <input
              id="source"
              value={source}
              onChange={(event) => setSource(event.target.value)}
              placeholder="MP4 path, webcam index, or RTSP URL"
            />
            <button className="button button-primary" onClick={startCapture} disabled={busy || status.running}>
              Start
            </button>
            <button className="button button-quiet" onClick={stopCapture} disabled={busy || !status.running}>
              Stop
            </button>
          </div>
          {error && <div className="error-banner">{error}</div>}
          {status.running && status.frame_id >= 0 && status.detections.length === 0 && (
            <div className="notice-banner">Frames are arriving, but the selected model has no target detections yet. Use a fine-tuned model for the red/blue boxes.</div>
          )}
        </article>

        <aside className="side-stack">
          <article className="panel current-panel">
            <div className="panel-heading compact">
              <span className="section-kicker">CURRENT STEP</span>
              <span className="step-count">{progress} / {plan.steps.length || "--"}</span>
            </div>
            <div className="step-id">{status.current_step_id || "--"}</div>
            <p>{status.current_step_description}</p>
            <div className="confidence-label"><span>Evidence confidence</span><strong>{Math.round(status.confidence * 100)}%</strong></div>
            <div className="confidence-track"><div style={{ width: `${Math.min(100, status.confidence * 100)}%` }} /></div>
            <div className="next-step"><span>NEXT</span><strong>{status.next_step_id || (completed ? "procedure complete" : "waiting")}</strong></div>
          </article>
          <article className="panel telemetry-panel">
            <div className="panel-heading compact"><span className="section-kicker">TELEMETRY</span><span className="telemetry-live">{status.running ? "STREAMING" : "IDLE"}</span></div>
            <div className="telemetry-grid">
              <div><span>Detections</span><strong>{status.detections.length}</strong></div>
              <div><span>Engine state</span><strong>{status.state.replaceAll("_", " ")}</strong></div>
              <div><span>Inference</span><strong>{status.device || "auto"}</strong></div>
              <div><span>Source</span><strong className="truncate">{status.source || "--"}</strong></div>
              <div><span>Buffer</span><strong>{status.buffer_segment_count} segments</strong></div>
              <div><span>Log</span><strong className="truncate">{status.log_path ? status.log_path.split("\\").pop() : "not started"}</strong></div>
            </div>
            <button className="silence-button" onClick={silenceAlerts} disabled={!status.running}>Silence alerts for 60s</button>
          </article>
        </aside>
      </section>

      <section className="lower-grid">
        <article className="panel timeline-panel">
          <div className="panel-heading">
            <div><span className="section-kicker">PROCEDURE</span><h2>{plan.name}</h2></div>
            <span className="muted-label">{plan.version || ""}</span>
          </div>
          <div className="timeline">
            {plan.steps.map((step, index) => {
              const isCurrent = step.id === status.current_step_id;
              const isDone = completed || (currentIndex >= 0 && index < currentIndex);
              return (
                <div className={`timeline-step ${isCurrent ? "current" : ""} ${isDone ? "done" : ""}`} key={step.id}>
                  <div className="timeline-marker">{isDone ? "✓" : String(index + 1).padStart(2, "0")}</div>
                  <div className="timeline-copy"><strong>{step.id.replaceAll("_", " ")}</strong><span>{step.description}</span></div>
                  <span className="timeline-kind">{step.evidence.join(" + ")}</span>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel events-panel">
          <div className="panel-heading"><div><span className="section-kicker">EVENT STREAM</span><h2>Recent events</h2></div><span className="event-count">{events.length}</span></div>
          <div className="events-list">
            {events.length === 0 ? (
              <div className="events-empty">Engine events will appear here as evidence changes.</div>
            ) : events.slice().reverse().map((event, index) => (
              <div className="event-row" key={`${event.ts_utc}-${index}`}>
                <div className={`event-icon ${event.alert_code ? "alert" : event.step_status === "completed" ? "complete" : "progress"}`}>{event.alert_code ? "!" : event.step_status === "completed" ? "✓" : "·"}</div>
                <div className="event-copy"><strong>{event.step_id.replaceAll("_", " ")}</strong><span>{event.evidence_summary}</span></div>
                <div className="event-meta"><b>{Math.round(event.confidence * 100)}%</b><span>{formatTime(event.ts_utc)}</span></div>
              </div>
            ))}
          </div>
        </article>
      </section>
      </>}
      <footer className="footer">BAS-HAR · {plan.name} · rule/procedure FSM primary · laptop edge target</footer>
    </main>
  );
}

export default App;
