import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  AppBar,
  Callout,
  DetailsPanel,
  DropOverlay,
  LiveSourceRow,
  MetricStrip,
  ModelAnswers,
  ProcedurePanel,
  SessionHeader,
  SessionLog,
  VideoStage,
  formatVideoTime,
} from "./Operations";
import TrainingStudio from "./TrainingStudio";
import { Announcer, ownsVoice, startVoiceOwnership } from "./voice";

const RECOGNITION_MODES = {
  zero_shot: "Described mode",
  hybrid: "Trained detector + questions",
  trained: "Trained detector",
};

const EMPTY_STATUS = {
  running: false,
  source: "",
  frame_id: -1,
  fps: 0,
  state: "idle",
  current_step_id: "",
  current_step_description: "",
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
  mode: "trained",
  questions: 0,
  questions_answered: 0,
  answers: {},
  show_boxes: true,
  video_time_s: 0,
};

const SESSION_LOG_LIMIT = 500;
const LOG_DISPLAY_LIMIT = 200;
const UPLOAD_PATH = /[\\/]logs[\\/]uploads[\\/]/;
const BOXES_PREFERENCE_KEY = "bas-har-show-boxes";

const SPEECH_RATE = 1.5;
const SPEECH_LABEL_WORDS = 8;
const SPEECH_CLAUSE_BREAK = /\s+(?:and|with|inside|into|in front|of)\s+/i;

