import { useCallback, useEffect, useState } from "react";

const ACTIVITY_KINDS = [
  ["experiment", "Science experiment"],
  ["maintenance", "Maintenance"],
  ["training", "Astronaut training"],
  ["exercise", "Exercise"],
  ["inspection", "Inspection"],
  ["other", "Other"],
];

const EMPTY_FORM = {
  id: "",
  name: "",
  kind: "experiment",
  description: "",
};

async function readJson(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function TrainingStudio() {
  const [activities, setActivities] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [selectedId, setSelectedId] = useState("");
  const [takes, setTakes] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [sessionId, setSessionId] = useState("session-1");
  const [busy, setBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try {
      setActivities(await readJson("/api/activities"));
    } catch (requestError) {
      setError(requestError.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!selectedId) {
      setTakes([]);
      setTimeline([]);
      return undefined;
    }
    let active = true;
    Promise.all([
      readJson(`/api/activities/${encodeURIComponent(selectedId)}/takes`),
      readJson(`/api/activities/${encodeURIComponent(selectedId)}/timeline`),
    ])
      .then(([nextTakes, nextTimeline]) => {
        if (active) {
          setTakes(nextTakes);
          setTimeline(nextTimeline);
        }
      })
      .catch((requestError) => setError(requestError.message));
    return () => {
      active = false;
    };
  }, [selectedId]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function createActivity(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const created = await readJson("/api/activities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setForm(EMPTY_FORM);
      setSelectedId(created.id);
      setMessage(`${created.name} created as a draft activity.`);
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadTake(file) {
    if (!file || !selectedId) return;
    setUploadBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`/api/activities/${encodeURIComponent(selectedId)}/takes`, {
        method: "POST",
        headers: {
          "Content-Type": file.type || "application/octet-stream",
          "X-Filename": file.name,
          "X-Recording-Session-ID": sessionId,
        },
        body: file,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Upload failed: ${response.status}`);
      setTakes((current) => [...current, data]);
      setMessage(`${file.name} uploaded and recorded as ${data.id}.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUploadBusy(false);
    }
  }

  async function uploadTimeline(file) {
    if (!file || !selectedId) return;
    setUploadBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`/api/activities/${encodeURIComponent(selectedId)}/timeline`, {
        method: "POST",
        headers: {
          "Content-Type": file.type || "application/octet-stream",
          "X-Filename": file.name,
        },
        body: file,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Timeline import failed: ${response.status}`);
      setTimeline(data.records);
      setMessage(`${data.records.length} timeline records imported and validated.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUploadBusy(false);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    uploadTake(event.dataTransfer.files[0]);
  }

  const selected = activities.find((activity) => activity.id === selectedId);

  return (
    <section className="studio-shell">
      <div className="studio-heading">
        <div>
          <span className="section-kicker">TRAINING STUDIO</span>
          <h2>Build an activity package</h2>
          <p>Define the approved activity first. Videos, ground truth, annotation, and training follow.</p>
        </div>
        <span className="studio-status">LOCAL WORKSPACE</span>
      </div>
      <div className="studio-grid">
        <article className="panel studio-card">
          <div className="panel-heading compact">
            <div><span className="section-kicker">STEP 01</span><h2>New activity</h2></div>
            <span className="step-count">DRAFT</span>
          </div>
          <form className="studio-form" onSubmit={createActivity}>
            <label>
              Activity ID
              <input name="id" value={form.id} onChange={updateField} placeholder="sample_handling" required />
            </label>
            <label>
              Display name
              <input name="name" value={form.name} onChange={updateField} placeholder="Sample Handling" required />
            </label>
            <label>
              Activity type
              <select name="kind" value={form.kind} onChange={updateField}>
                {ACTIVITY_KINDS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              Description
              <textarea name="description" value={form.description} onChange={updateField} placeholder="What is the astronaut expected to do?" rows="4" />
            </label>
            <button className="button button-primary" type="submit" disabled={busy}>
              {busy ? "Creating…" : "Create draft activity"}
            </button>
          </form>
          {message && <div className="success-banner">{message}</div>}
          {error && <div className="error-banner">{error}</div>}
        </article>
        <article className="panel studio-card">
          <div className="panel-heading compact">
            <div><span className="section-kicker">ACTIVITY REGISTRY</span><h2>Local packages</h2></div>
            <span className="event-count">{activities.length}</span>
          </div>
          {activities.length === 0 ? (
            <div className="studio-empty">Create the first activity to begin a procedure package.</div>
          ) : (
            <div className="activity-list">
              {activities.map((activity) => (
                <button
                  className={`activity-row ${selectedId === activity.id ? "selected" : ""}`}
                  key={activity.id}
                  onClick={() => setSelectedId(activity.id)}
                  type="button"
                >
                  <span><strong>{activity.name}</strong><small>{activity.id} · {activity.kind}</small></span>
                  <em>{activity.lifecycle}</em>
                </button>
              ))}
            </div>
          )}
          {selected && (
            <div className="studio-next-stack">
              <div className="upload-block">
                <div className="panel-heading compact">
                  <div><span className="section-kicker">STEP 02</span><h2>Training videos</h2></div>
                  <span className="step-count">{takes.length}</span>
                </div>
                <label className="session-field">
                  Recording session ID
                  <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} placeholder="session-2026-09-05-a" />
                </label>
                <label className={`upload-zone ${uploadBusy ? "busy" : ""}`} onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
                  <input type="file" accept="video/*,.mkv,.webm" onChange={(event) => uploadTake(event.target.files[0])} disabled={uploadBusy} />
                  <strong>{uploadBusy ? "Uploading and probing…" : "Drop a video here"}</strong>
                  <span>MP4, MOV, AVI, MKV, or WEBM · one recording session per take</span>
                </label>
                {takes.length > 0 && (
                  <div className="take-list">
                    {takes.map((take) => (
                      <div className="take-row" key={take.id}>
                        <span><strong>{take.id}</strong><small>{take.duration_s.toFixed(1)}s · {take.width}×{take.height} · {take.recording_session_id}</small></span>
                        <em>IMPORTED</em>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="activity-next">
                <span className="section-kicker">NEXT WORKFLOW</span>
                <strong>{selected.name}</strong>
                <p>Procedure builder, timestamp ground truth, assisted annotation, and training will attach to this package.</p>
              </div>
              <div className="upload-block">
                <div className="panel-heading compact">
                  <div><span className="section-kicker">STEP 03</span><h2>Ground truth timeline</h2></div>
                  <span className="step-count">{timeline.length}</span>
                </div>
                <p className="workflow-copy">Import the timestamps and actions you verified in the recording. The Studio checks every row against the uploaded video.</p>
                <div className="timeline-actions">
                  <a className="button button-quiet" href={`/api/activities/${encodeURIComponent(selectedId)}/timeline-template`}>Download CSV template</a>
                  <label className="button button-primary file-button">
                    Import CSV or Excel
                    <input type="file" accept=".csv,.xlsx,.xlsm" onChange={(event) => uploadTimeline(event.target.files[0])} disabled={uploadBusy} />
                  </label>
                </div>
                {timeline.length > 0 && (
                  <div className="ground-truth-list">
                    {timeline.slice(0, 6).map((record) => (
                      <div className="ground-truth-row" key={record.id}>
                        <span><strong>{record.expected_step_id}</strong><small>{record.start_s.toFixed(2)}s–{record.end_s.toFixed(2)}s · {record.observed_action}</small></span>
                        <em>{record.result}</em>
                      </div>
                    ))}
                    {timeline.length > 6 && <small className="more-label">+ {timeline.length - 6} more records</small>}
                  </div>
                )}
              </div>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}

export default TrainingStudio;
