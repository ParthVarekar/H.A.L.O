import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
  summary: null,
  analysis: null,
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

function formatEventTime(event) {
  const videoTime = event.extra?.video_time_s;
  return typeof videoTime === "number" ? `${videoTime.toFixed(1)}s` : formatTime(event.ts_utc);
}

const SPEECH_RATE = 1.5;
const SPEECH_LABEL_WORDS = 8;
const SPEECH_CLAUSE_BREAK = /\s+(?:and|with|inside|into|in front|of)\s+/i;
const SPEECH_MAX_PENDING = 2;

let audioContext = null;

function unlockAudio() {
  const AudioCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtor) return null;
  if (!audioContext) audioContext = new AudioCtor();
  if (audioContext.state === "suspended") audioContext.resume().catch(() => undefined);
  return audioContext;
}

function playTone(frequency, durationMs, repeats = 1) {
  const context = unlockAudio();
  if (!context) return;
  for (let index = 0; index < repeats; index += 1) {
    const start = context.currentTime + index * (durationMs / 1000 + 0.08);
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.25, start + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + durationMs / 1000);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(start);
    oscillator.stop(start + durationMs / 1000 + 0.02);
  }
}

function describeCompletions(steps) {
  if (steps.length === 1) return `Step ${steps[0].number} done, ${steps[0].label}.`;
  const numbers = steps.map((step) => step.number);
  const consecutive = numbers.every((number, index) => index === 0 || number === numbers[index - 1] + 1);
  if (steps.length === 2) return `Steps ${numbers[0]} and ${numbers[1]} done.`;
  if (consecutive) return `Steps ${numbers[0]} to ${numbers[numbers.length - 1]} done.`;
  return `Steps ${numbers.slice(0, -1).join(", ")} and ${numbers[numbers.length - 1]} done.`;
}

function eventKey(event) {
  return `${event.ts_utc}|${event.step_id}|${event.step_status}|${event.alert_code || ""}`;
}

function StateBadge({ state, running }) {
  const label = running ? state.replaceAll("_", " ") : "stopped";
  return <span className={`state-badge ${running ? "is-live" : "is-idle"}`}>{label}</span>;
}

