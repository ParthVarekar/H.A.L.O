import { useEffect, useRef, useState } from "react";

import { SPEECH_LANGUAGES } from "./speech";

const ICONS = {
  check: <polyline points="20 6 9 17 4 12" />,
  x: (
    <>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </>
  ),
  alert: (
    <>
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </>
  ),
  upload: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </>
  ),
  camera: (
    <>
      <rect x="2" y="6" width="14" height="12" rx="2" />
      <path d="m16 10 6-4v12l-6-4" />
    </>
  ),
  stop: <rect x="6" y="6" width="12" height="12" rx="1.5" />,
  play: <polygon points="7 4 20 12 7 20 7 4" />,
  volume: (
    <>
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7" />
      <path d="M19 5a10 10 0 0 1 0 14" />
    </>
  ),
  mute: (
    <>
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <line x1="22" y1="9" x2="16" y2="15" />
      <line x1="16" y1="9" x2="22" y2="15" />
    </>
  ),
  skip: (
    <>
      <polygon points="5 4 15 12 5 20 5 4" />
      <line x1="19" y1="5" x2="19" y2="19" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15 14" />
    </>
  ),
  chevron: <polyline points="6 9 12 15 18 9" />,
  chip: (
    <>
      <rect x="5" y="5" width="14" height="14" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <line x1="9" y1="2" x2="9" y2="5" />
      <line x1="15" y1="2" x2="15" y2="5" />
      <line x1="9" y1="19" x2="9" y2="22" />
      <line x1="15" y1="19" x2="15" y2="22" />
    </>
  ),
  box: (
    <>
      <path d="M4 8V5a1 1 0 0 1 1-1h3" />
      <path d="M16 4h3a1 1 0 0 1 1 1v3" />
      <path d="M20 16v3a1 1 0 0 1-1 1h-3" />
      <path d="M8 20H5a1 1 0 0 1-1-1v-3" />
    </>
  ),
  dot: <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" />,
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <line x1="12" y1="2" x2="12" y2="4" />
      <line x1="12" y1="20" x2="12" y2="22" />
      <line x1="4.9" y1="4.9" x2="6.3" y2="6.3" />
      <line x1="17.7" y1="17.7" x2="19.1" y2="19.1" />
      <line x1="2" y1="12" x2="4" y2="12" />
      <line x1="20" y1="12" x2="22" y2="12" />
      <line x1="4.9" y1="19.1" x2="6.3" y2="17.7" />
      <line x1="17.7" y1="6.3" x2="19.1" y2="4.9" />
    </>
  ),
  moon: <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />,
  shield: (
    <>
      <path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z" />
      <polyline points="8.5 12 11 14.5 15.5 10" />
    </>
  ),
  cast: (
    <>
      <path d="M2 8V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6" />
      <path d="M2 12a9 9 0 0 1 8 8" />
      <path d="M2 16a5 5 0 0 1 4 4" />
      <line x1="2" y1="20" x2="2.01" y2="20" />
    </>
  ),
  download: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </>
  ),
};