async function readJson(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function formatClock(value) {
  if (!value) return "";
  return new Date(value).toLocaleTimeString([], { hour12: false });
}

function baseName(path) {
  return path ? String(path).split(/[\\/]/).pop() : "";
}

function shortGpuName(hardware) {
  if (!hardware) return "";
  if (!hardware.cuda_available) return "CPU only";
  return (hardware.device_name || hardware.device || "GPU").replace(/^NVIDIA\s+(GeForce\s+)?/i, "");
}

function readBoxesPreference() {
  try {
    const stored = window.localStorage.getItem(BOXES_PREFERENCE_KEY);
    return stored === null ? null : stored !== "off";
  } catch {
    return null;
  }
}

function writeBoxesPreference(showBoxes) {
  try {
    window.localStorage.setItem(BOXES_PREFERENCE_KEY, showBoxes ? "on" : "off");
  } catch {
    return;
  }
}

function capitalise(text) {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

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

function eventKey(event) {
  return `${event.ts_utc}|${event.step_id}|${event.step_status}|${event.alert_code || ""}`;
}

function isAlertEvent(event) {
  return event.step_status === "skipped" || Boolean(event.alert_code);
}

function App() {
  const [plan, setPlan] = useState({ name: "", id: "", steps: [] });
  const [status, setStatus] = useState(EMPTY_STATUS);
  const [events, setEvents] = useState([]);
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [workspace, setWorkspace] = useState(() => new URLSearchParams(window.location.search).get("workspace") === "studio" ? "studio" : "operations");
  const [operationActivities, setOperationActivities] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [connected, setConnected] = useState(true);
  const [hardware, setHardware] = useState(null);
  const [localAnalysis, setLocalAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [voiceOn, setVoiceOn] = useState(true);
  const [voiceHere, setVoiceHere] = useState(true);
  const [analyzableActivities, setAnalyzableActivities] = useState([]);
  const [selectedExperiment, setSelectedExperiment] = useState("");
  const [previewPlan, setPreviewPlan] = useState(null);
  const [liveOpen, setLiveOpen] = useState(false);
  const [sessionLog, setSessionLog] = useState([]);
  const [logFilter, setLogFilter] = useState("all");
  const [dismissedAlert, setDismissedAlert] = useState(null);
  const [showBoxes, setShowBoxes] = useState(() => readBoxesPreference() ?? true);
  const [stillVersion, setStillVersion] = useState(0);

  const spokenEvents = useRef(null);
  const spokenSummary = useRef(undefined);
  const sessionKey = useRef(null);
  const planRevision = useRef(null);
  const boxesSynced = useRef(false);
  const pendingBoxes = useRef(null);
  const announcer = useRef(null);
  if (announcer.current === null) announcer.current = new Announcer(SPEECH_RATE);

  useEffect(() => {
    readJson("/api/analyze/activities").then(setAnalyzableActivities).catch(() => setAnalyzableActivities([]));
    readJson("/api/hardware").then(setHardware).catch(() => setHardware(null));
  }, []);

  useEffect(() => startVoiceOwnership(), []);

  useEffect(() => {
    const update = () => setVoiceHere(ownsVoice());
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, []);

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
      setSource((current) => current || (UPLOAD_PATH.test(nextStatus.source || "") ? "" : nextStatus.source || ""));
      setError(nextStatus.error || "");
      setConnected(true);
      setLoaded(true);
    } catch (requestError) {
      setConnected(false);
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

  const applyBoxes = useCallback(async (next) => {
    pendingBoxes.current = next;
    setShowBoxes(next);
    try {
      await readJson("/api/display", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ show_boxes: next }),
      });
      setStillVersion((version) => version + 1);
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      pendingBoxes.current = null;
    }
  }, [refresh]);

  useEffect(() => {
    if (!loaded) return;
    if (!boxesSynced.current) {
      boxesSynced.current = true;
      const saved = readBoxesPreference();
      if (saved !== null && saved !== status.show_boxes) {
        applyBoxes(saved);
        return;
      }
    }
    if (pendingBoxes.current === null && status.show_boxes !== showBoxes) {
      setShowBoxes(status.show_boxes);
      setStillVersion((version) => version + 1);
    }
  }, [loaded, status.show_boxes, showBoxes, applyBoxes]);

  function changeShowBoxes(next) {
    writeBoxesPreference(next);
    applyBoxes(next);
  }

  useEffect(() => {
    const key = status.started_at || "none";
    const reset = sessionKey.current !== key;
    sessionKey.current = key;
    setSessionLog((current) => {
      const base = reset ? [] : current;
      const seen = new Set(base.map((entry) => entry.key));
      const additions = events
        .filter((event) => !seen.has(eventKey(event)))
        .map((event) => ({ ...event, key: eventKey(event) }));
      if (!reset && additions.length === 0) return current;
      return [...base, ...additions].slice(-SESSION_LOG_LIMIT);
    });
    if (reset) setDismissedAlert(null);
  }, [events, status.started_at]);

  useEffect(() => {
    if (!selectedExperiment) {
      setPreviewPlan(null);
      return undefined;
    }
    let cancelled = false;
    readJson(`/api/activities/${encodeURIComponent(selectedExperiment)}/plan`)
      .then((selected) => {
        if (cancelled) return;
        setPreviewPlan({
          id: selected.id,
          name: selected.name,
          version: selected.version,
          steps: selected.steps.map((step) => ({
            id: step.id,
            description: step.description,
            evidence: step.evidence.map((rule) => rule.kind),
          })),
        });
      })
      .catch(() => {
        if (!cancelled) setPreviewPlan(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedExperiment]);

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

  const say = useCallback(
    (text, kind = "info") => {
      if (!voiceOn || !ownsVoice()) return;
      announcer.current.enqueue(text, kind);
    },
    [voiceOn],
  );

  useEffect(() => {
    if (!voiceOn) announcer.current.clear();
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
      if (!voiceOn || !ownsVoice()) continue;
      const number = stepNumber(event.step_id);
      const name = number ? `Step ${number}` : capitalise(describeStep(event.step_id));
      if (isAlertEvent(event)) {
        playTone(440, 160, 2);
        if (event.step_status === "skipped") say(`Alert. ${name} skipped.`, "alert");
        else if (event.alert_code === "OUT_OF_ORDER") say(`Alert. ${name} done out of order.`, "alert");
        else if (event.alert_code === "PAUSE_EXCEEDED") say(`Alert. No progress on ${name.toLowerCase()}.`, "alert");
        else say(`Alert on ${name.toLowerCase()}.`, "alert");
      } else if (event.step_status === "completed") {
        playTone(880, 90);
        say(`${name} done. ${capitalise(shortStep(event.step_id))}.`, "step");
      }
    }
  }, [loaded, events, voiceOn, say, stepNumber, describeStep, shortStep]);

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

  const frameSession = encodeURIComponent(status.started_at || "current");
  const imageUrl = !status.has_frame
    ? ""
    : status.running
      ? `/api/stream.mjpg?session=${frameSession}`
      : `/api/frame.jpg?session=${frameSession}&v=${stillVersion}`;
  const analysis = status.analysis || localAnalysis;
  const showingPreview = Boolean(previewPlan) && !status.running && previewPlan.id !== plan.id;
  const displayPlan = showingPreview ? previewPlan : plan;
  const finishedSummary = status.running ? null : status.summary;

  const toLogEntry = useCallback(
    (event) => {
      const number = stepNumber(event.step_id);
      const label = number ? `Step ${number}` : describeStep(event.step_id);
      const time = formatVideoTime(event.extra?.video_time_s) || formatClock(event.ts_utc);
      const base = { key: event.key, time, detail: describeStep(event.step_id), technical: event.evidence_summary };
      if (event.step_status === "skipped") return { ...base, tone: "danger", icon: "skip", title: `${label} skipped`, isAlert: true };
      if (event.alert_code === "OUT_OF_ORDER") return { ...base, tone: "warn", icon: "clock", title: `${label} done out of order`, isAlert: true };
      if (event.alert_code === "PAUSE_EXCEEDED") return { ...base, tone: "warn", icon: "alert", title: `No progress on ${label.toLowerCase()}`, isAlert: true };
      if (event.alert_code) {
        const code = event.alert_code.replaceAll("_", " ").toLowerCase();
        return { ...base, tone: "danger", icon: "alert", title: `${capitalise(code)} on ${label.toLowerCase()}`, isAlert: true };
      }
      if (event.step_status === "completed") return { ...base, tone: "ok", icon: "check", title: `${label} completed`, isStep: true };
      if (event.step_status === "anomalous") return { ...base, tone: "warn", icon: "alert", title: `Unusual evidence on ${label.toLowerCase()}` };
      return { ...base, tone: "muted", icon: "dot", title: `${label} evidence ${Math.round(event.confidence * 100)}%`, isUpdate: true };
    },
    [stepNumber, describeStep],
  );

  const logEntries = useMemo(() => sessionLog.map(toLogEntry).reverse(), [sessionLog, toLogEntry]);
  const logCounts = useMemo(
    () => ({
      all: logEntries.filter((entry) => !entry.isUpdate).length,
      steps: logEntries.filter((entry) => entry.isStep).length,
      alerts: logEntries.filter((entry) => entry.isAlert).length,
      evidence: logEntries.filter((entry) => entry.isUpdate).length,
    }),
    [logEntries],
  );
  const visibleLog = useMemo(() => {
    const filtered = logEntries.filter((entry) => {
      if (logFilter === "steps") return entry.isStep;
      if (logFilter === "alerts") return entry.isAlert;
      if (logFilter === "evidence") return entry.isUpdate;
      return !entry.isUpdate;
    });
    return filtered.slice(0, LOG_DISPLAY_LIMIT);
  }, [logEntries, logFilter]);

  const latestAlert = useMemo(() => {
    for (let index = sessionLog.length - 1; index >= 0; index -= 1) {
      if (isAlertEvent(sessionLog[index])) return sessionLog[index];
    }
    return null;
  }, [sessionLog]);
  const activeAlert = latestAlert && latestAlert.key !== dismissedAlert ? toLogEntry(latestAlert) : null;

  const stepsView = useMemo(() => {
    if (showingPreview) return displayPlan.steps.map((step) => ({ ...step, state: "pending" }));
    const completedIds = new Set(finishedSummary?.completed_steps || []);
    const skippedIds = new Set(finishedSummary?.skipped_steps || []);
    const lateIds = new Set(finishedSummary?.out_of_order_steps || []);
    const times = {};
    for (const entry of sessionLog) {
      if (entry.step_status === "completed") {
        completedIds.add(entry.step_id);
        if (times[entry.step_id] === undefined) times[entry.step_id] = entry.extra?.video_time_s;
      } else if (entry.step_status === "skipped") {
        skippedIds.add(entry.step_id);
      }
      if (entry.alert_code === "OUT_OF_ORDER") lateIds.add(entry.step_id);
    }
    const currentIndex = plan.steps.findIndex((step) => step.id === status.current_step_id);
    return plan.steps.map((step, index) => {
      let state = "pending";
      if (lateIds.has(step.id)) state = "late";
      else if (completedIds.has(step.id)) state = "done";
      else if (skippedIds.has(step.id)) state = "skipped";
      else if (finishedSummary) state = "missed";
      else if (status.running && step.id === status.current_step_id && status.state !== "completed") state = "current";
      else if (status.running && currentIndex >= 0 && index < currentIndex) state = "done";
      return { ...step, state, time: times[step.id] };
    });
  }, [showingPreview, displayPlan.steps, finishedSummary, sessionLog, plan.steps, status.current_step_id, status.running, status.state]);

  const doneCount = stepsView.filter((step) => step.state === "done" || step.state === "late").length;
  const currentStepIndex = stepsView.findIndex((step) => step.state === "current");

  const result = useMemo(() => {
    if (!finishedSummary || showingPreview) return null;
    const total = finishedSummary.total_steps;
    const done = finishedSummary.completed_steps.length;
    const skipped = finishedSummary.skipped_steps || [];
    const missed = finishedSummary.missed_steps || [];
    const late = finishedSummary.out_of_order_steps || [];
    const clean = done === total && skipped.length === 0 && late.length === 0;
    const notes = [];
    if (skipped.length) notes.push(`${skipped.length} skipped`);
    if (late.length) notes.push(`${late.length} out of order`);
    if (missed.length) notes.push(`${missed.length} not reached`);
    if (!finishedSummary.source_finished) notes.push("stopped before the end of the video");
    return {
      tone: clean ? "ok" : "warn",
      title: clean ? "All steps completed in order" : `${done} of ${total} steps completed`,
      detail: notes.length ? capitalise(notes.join(" · ")) : null,
      done,
      total,
    };
  }, [finishedSummary, showingPreview]);

  const recognitionNote = useMemo(() => {
    if (!analysis?.recognized) return "";
    if (analysis.sampled_frames === 0) return "procedure selected manually";
    const match = analysis.scores.find((score) => score.activity_id === analysis.activity_id);
    return match ? `recognised from the video (${Math.round(match.score * 100)}% of frames matched)` : "recognised from the video";
  }, [analysis]);

  let statusText = "Open a video or connect a live source to begin.";
  let statusTone = "idle";
  if (!connected) {
    statusText = "Lost connection to the capture service. Retrying.";
    statusTone = "danger";
  } else if (analyzing) {
    statusText = selectedExperiment ? "Uploading the video" : "Uploading and recognising the experiment";
    statusTone = "busy";
  } else if (status.running && !status.has_frame) {
    statusText = status.message || "Starting";
    statusTone = "busy";
  } else if (status.running) {
    statusText = recognitionNote ? capitalise(recognitionNote) : "Monitoring the procedure";
    statusTone = "live";
  } else if (showingPreview) {
    statusText = "Selected. Open a video of this procedure to start monitoring.";
  } else if (result) {
    statusText = `${result.done} of ${result.total} steps completed${finishedSummary.source_finished ? "" : ", stopped early"}`;
    statusTone = result.tone;
  } else if (analysis && !analysis.recognized) {
    statusText = "The last video was not recognised";
    statusTone = "warn";
  }

  async function startCapture() {
    setBusy(true);
    setError("");
    try {
      await readJson("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source }),
      });
      setLiveOpen(false);
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

  async function selectActivity(activityId) {
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

  function chooseExperiment(activityId) {
    setSelectedExperiment(activityId);
    if (activityId && operationActivities.some((activity) => activity.id === activityId)) {
      selectActivity(activityId);
    }
  }

  async function analyzeFile(file) {
    if (!file) return;
    if (status.running) {
      setAnalysisError("Stop the running session before analysing another video.");
      return;
    }
    setAnalyzing(true);
    setAnalysisError("");
    setLocalAnalysis(null);
    setLiveOpen(false);
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
      const name = known?.name || data.scores.find((score) => score.activity_id === data.activity_id)?.name || data.activity_id;
      const verb = selectedExperiment ? "Selected" : "Recognised";
      if (!data.recognized) {
        say("Experiment not recognised.");
      } else if (known?.mode === "unavailable") {
        say(`${verb} ${name}, but it cannot be monitored yet.`);
      } else {
        say(`${verb} ${name}. Monitoring.`);
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

  const locked = analyzing || status.running;
  const sessionActive = status.running || Boolean(finishedSummary);
  const modeLabel = sessionActive && !showingPreview ? RECOGNITION_MODES[status.mode] : "";
  const recognisedActivity = analysis?.recognized
    ? analyzableActivities.find((activity) => activity.id === analysis.activity_id)
    : null;
  const alertEntries = logEntries.filter((entry) => entry.isAlert);
  const totalSteps = stepsView.length;
  const currentStep = currentStepIndex >= 0 ? stepsView[currentStepIndex] : null;

  const metrics = [
    {
      label: "Progress",
      value: totalSteps ? `${doneCount} / ${totalSteps}` : "–",
      progress: totalSteps ? doneCount / totalSteps : 0,
      tone: sessionActive && !showingPreview ? (totalSteps && doneCount === totalSteps ? "ok" : "neutral") : "muted",
    },
    {
      label: "Current step",
      value: currentStep ? `Step ${currentStepIndex + 1}` : result ? "Finished" : status.running ? "Complete" : "–",
      sub: currentStep ? capitalise(shortStep(currentStep.id)) : result ? result.title : status.running ? "Every step observed" : "Waiting for a video",
      tone: sessionActive && !showingPreview ? "neutral" : "muted",
    },
    {
      label: "Alerts",
      value: sessionActive && !showingPreview ? String(alertEntries.length) : "–",
      sub: alertEntries.length ? alertEntries[0].title : sessionActive ? "None raised" : "Skips and out-of-order steps",
      tone: !sessionActive || showingPreview ? "muted" : alertEntries.length ? "danger" : "ok",
    },
    {
      label: "Video time",
      value: sessionActive && !showingPreview ? formatVideoTime(status.video_time_s || 0) : "–",
      sub:
        sessionActive && status.realtime_factor != null
          ? `${status.realtime_factor.toFixed(2)}× real time · ${Number(status.fps || 0).toFixed(0)} fps`
          : "Not running",
      tone: sessionActive && !showingPreview ? "neutral" : "muted",
    },
  ];

  let now = null;
  if (analyzing) now = { label: "Starting", text: selectedExperiment ? "Uploading the video" : "Recognising the experiment" };
  else if (status.running && currentStep) now = { label: `Step ${currentStepIndex + 1} of ${totalSteps}`, text: currentStep.description };
  else if (status.running && status.has_frame) now = { label: "Complete", text: "Every step has been observed. Watching until the video ends." };
  else if (status.running) now = { label: "Starting", text: status.message || "Preparing the models" };
  else if (result) now = { label: "Finished", text: result.detail ? `${result.title}. ${result.detail}.` : `${result.title}.` };

  const detailRows = [
    ["Recognition", RECOGNITION_MODES[status.mode] || "Trained detector"],
    ["Inference device", status.device || hardware?.device || "auto"],
    ["GPU", hardware?.device_name || "None detected"],
    ["Frame encoder", status.encoder || "Not started"],
    ["Display rate", status.display_fps ? `${Number(status.display_fps).toFixed(1)} fps` : "Not started"],
    ["Behind video", status.lag_s != null ? `${Number(status.lag_s).toFixed(2)} s` : "Not started"],
    ["Source", baseName(status.source) || "None"],
    ["Event log", baseName(status.log_path) || "Not started"],
    ["Recording buffer", `${status.buffer_segment_count} segments`],
    ["Plan", displayPlan.id || "Loading"],
  ];

  const notScored = analysis && !analysis.recognized && !analyzing;

  return (
    <div
      className={`ops ${workspace === "studio" ? "is-studio" : ""}`}
      onDragOver={workspace === "operations" ? handleDragOver : undefined}
      onDragLeave={workspace === "operations" ? handleDragLeave : undefined}
      onDrop={workspace === "operations" ? handleDrop : undefined}
    >
      <AppBar workspace={workspace} onWorkspace={setWorkspace} connected={connected} gpuName={shortGpuName(hardware)} />
      {workspace === "studio" ? (
        <main className="app-shell">
          <TrainingStudio />
        </main>
      ) : (
        <main className="ops-main">
          <SessionHeader
            title={displayPlan.name || "Loading procedure"}
            version={displayPlan.version}
            modeLabel={modeLabel}
            statusText={statusText}
            statusTone={statusTone}
            activities={analyzableActivities}
            selectedExperiment={selectedExperiment}
            onSelectExperiment={chooseExperiment}
            running={status.running}
            locked={locked}
            onFile={analyzeFile}
            liveOpen={liveOpen}
            onToggleLive={() => setLiveOpen((open) => !open)}
            onStop={stopCapture}
            busy={busy}
            voiceOn={voiceOn}
            voiceHere={voiceHere}
            onToggleVoice={() => setVoiceOn((on) => !on)}
          />

          {liveOpen && !status.running && (
            <LiveSourceRow source={source} onSource={setSource} onStart={startCapture} disabled={busy || locked} />
          )}

          <div className="ops-notices">
            {activeAlert && (
              <Callout
                tone={activeAlert.tone === "danger" ? "danger" : "warn"}
                icon={activeAlert.icon}
                title={`${activeAlert.title} at ${activeAlert.time}`}
                actions={
                  <>
                    {status.running && (
                      <button className="ops-btn ops-btn--small" type="button" onClick={silenceAlerts}>
                        Silence for 60 s
                      </button>
                    )}
                    <button className="ops-btn ops-btn--small ops-btn--ghost" type="button" onClick={() => setDismissedAlert(latestAlert.key)}>
                      Dismiss
                    </button>
                  </>
                }
              >
                {activeAlert.detail}
              </Callout>
            )}
            {(analysisError || (connected && error)) && (
              <Callout tone="danger" title="Something went wrong">
                {analysisError || error}
              </Callout>
            )}
            {status.cpu_fallback && (
              <Callout tone="danger" title="Running on the CPU although an NVIDIA GPU is present">
                Start the dashboard with .venv\Scripts\python.exe (startup.bat does this) so detection uses the GPU.
              </Callout>
            )}
            {status.running && status.falling_behind && (
              <Callout tone="warn" title="Falling behind the video">
                Some frames are being skipped so analysis keeps pace with real time.
              </Callout>
            )}
            {notScored && (
              <Callout tone="warn" title="Experiment not recognised">
                {analysis.reason} Choose the procedure from the list and open the video again.
                {analysis.scores.length > 0 && (
                  <div className="ops-callout-scores">
                    {analysis.scores.map((score) => (
                      <div key={score.activity_id}>
                        <span>{score.name}</span>
                        <div className="ops-meter"><div style={{ width: `${Math.min(100, score.score * 100)}%` }} /></div>
                        <span>{Math.round(score.score * 100)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </Callout>
            )}
            {recognisedActivity?.mode === "unavailable" && !status.running && (
              <Callout tone="warn" title={`${recognisedActivity.name} cannot be monitored yet`}>
                It has no trained detector and no object descriptions. Add either one in the Training Studio.
              </Callout>
            )}
          </div>

          <MetricStrip metrics={metrics} />

          <div className="ops-grid">
            <VideoStage
              imageUrl={imageUrl}
              running={status.running}
              finished={Boolean(finishedSummary)}
              busyText={analyzing ? (selectedExperiment ? "Uploading the video" : "Recognising the experiment") : status.running ? status.message : ""}
              onFile={analyzeFile}
              onOpenLive={() => setLiveOpen(true)}
              locked={locked}
              now={now}
              showBoxes={showBoxes}
              onShowBoxes={changeShowBoxes}
            />
            <div className="ops-side">
              <ProcedurePanel
                steps={stepsView}
                currentStepId={status.current_step_id}
                confidence={status.confidence}
                doneCount={doneCount}
                result={result}
              />
            </div>
          </div>

          <div className="ops-grid ops-grid--start">
            <SessionLog entries={visibleLog} filter={logFilter} onFilter={setLogFilter} counts={logCounts} />
            <div className="ops-stack">
              {Object.keys(status.answers || {}).length > 0 && (
                <ModelAnswers
                  answers={status.answers}
                  answered={status.questions_answered}
                  modeLabel={RECOGNITION_MODES[status.mode] || "Model answers"}
                />
              )}
              <DetailsPanel rows={detailRows} timings={Object.entries(status.timings_ms || {})} />
            </div>
          </div>
        </main>
      )}
      <DropOverlay active={dragActive && workspace === "operations"} />
    </div>
  );
}

export default App;