function AnalysisResult({ analysis, activities, summary, running, steps, currentStepId }) {
  const describe = (stepId) => steps.find((step) => step.id === stepId)?.description || stepId;
  const match =
    analysis.scores.find((score) => score.activity_id === analysis.activity_id) ||
    activities.find((activity) => activity.id === analysis.activity_id);
  const manual = analysis.recognized && analysis.sampled_frames === 0;
  return (
    <div className="analysis-result">
      <div className={`analysis-verdict ${analysis.recognized ? "is-recognized" : "is-unknown"}`}>
        <strong>{analysis.recognized ? `${manual ? "Selected" : "Recognised"}: ${match?.name || analysis.activity_id}` : "Experiment not recognised"}</strong>
        <span>{analysis.reason}</span>
      </div>
      {analysis.scores.length > 0 && (
        <div className="analysis-scores">
          {analysis.scores.map((score) => (
            <div className="analysis-score" key={score.activity_id}>
              <div className="analysis-score-label"><span>{score.name}</span><b>{Math.round(score.score * 100)}% of frames</b></div>
              <div className="confidence-track"><div style={{ width: `${Math.min(100, score.score * 100)}%` }} /></div>
              <small>Scene similarity {Math.round(score.mean_similarity * 100)}% · {score.has_detector ? "detector trained" : "no trained detector"}</small>
            </div>
          ))}
        </div>
      )}
      {analysis.recognized && match && !match.has_detector && (
        <div className="notice-banner">Step monitoring is unavailable: this activity has no trained detector yet.</div>
      )}
      {analysis.recognized && running && (
        <div className="notice-banner">Monitoring the procedure. Current step: {describe(currentStepId)}</div>
      )}
      {analysis.recognized && !running && summary && (
        <div className="analysis-summary">
          <strong>
            {summary.completed_steps.length} of {summary.total_steps} steps completed
            {summary.source_finished ? "" : " (analysis stopped before the end of the video)"}
          </strong>
          <ul>
            {steps.map((step) => {
              const done = summary.completed_steps.includes(step.id);
              const late = (summary.out_of_order_steps || []).includes(step.id);
              const skipped = (summary.skipped_steps || []).includes(step.id);
              const note = late ? " (out of order)" : skipped ? " (skipped)" : done ? "" : " (not reached)";
              return (
                <li className={done ? "done" : "missed"} key={step.id}>
                  <span>{done ? "✓" : "✗"}</span>
                  {step.description}
                  {note && <em>{note}</em>}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function App() {
  const [plan, setPlan] = useState({ name: "BAS-HAR", id: "", steps: [] });
  const [status, setStatus] = useState(EMPTY_STATUS);
  const [events, setEvents] = useState([]);
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [workspace, setWorkspace] = useState(() => new URLSearchParams(window.location.search).get("workspace") === "studio" ? "studio" : "operations");
  const [operationActivities, setOperationActivities] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [localAnalysis, setLocalAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [voiceOn, setVoiceOn] = useState(true);
  const [analyzableActivities, setAnalyzableActivities] = useState([]);
  const [selectedExperiment, setSelectedExperiment] = useState("");

  useEffect(() => {
    readJson("/api/analyze/activities").then(setAnalyzableActivities).catch(() => setAnalyzableActivities([]));
  }, []);
  const spokenEvents = useRef(null);
  const spokenSummary = useRef(undefined);

  const planRevision = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [nextStatus, nextEvents] = await Promise.all([
        readJson("/api/status"),
        readJson("/api/events"),
      ]);
      if (planRevision.current !== nextStatus.plan_revision) {
        const [nextPlan, nextActivities] = await Promise.all([
          readJson("/api/plan"),
          readJson("/api/operations/activities"),
        ]);
        planRevision.current = nextStatus.plan_revision;
        setPlan(nextPlan);
        setOperationActivities(nextActivities);
      }
      setStatus(nextStatus);
      setEvents(nextEvents);
      setSource((current) => current || nextStatus.source || "");
      setError(nextStatus.error || "");
      setLoaded(true);
    } catch (requestError) {
      setError(requestError.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 700);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    const blockNavigation = (event) => {
      if (event.dataTransfer?.types?.includes("Files")) event.preventDefault();
    };
    window.addEventListener("dragover", blockNavigation);
    window.addEventListener("drop", blockNavigation);
    return () => {
      window.removeEventListener("dragover", blockNavigation);
      window.removeEventListener("drop", blockNavigation);
    };
  }, []);

  const describeStep = useCallback(
    (stepId) => (plan.steps.find((step) => step.id === stepId)?.description || (stepId || "unknown step").replaceAll("_", " ")).replace(/[.\s]+$/, ""),
    [plan.steps],
  );

  const stepNumber = useCallback(
    (stepId) => {
      const index = plan.steps.findIndex((step) => step.id === stepId);
      return index >= 0 ? index + 1 : null;
    },
    [plan.steps],
  );

  const shortStep = useCallback(
    (stepId) =>
      describeStep(stepId)
        .replace(/\s*\([^)]*\)/g, "")
        .replace(/^slawosz\s+/i, "")
        .split(SPEECH_CLAUSE_BREAK)[0]
        .split(/\s+/)
        .slice(0, SPEECH_LABEL_WORDS)
        .join(" "),
    [describeStep],
  );

  const speechQueue = useRef({ messages: [], steps: [], current: null });

  const flushSpeech = useCallback(() => {
    if (!("speechSynthesis" in window)) return;
    const queue = speechQueue.current;
    if (queue.current) return;
    let text = null;
    let kind = null;
    if (queue.messages.length) {
      const next = queue.messages.shift();
      text = next.text;
      kind = next.kind;
    } else if (queue.steps.length) {
      const steps = queue.steps.splice(0).sort((a, b) => a.number - b.number);
      text = describeCompletions(steps);
      kind = "steps";
    }
    if (!text) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = SPEECH_RATE;
    const token = { kind, utterance };
    const finish = () => {
      if (queue.current === token) {
        queue.current = null;
        flushSpeech();
      }
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    queue.current = token;
    window.speechSynthesis.speak(utterance);
  }, []);

  const say = useCallback(
    (text, kind = "info") => {
      if (!voiceOn || !("speechSynthesis" in window)) return;
      const queue = speechQueue.current;
      if (kind === "alert") {
        queue.messages = [{ text, kind }, ...queue.messages.filter((item) => item.kind === "alert")];
        if (queue.current && queue.current.kind !== "alert") {
          queue.current = null;
          window.speechSynthesis.cancel();
        }
      } else if (kind === "summary") {
        queue.messages = [{ text, kind }];
        queue.steps = [];
        if (queue.current) {
          queue.current = null;
          window.speechSynthesis.cancel();
        }
      } else {
        queue.messages = [...queue.messages.slice(-(SPEECH_MAX_PENDING - 1)), { text, kind }];
      }
      flushSpeech();
    },
    [voiceOn, flushSpeech],
  );

  const announceStep = useCallback(
    (stepId) => {
      if (!voiceOn || !("speechSynthesis" in window)) return;
      const number = stepNumber(stepId);
      if (number === null) return;
      const queue = speechQueue.current;
      if (!queue.steps.some((item) => item.number === number)) {
        queue.steps.push({ number, label: shortStep(stepId) });
      }
      flushSpeech();
    },
    [voiceOn, stepNumber, shortStep, flushSpeech],
  );

  useEffect(() => {
    if (voiceOn || !("speechSynthesis" in window)) return;
    speechQueue.current = { messages: [], steps: [], current: null };
    window.speechSynthesis.cancel();
  }, [voiceOn]);

  useEffect(() => {
    if (!loaded) return;
    if (spokenEvents.current === null) {
      spokenEvents.current = new Set(events.map(eventKey));
      return;
    }
    for (const event of events) {
      const key = eventKey(event);
      if (spokenEvents.current.has(key)) continue;
      spokenEvents.current.add(key);
      const number = stepNumber(event.step_id);
      const name = number ? `step ${number}` : describeStep(event.step_id);
      const alerting = event.step_status === "skipped" || Boolean(event.alert_code);
      if (voiceOn && (alerting || event.step_status === "completed")) {
        if (alerting) playTone(440, 160, 2);
        else playTone(880, 90);
      }
      if (event.step_status === "skipped") {
        say(`Alert: ${name} skipped.`, "alert");
      } else if (event.alert_code === "OUT_OF_ORDER") {
        say(`Alert: ${name} done out of order.`, "alert");
      } else if (event.alert_code === "PAUSE_EXCEEDED") {
        say(`Alert: no progress on ${name}.`, "alert");
      } else if (event.step_status === "completed") {
        announceStep(event.step_id);
      }
    }
  }, [loaded, events, voiceOn, say, announceStep, stepNumber, describeStep]);

  useEffect(() => {
    const unlock = () => unlockAudio();
    window.addEventListener("pointerdown", unlock);
    window.addEventListener("keydown", unlock);
    window.addEventListener("drop", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
      window.removeEventListener("drop", unlock);
    };
  }, []);

  useEffect(() => {
    if (!loaded) return;
    const summary = status.summary;
    const key = summary && !status.running ? `${status.started_at}|${JSON.stringify(summary)}` : null;
    if (spokenSummary.current === undefined) {
      spokenSummary.current = key;
      return;
    }
    if (!key || key === spokenSummary.current) return;
    spokenSummary.current = key;
    const numbers = (ids) => ids.map((id) => stepNumber(id) ?? describeStep(id)).join(", ");
    const skipped = summary.skipped_steps || [];
    const missed = summary.missed_steps || [];
    const late = summary.out_of_order_steps || [];
    say(
      `Analysis finished. ${summary.completed_steps.length} of ${summary.total_steps} steps done.` +
        (skipped.length ? ` Skipped: step ${numbers(skipped)}.` : "") +
        (late.length ? ` Out of order: step ${numbers(late)}.` : "") +
        (missed.length ? ` Not reached: step ${numbers(missed)}.` : "") +
        (!skipped.length && !missed.length && !late.length ? " All in order." : ""),
      "summary",
    );
  }, [loaded, status.summary, status.running, status.started_at, say, stepNumber, describeStep]);

  const currentIndex = useMemo(
    () => plan.steps.findIndex((step) => step.id === status.current_step_id),
    [plan.steps, status.current_step_id],
  );
  const completed = status.state === "completed";
  const progress = completed ? plan.steps.length : Math.max(0, currentIndex + 1);
  const imageUrl = status.has_frame
    ? `/api/stream.mjpg?session=${encodeURIComponent(status.started_at || "current")}`
    : "";
  const analysis = status.analysis || localAnalysis;

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

  async function selectActivity(event) {
    const activityId = event.target.value;
    if (!activityId) return;
    setBusy(true);
    setError("");
    try {
      const selected = await readJson("/api/operations/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activity_id: activityId }),
      });
      setPlan(selected.plan);
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function analyzeFile(file) {
    if (!file) return;
    if (status.running) {
      setAnalysisError("Stop the running capture before analysing another video.");
      return;
    }
    setAnalyzing(true);
    setAnalysisError("");
    setLocalAnalysis(null);
    try {
      const data = await readJson("/api/analyze", {
        method: "POST",
        headers: {
          "X-Filename": encodeURIComponent(file.name),
          ...(selectedExperiment ? { "X-Activity-Id": selectedExperiment } : {}),
        },
        body: file,
      });
      setLocalAnalysis(data);
      const known = analyzableActivities.find((activity) => activity.id === data.activity_id);
      const match = data.scores.find((score) => score.activity_id === data.activity_id) || known;
      const verb = selectedExperiment ? "Selected" : "Recognised";
      if (!data.recognized) {
        say("Experiment not recognised.");
      } else if (match && !match.has_detector) {
        say(`${verb} ${match.name}, but step monitoring is not available for it yet.`);
      } else {
        say(`${verb} ${match?.name || data.activity_id}. Monitoring.`);
      }
      await refresh();
    } catch (requestError) {
      setAnalysisError(requestError.message);
    } finally {
      setAnalyzing(false);
    }
  }

  function handleDragOver(event) {
    if (!event.dataTransfer?.types?.includes("Files")) return;
    event.preventDefault();
    setDragActive(true);
  }

  function handleDragLeave(event) {
    if (event.currentTarget.contains(event.relatedTarget)) return;
    setDragActive(false);
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    analyzeFile(event.dataTransfer.files?.[0]);
  }

  return (
    <main
      className="app-shell"
      onDragOver={workspace === "operations" ? handleDragOver : undefined}
      onDragLeave={workspace === "operations" ? handleDragLeave : undefined}
      onDrop={workspace === "operations" ? handleDrop : undefined}
    >
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
          {operationActivities.length > 0 && <select className="operation-select" value={operationActivities.some((activity) => activity.id === plan.id) ? plan.id : ""} onChange={selectActivity} disabled={busy} aria-label="Approved activity"><option value="">Select approved activity</option>{operationActivities.map((activity) => <option key={activity.id} value={activity.id}>{activity.name}</option>)}</select>}
          <span className="connection"><span className="connection-dot" /> localhost:5767</span>
        </div>
      </header>

      {workspace === "studio" ? <TrainingStudio /> : <>
      <section className={`panel analyze-panel ${dragActive ? "is-dragging" : ""}`}>
        <div className="analyze-head">
          <div className="analyze-copy">
            <span className="section-kicker">VIDEO ANALYSIS</span>
            <h2>{dragActive ? "Release to analyse this video" : "Drop an experiment video anywhere on this page"}</h2>
            <p>The video's scenes are matched against the stored takes of every activity package. If the match has a trained detector, its procedure is then monitored step by step, with spoken alerts and a final list of completed and missed steps.</p>
          </div>
          <div className="analyze-actions">
            <label className="experiment-picker">
              <span>Experiment</span>
              <select
                value={selectedExperiment}
                onChange={(event) => setSelectedExperiment(event.target.value)}
                disabled={analyzing || status.running}
                aria-label="Experiment being performed"
              >
                <option value="">Auto-detect from video</option>
                {analyzableActivities.map((activity) => (
                  <option key={activity.id} value={activity.id}>
                    {activity.name}{activity.has_detector ? "" : " (no trained detector)"}
                  </option>
                ))}
              </select>
            </label>
            <label className={`button button-primary file-button ${analyzing || status.running ? "is-disabled" : ""}`}>
              {analyzing ? (selectedExperiment ? "Uploading…" : "Recognising…") : "Choose video"}
              <input
                type="file"
                accept="video/*"
                disabled={analyzing || status.running}
                onChange={(event) => {
                  analyzeFile(event.target.files?.[0]);
                  event.target.value = "";
                }}
              />
            </label>
            <label className="voice-toggle">
              <input type="checkbox" checked={voiceOn} onChange={(event) => setVoiceOn(event.target.checked)} />
              Voice alerts
            </label>
          </div>
        </div>
        {analysisError && <div className="error-banner">{analysisError}</div>}
        {analyzing && <div className="notice-banner">Uploading and recognising the experiment. This takes a few seconds per stored activity take.</div>}
        {analysis && !analyzing && (
          <AnalysisResult
            analysis={analysis}
            activities={analyzableActivities}
            summary={status.summary}
            running={status.running}
            steps={plan.steps}
            currentStepId={status.current_step_id}
          />
        )}
      </section>

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
                <span>Drop a video above, or start a video, webcam, or RTSP source below</span>
              </div>
            )}
            <div className="video-overlay"><span className="rec-dot" /> {status.running ? "LIVE" : "STANDBY"}</div>
            <div className="video-stats">
              {status.fps.toFixed(1)} FPS <span>·</span> frame {Math.max(0, status.frame_id)}
              {status.realtime_factor != null && <><span>·</span> {status.realtime_factor.toFixed(2)}x speed</>}
            </div>
          </div>
          {status.cpu_fallback && (
            <div className="error-banner">Running on the CPU although an NVIDIA GPU is present. Start the dashboard with .venv\Scripts\python.exe (startup.bat does this) so detection uses the GPU.</div>
          )}
          {status.running && status.falling_behind && (
            <div className="notice-banner">Analysis is falling behind the video; some frames are being skipped to keep real speed.</div>
          )}
          {Object.keys(status.timings_ms || {}).length > 0 && (
            <div className="perf-readout">
              <span>{status.device || "auto"}</span>
              <span>{status.encoder || "--"} JPEG</span>
              <span>display {Number(status.display_fps || 0).toFixed(1)} fps</span>
              {Object.entries(status.timings_ms).map(([stage, value]) => (
                <span key={stage}>{stage} {Number(value).toFixed(1)} ms</span>
              ))}
            </div>
          )}
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
          {!analysis && status.running && status.frame_id >= 0 && status.detections.length === 0 && (
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
                <div className="event-copy"><strong>{event.step_id.replaceAll("_", " ")}</strong><span>{event.alert_code ? `${event.alert_code.replaceAll("_", " ").toLowerCase()} · ` : ""}{event.evidence_summary}</span></div>
                <div className="event-meta"><b>{Math.round(event.confidence * 100)}%</b><span>{formatEventTime(event)}</span></div>
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