export function Icon({ name, size = 16 }) {
  return (
    <svg
      className="ops-icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  );
}

export function formatVideoTime(seconds) {
  if (typeof seconds !== "number" || Number.isNaN(seconds)) return "";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds - minutes * 60;
  return `${minutes}:${rest.toFixed(1).padStart(4, "0")}`;
}

export function BrandMark({ size = 28 }) {
  return (
    <svg className="ops-brand-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="ops-brand-tile" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#18253c" />
          <stop offset="1" stopColor="#0e131b" />
        </linearGradient>
      </defs>
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="url(#ops-brand-tile)" stroke="#2c3a52" />
      <path d="M25.29 14.03A9.5 9.5 0 1 1 17.98 6.71" fill="none" stroke="#5b9dff" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="22.72" cy="9.28" r="2.1" fill="#eef2f7" />
      <polyline points="11.4 16.4 14.4 19.3 19.5 13.9" fill="none" stroke="#eef2f7" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AppBar({ workspace, onWorkspace, connected, gpuName, theme, onToggleTheme }) {
  const tabs = [
    ["operations", "Operations"],
    ["studio", "Training Studio"],
  ];
  return (
    <header className="ops-appbar">
      <div className="ops-appbar-inner">
        <div className="ops-brand">
          <BrandMark />
          <div className="ops-brand-text">
            <strong>H.A.L.O.</strong>
            <span>Human Activity Logging in Orbit</span>
          </div>
        </div>
        <nav className="ops-segmented" aria-label="Workspace">
          {tabs.map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-current={workspace === id ? "page" : undefined}
              onClick={() => onWorkspace(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="ops-appbar-status">
          {gpuName && (
            <span className="ops-pill">
              <Icon name="chip" size={13} />
              {gpuName}
            </span>
          )}
          <span className={`ops-pill ops-connection ${connected ? "is-up" : "is-down"}`}>
            <i aria-hidden="true" />
            {connected ? "Connected" : "Reconnecting"}
          </span>
          <button
            type="button"
            className="ops-pill ops-theme-toggle"
            onClick={onToggleTheme}
            title={theme === "light" ? "Switch to the dark theme" : "Switch to the light theme"}
          >
            <Icon name={theme === "light" ? "moon" : "sun"} size={13} />
            <span className="ops-sr">{theme === "light" ? "Switch to the dark theme" : "Switch to the light theme"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}

export function FileButton({ children, onFile, disabled, variant = "primary" }) {
  return (
    <label className={`ops-btn ops-btn--${variant} ops-file-button ${disabled ? "is-disabled" : ""}`}>
      <Icon name="upload" size={15} />
      {children}
      <input
        type="file"
        accept="video/*"
        disabled={disabled}
        onChange={(event) => {
          onFile(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
    </label>
  );
}

const MODE_SUFFIX = { trained: "", described: " (described)", unavailable: " (not set up)" };
const STATUS_LABEL = { live: "Live", busy: "Starting", ok: "Complete", warn: "Needs review", danger: "Offline", idle: "Standby" };

export function SessionHeader({
  title,
  version,
  modeLabel,
  statusText,
  statusTone,
  activities,
  selectedExperiment,
  onSelectExperiment,
  running,
  locked,
  onFile,
  liveOpen,
  onToggleLive,
  onStop,
  busy,
  voiceOn,
  voiceHere,
  onToggleVoice,
  voiceLang,
  onVoiceLang,
}) {
  return (
    <section className="ops-hero" aria-label="Session">
      <div className="ops-hero-title">
        <span className="ops-eyebrow">Procedure</span>
        <h1>{title}</h1>
        <div className="ops-hero-meta">
          <span className={`ops-status is-${statusTone}`}>
            <i aria-hidden="true" />
            {STATUS_LABEL[statusTone] || "Standby"}
          </span>
          <span className="ops-hero-text">{statusText}</span>
          {(version || modeLabel) && <span className="ops-hero-sep" aria-hidden="true" />}
          {modeLabel && <span className="ops-tag">{modeLabel}</span>}
          {version && <span className="ops-tag ops-tag--quiet">v{version}</span>}
        </div>
      </div>
      <div className="ops-toolbar">
        <label className="ops-select-wrap">
          <span className="ops-sr">Procedure</span>
          <select
            className="ops-select"
            value={selectedExperiment}
            onChange={(event) => onSelectExperiment(event.target.value)}
            disabled={locked}
          >
            <option value="">Detect procedure from video</option>
            {activities.map((activity) => (
              <option key={activity.id} value={activity.id} disabled={activity.mode === "unavailable"}>
                {activity.name}
                {MODE_SUFFIX[activity.mode] ?? ""}
              </option>
            ))}
          </select>
          <Icon name="chevron" size={14} />
        </label>
        {running ? (
          <button className="ops-btn ops-btn--danger" type="button" onClick={onStop} disabled={busy}>
            <Icon name="stop" size={13} />
            Stop
          </button>
        ) : (
          <>
            <button className="ops-btn" type="button" aria-expanded={liveOpen} onClick={onToggleLive} disabled={locked}>
              <Icon name="camera" size={15} />
              Live source
            </button>
            <FileButton onFile={onFile} disabled={locked}>
              Open video
            </FileButton>
          </>
        )}
        <button
          className="ops-btn ops-btn--icon"
          type="button"
          aria-pressed={voiceOn}
          onClick={onToggleVoice}
          title={
            !voiceOn
              ? "Voice alerts are off"
              : voiceHere
                ? "Voice alerts on"
                : "Voice alerts are playing in another open window. Click anywhere here to move them to this one."
          }
        >
          <Icon name={voiceOn ? "volume" : "mute"} size={16} />
          {voiceOn && !voiceHere && <i className="ops-voice-away" aria-hidden="true" />}
          <span className="ops-sr">{voiceOn ? "Turn voice alerts off" : "Turn voice alerts on"}</span>
        </button>
        <div className="ops-lang" role="group" aria-label="Announcement language">
          {SPEECH_LANGUAGES.map(([id, short, full]) => (
            <button
              key={id}
              type="button"
              lang={id}
              aria-pressed={voiceLang === id}
              title={`Announce in ${full}`}
              onClick={() => onVoiceLang(id)}
            >
              {short}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LiveSourceRow({ source, onSource, onStart, disabled }) {
  return (
    <form
      className="ops-card ops-live-row"
      onSubmit={(event) => {
        event.preventDefault();
        onStart();
      }}
    >
      <label className="ops-live-field">
        <span>Live source</span>
        <input
          className="ops-input"
          value={source}
          onChange={(event) => onSource(event.target.value)}
          placeholder="Camera index (0), RTSP URL, or a video file path"
          spellCheck="false"
        />
      </label>
      <button className="ops-btn ops-btn--primary" type="submit" disabled={disabled || !source.trim()}>
        <Icon name="play" size={12} />
        Start monitoring
      </button>
    </form>
  );
}

export function Callout({ tone = "info", icon, title, children, actions }) {
  return (
    <div className={`ops-callout is-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <span className="ops-callout-icon">
        <Icon name={icon || (tone === "ok" ? "check" : "alert")} size={15} />
      </span>
      <div className="ops-callout-body">
        {title && <strong>{title}</strong>}
        {children && <div className="ops-callout-text">{children}</div>}
      </div>
      {actions && <div className="ops-callout-actions">{actions}</div>}
    </div>
  );
}

export function MetricStrip({ metrics }) {
  return (
    <section className="ops-metrics" aria-label="Session summary">
      {metrics.map((metric) => (
        <div key={metric.label} className={`ops-card ops-metric is-${metric.tone || "neutral"}`}>
          <span className="ops-metric-label">{metric.label}</span>
          <strong className="ops-metric-value">{metric.value}</strong>
          {metric.progress != null ? (
            <div className="ops-metric-bar" aria-hidden="true">
              <div style={{ width: `${Math.min(100, Math.max(0, metric.progress * 100))}%` }} />
            </div>
          ) : (
            <span className="ops-metric-sub">{metric.sub}</span>
          )}
        </div>
      ))}
    </section>
  );
}

export function Switch({ checked, onChange, label, disabled }) {
  return (
    <label className={`ops-switch ${disabled ? "is-disabled" : ""}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      <span aria-hidden="true" />
      {label}
    </label>
  );
}

export function VideoStage({ imageUrl, running, finished, busyText, onFile, onOpenLive, locked, now, showBoxes, onShowBoxes, streaming }) {
  let badge = null;
  if (running && imageUrl) badge = <span className="ops-stage-badge is-live"><i />Live analysis</span>;
  else if (finished && imageUrl) badge = <span className="ops-stage-badge">Session ended</span>;
  return (
    <section className="ops-card ops-stage-card" aria-label="Video">
      <div className="ops-stage">
        {imageUrl ? (
          <img src={imageUrl} alt="Analysed procedure video" />
        ) : busyText ? (
          <div className="ops-stage-empty">
            <span className="ops-spinner" aria-hidden="true" />
            <p className="ops-stage-busy">{busyText}</p>
          </div>
        ) : (
          <div className="ops-stage-empty">
            <div className="ops-dropzone">
              <div className="ops-empty-icon"><Icon name="upload" size={20} /></div>
              <h2>Drop an experiment video</h2>
              <p>The procedure is recognised from the video, then followed step by step with spoken alerts.</p>
              <div className="ops-empty-actions">
                <FileButton onFile={onFile} disabled={locked}>Choose video</FileButton>
                <button className="ops-btn ops-btn--ghost" type="button" onClick={onOpenLive} disabled={locked}>
                  <Icon name="camera" size={15} />
                  Use a live camera
                </button>
              </div>
            </div>
          </div>
        )}
        {badge}
      </div>
      <div className="ops-stage-footer">
        <div className="ops-now">
          {now ? (
            <>
              <span className="ops-now-label">{now.label}</span>
              <span className="ops-now-text">{now.text}</span>
              {now.next && <span className="ops-now-next">Next: {now.next}</span>}
            </>
          ) : (
            <span className="ops-now-text is-muted">No active session</span>
          )}
        </div>
        <div className="ops-stage-controls">
          {streaming && (
            <span className="ops-stream-pill" title={`Streaming to ${streaming}`}>
              <i aria-hidden="true" />
              {streaming}
            </span>
          )}
          <Switch checked={showBoxes} onChange={onShowBoxes} label="Detection boxes" />
        </div>
      </div>
    </section>
  );
}

const STEP_META = {
  late: "Out of order",
  skipped: "Skipped",
  missed: "Not reached",
  current: "Now",
  pending: "",
};

function StepMarker({ state, number }) {
  if (state === "done") return <Icon name="check" size={12} />;
  if (state === "late") return <Icon name="clock" size={12} />;
  if (state === "skipped") return <Icon name="skip" size={10} />;
  if (state === "missed") return <Icon name="x" size={12} />;
  return number;
}

export function ProcedurePanel({ steps, currentStepId, confidence, doneCount, result }) {
  const currentRef = useRef(null);
  useEffect(() => {
    currentRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [currentStepId]);
  const percent = steps.length ? Math.round((doneCount / steps.length) * 100) : 0;
  return (
    <section className="ops-card ops-procedure" aria-label="Procedure steps">
      <div className="ops-card-head">
        <h2>Steps</h2>
        <span className="ops-count">
          {doneCount}/{steps.length} · {percent}%
        </span>
      </div>
      {result && (
        <div className="ops-procedure-result">
          <Callout tone={result.tone} title={result.title}>{result.detail}</Callout>
        </div>
      )}
      <ol className="ops-steps">
        {steps.map((step, index) => {
          const isCurrent = step.state === "current";
          return (
            <li
              key={step.id}
              ref={isCurrent ? currentRef : undefined}
              className={`ops-step is-${step.state}`}
              aria-current={isCurrent ? "step" : undefined}
              title={step.evidence?.length ? `Evidence: ${step.evidence.join(", ").replaceAll("_", " ")}` : undefined}
            >
              <span className="ops-step-marker">
                <StepMarker state={step.state} number={index + 1} />
              </span>
              <div className="ops-step-body">
                <p className="ops-step-title">{step.description}</p>
                {isCurrent && (
                  <div className="ops-meter-block">
                    <div className="ops-meter">
                      <div style={{ width: `${Math.min(100, Math.max(0, confidence * 100))}%` }} />
                    </div>
                    <span>{Math.round(confidence * 100)}% evidence</span>
                  </div>
                )}
              </div>
              <span className="ops-step-meta">
                {step.state === "done" ? formatVideoTime(step.time) || "Done" : STEP_META[step.state]}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

const LOG_FILTERS = [
  ["all", "All"],
  ["steps", "Steps"],
  ["alerts", "Alerts"],
  ["evidence", "Evidence"],
];

export function SessionLog({ entries, filter, onFilter, counts }) {
  return (
    <section className="ops-card ops-log" aria-label="Session log">
      <div className="ops-card-head">
        <h2>Session log</h2>
        <div className="ops-filter" role="tablist" aria-label="Filter the session log">
          {LOG_FILTERS.map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={filter === id}
              onClick={() => onFilter(id)}
            >
              {label}
              {counts[id] > 0 && <span>{counts[id]}</span>}
            </button>
          ))}
        </div>
      </div>
      {entries.length === 0 ? (
        <p className="ops-empty-note">
          {filter === "alerts" ? "No alerts in this session." : "Completed steps, skipped steps and alerts appear here while a procedure is monitored."}
        </p>
      ) : (
        <ol className="ops-log-list">
          {entries.map((entry) => (
            <li key={entry.key} className={`ops-log-row is-${entry.tone}`}>
              <time>{entry.time}</time>
              <span className="ops-log-icon"><Icon name={entry.icon} size={12} /></span>
              <div className="ops-log-text">
                <strong>{entry.title}</strong>
                <span>{entry.detail}</span>
                {entry.isUpdate && entry.technical && <code>{entry.technical}</code>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

const VERDICT_LABEL = { yes: "Yes", no: "No", unsure: "Unsure" };

export function ModelAnswers({ answers, answered, modeLabel }) {
  const rows = Object.entries(answers);
  return (
    <section className="ops-card ops-answers" aria-label="Model answers">
      <div className="ops-card-head">
        <h2>What the model sees</h2>
        <span className="ops-count">{answered} answers</span>
      </div>
      <ul className="ops-answer-list">
        {rows.map(([question, answer]) => (
          <li key={question} className={`ops-answer is-${answer.verdict}`}>
            <p>{question}</p>
            <div className="ops-answer-row">
              <div className="ops-answer-track">
                <div style={{ width: `${Math.round(answer.p * 100)}%` }} />
              </div>
              <span className="ops-answer-value">{Math.round(answer.p * 100)}%</span>
              <span className="ops-verdict">{VERDICT_LABEL[answer.verdict] || answer.verdict}</span>
            </div>
          </li>
        ))}
      </ul>
      <p className="ops-card-note">{modeLabel}. Answers between 40% and 60% count as unsure and complete nothing.</p>
    </section>
  );
}

function formatBytes(bytes) {
  if (bytes == null) return "–";
  if (bytes < 10_000) return `${bytes.toLocaleString()} bytes`;
  if (bytes < 1_000_000) return `${(bytes / 1000).toFixed(1)} KB`;
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}

export function EvidencePanel({ downlink }) {
  if (!downlink || downlink.error) return null;
  const verified = Boolean(downlink.verified);
  const rows = [
    ["Report size", formatBytes(downlink.bytes)],
    ["Video size", formatBytes(downlink.source_bytes)],
    ["Smaller than video", downlink.ratio ? `${downlink.ratio.toLocaleString()}×` : "–"],
    ["Events signed", String(downlink.events)],
    ["Station key", downlink.key_id],
    ["Chain ends in", `${String(downlink.final_hash).slice(0, 16)}…`],
  ];
  return (
    <section className="ops-card ops-evidence" aria-label="Signed session report">
      <div className="ops-card-head">
        <h2>Signed session report</h2>
        <span className={`ops-status ${verified ? "is-ok" : "is-danger"}`}>
          <Icon name="shield" size={12} />
          {verified ? "Verified" : "Not verified"}
        </span>
      </div>
      <dl className="ops-details-grid">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className={label === "Station key" || label === "Chain ends in" ? "is-mono" : undefined}>{value}</dd>
          </div>
        ))}
      </dl>
      <div className="ops-evidence-actions">
        <a className="ops-btn ops-btn--small" href="/api/downlink" download>
          <Icon name="download" size={13} />
          Report
        </a>
        <a className="ops-btn ops-btn--small ops-btn--ghost" href="/api/session-log" download>
          <Icon name="download" size={13} />
          Signed log
        </a>
      </div>
      <p className="ops-card-note">
        Every event is SHA-256 chained and Ed25519-signed. Anyone can check a copy with <code>python -m halo verify-log</code>.
      </p>
    </section>
  );
}

export function StreamPanel({ stream, onApply, busy }) {
  const [host, setHost] = useState(stream?.host || "");
  const [port, setPort] = useState(String(stream?.port || 5000));
  const enabled = Boolean(stream?.enabled);
  useEffect(() => {
    if (!stream) return;
    setHost((current) => current || stream.host);
    setPort((current) => current || String(stream.port));
  }, [stream]);
  if (!stream) return null;
  const submit = (event) => {
    event.preventDefault();
    if (enabled) onApply({ enabled: false });
    else onApply({ enabled: true, host: host.trim(), port: Number(port) });
  };
  return (
    <section className="ops-card ops-stream" aria-label="Stream to another computer">
      <div className="ops-card-head">
        <h2>Stream to IP</h2>
        {enabled && (
          <span className="ops-status is-live">
            <i aria-hidden="true" />
            Streaming
          </span>
        )}
      </div>
      <form className="ops-stream-form" onSubmit={submit}>
        <label className="ops-live-field">
          <span>IP address</span>
          <input
            className="ops-input"
            value={host}
            onChange={(event) => setHost(event.target.value)}
            placeholder="192.168.1.20"
            spellCheck="false"
            disabled={enabled}
          />
        </label>
        <label className="ops-live-field ops-stream-port">
          <span>Port</span>
          <input
            className="ops-input"
            value={port}
            onChange={(event) => setPort(event.target.value.replace(/\D/g, ""))}
            inputMode="numeric"
            disabled={enabled}
          />
        </label>
        <button
          className={`ops-btn ${enabled ? "ops-btn--danger" : "ops-btn--primary"}`}
          type="submit"
          disabled={busy || (!enabled && (!host.trim() || !port))}
        >
          <Icon name={enabled ? "stop" : "cast"} size={13} />
          {enabled ? "Stop" : "Start"}
        </button>
      </form>
      <p className="ops-card-note">
        {enabled
          ? `Sending to ${stream.target} · ${stream.frames_sent.toLocaleString()} frames${stream.codec ? ` · ${stream.codec}` : ""}. On that computer, open ${stream.player_url} in VLC.`
          : "Sends the annotated video live as MPEG-TS over UDP. The rolling recording on this computer continues."}
      </p>
      {stream.error && <p className="ops-card-note is-danger">{stream.error}</p>}
    </section>
  );
}

export function DetailsPanel({ rows, timings }) {
  return (
    <details className="ops-card ops-details">
      <summary>
        <h2>System details</h2>
        <Icon name="chevron" size={16} />
      </summary>
      <dl className="ops-details-grid">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd title={typeof value === "string" ? value : undefined}>{value}</dd>
          </div>
        ))}
      </dl>
      {timings.length > 0 && (
        <div className="ops-timings">
          <span className="ops-timings-label">Per-frame time</span>
          <dl className="ops-details-grid ops-details-grid--compact">
            {timings.map(([stage, value]) => (
              <div key={stage}>
                <dt>{stage}</dt>
                <dd>{Number(value).toFixed(1)} ms</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </details>
  );
}

export function DropOverlay({ active }) {
  if (!active) return null;
  return (
    <div className="ops-drop-overlay" aria-hidden="true">
      <div>
        <span className="ops-empty-icon"><Icon name="upload" size={22} /></span>
        <strong>Drop to analyse this video</strong>
      </div>
    </div>
  );
}
