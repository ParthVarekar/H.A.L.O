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

const EMPTY_STEP = {
  id: "step_1",
  description: "",
  kind: "actor_visible",
  object: "",
  label: "",
  state: "",
  min_frames: 5,
  timeout_s: 60,
  expected_duration_s: 5,
  next: "",
};

const EMPTY_PROCEDURE = {
  name: "",
  description: "",
  objects: [],
  steps: [],
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
  const [dataset, setDataset] = useState(null);
  const [datasetJobs, setDatasetJobs] = useState([]);
  const [trainingJobs, setTrainingJobs] = useState([]);
  const [evaluationJobs, setEvaluationJobs] = useState([]);
  const [releases, setReleases] = useState([]);
  const [reviewer, setReviewer] = useState("");
  const [quality, setQuality] = useState(null);
  const [evaluationReport, setEvaluationReport] = useState(null);
  const [selectedTakeId, setSelectedTakeId] = useState("");
  const [keyframes, setKeyframes] = useState([]);
  const [annotations, setAnnotations] = useState([]);
  const [activeFrame, setActiveFrame] = useState(null);
  const [frameEvery, setFrameEvery] = useState(30);
  const [annotationLabel, setAnnotationLabel] = useState("");
  const [draftBox, setDraftBox] = useState(null);
  const [dragStart, setDragStart] = useState(null);
  const [hardware, setHardware] = useState(null);
  const [procedure, setProcedure] = useState(EMPTY_PROCEDURE);
  const [procedureExists, setProcedureExists] = useState(false);
  const [sessionId, setSessionId] = useState("session-1");
  const [busy, setBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [procedureBusy, setProcedureBusy] = useState(false);
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
    readJson("/api/hardware").then(setHardware).catch((requestError) => setError(requestError.message));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setTakes([]);
      setTimeline([]);
      setDataset(null);
      setDatasetJobs([]);
      setTrainingJobs([]);
      setEvaluationJobs([]);
      setReleases([]);
      setReviewer("");
      setQuality(null);
      setEvaluationReport(null);
      setSelectedTakeId("");
      setKeyframes([]);
      setAnnotations([]);
      setActiveFrame(null);
      setDraftBox(null);
      setProcedure(EMPTY_PROCEDURE);
      setProcedureExists(false);
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
          setSelectedTakeId((current) => current || nextTakes[0]?.id || "");
        }
      })
      .catch((requestError) => setError(requestError.message));
    readJson(`/api/activities/${encodeURIComponent(selectedId)}/plan`)
      .then((plan) => {
        if (!active) return;
        setProcedureExists(true);
        setProcedure({
          name: plan.name,
          description: plan.description || "",
          objects: (plan.objects || []).map((object) => ({
            id: object.id,
            classes: object.classes.join(", "),
            colors_any: (object.colors_any || []).join(", "),
          })),
          steps: (plan.steps || []).map((step) => {
            const rule = step.evidence[0] || {};
            return {
              ...EMPTY_STEP,
              id: step.id,
              description: step.description,
              kind: rule.kind || "actor_visible",
              object: rule.object || "",
              label: rule.label || "",
              state: rule.state || "",
              min_frames: rule.min_frames || 1,
              timeout_s: step.timeout_s || 60,
              expected_duration_s: step.expected_duration_s || 5,
              next: (step.next || []).join(", "),
            };
          }),
        });
      })
      .catch((requestError) => {
        if (requestError.message.includes("404")) {
          setProcedureExists(false);
          const activity = activities.find((item) => item.id === selectedId);
          setProcedure({ ...EMPTY_PROCEDURE, name: activity?.name || "" });
        } else {
          setError(requestError.message);
        }
      });
    return () => {
      active = false;
    };
  }, [selectedId, activities]);

  useEffect(() => {
    if (!selectedId || !selectedTakeId) {
      setKeyframes([]);
      setAnnotations([]);
      setActiveFrame(null);
      return undefined;
    }
    let active = true;
    const activityPath = `/api/activities/${encodeURIComponent(selectedId)}`;
    Promise.all([
      readJson(`${activityPath}/keyframes?take_id=${encodeURIComponent(selectedTakeId)}&every_frames=${frameEvery}&limit=120`),
      readJson(`${activityPath}/annotations?take_id=${encodeURIComponent(selectedTakeId)}`),
    ])
      .then(([nextFrames, nextAnnotations]) => {
        if (!active) return;
        setKeyframes(nextFrames);
        setAnnotations(nextAnnotations);
        setActiveFrame((current) => nextFrames.find((frame) => frame.frame_id === current?.frame_id) || nextFrames[0] || null);
        setDraftBox(null);
      })
      .catch((requestError) => setError(requestError.message));
    return () => {
      active = false;
    };
  }, [selectedId, selectedTakeId, frameEvery]);

  useEffect(() => {
    if (!selectedId) return undefined;
    let active = true;
    const loadJobs = async () => {
      const activityPath = `/api/activities/${encodeURIComponent(selectedId)}`;
      const [nextDataset, nextDatasetJobs, nextTrainingJobs, nextEvaluationJobs, nextReleases] = await Promise.all([
        fetch(`${activityPath}/dataset`).then((response) => response.ok ? response.json() : null),
        readJson(`${activityPath}/dataset/jobs`),
        readJson(`${activityPath}/training/jobs`),
        readJson(`${activityPath}/evaluation/jobs`),
        readJson(`${activityPath}/releases`),
      ]);
      if (!active) return;
      setDataset(nextDataset);
      setDatasetJobs(nextDatasetJobs);
      setTrainingJobs(nextTrainingJobs);
      setEvaluationJobs(nextEvaluationJobs);
      setReleases(nextReleases);
      const latestEvaluation = nextEvaluationJobs[nextEvaluationJobs.length - 1];
      if (latestEvaluation?.report_id) {
        readJson(`${activityPath}/evaluation/reports/${encodeURIComponent(latestEvaluation.report_id)}`)
          .then(setEvaluationReport)
          .catch(() => undefined);
      }
    };
    loadJobs().catch((requestError) => setError(requestError.message));
    const timer = window.setInterval(() => loadJobs().catch((requestError) => setError(requestError.message)), 1000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) return undefined;
    const activityPath = `/api/activities/${encodeURIComponent(selectedId)}`;
    fetch(`${activityPath}/dataset/quality`)
      .then((response) => response.ok ? response.json() : null)
      .then(setQuality)
      .catch(() => undefined);
    return undefined;
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

  function addObject() {
    setProcedure((current) => ({
      ...current,
      objects: [
        ...current.objects,
        { id: `object_${current.objects.length + 1}`, classes: "", colors_any: "" },
      ],
    }));
  }

  function updateObject(index, field, value) {
    setProcedure((current) => ({
      ...current,
      objects: current.objects.map((object, objectIndex) =>
        objectIndex === index ? { ...object, [field]: value } : object
      ),
    }));
  }

  function removeObject(index) {
    setProcedure((current) => ({
      ...current,
      objects: current.objects.filter((_, objectIndex) => objectIndex !== index),
    }));
  }

  function addStep() {
    setProcedure((current) => ({
      ...current,
      steps: [
        ...current.steps,
        { ...EMPTY_STEP, id: `step_${current.steps.length + 1}` },
      ],
    }));
  }

  function updateStep(index, field, value) {
    setProcedure((current) => ({
      ...current,
      steps: current.steps.map((step, stepIndex) =>
        stepIndex === index ? { ...step, [field]: value } : step
      ),
    }));
  }

  function removeStep(index) {
    setProcedure((current) => {
      const removedId = current.steps[index]?.id;
      return {
        ...current,
        steps: current.steps
          .filter((_, stepIndex) => stepIndex !== index)
          .map((step) => ({
            ...step,
            next: splitValues(step.next).filter((stepId) => stepId !== removedId).join(", "),
          })),
      };
    });
  }

  function splitValues(value) {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
  }

  async function saveProcedure() {
    if (!selectedId || procedure.steps.length === 0) {
      setError("Add at least one procedure step before saving.");
      return;
    }
    setProcedureBusy(true);
    setError("");
    setMessage("");
    try {
      const plan = {
        id: selectedId,
        name: procedure.name || selected.name,
        version: "0.1.0",
        author: "local",
        description: procedure.description,
        camera: { source: 0, fps: 30, resolution: [1280, 720] },
        fiducial: { type: "none" },
        objects: procedure.objects.map((object) => ({
          id: object.id,
          classes: splitValues(object.classes),
          colors_any: splitValues(object.colors_any),
        })),
        regions: [],
        region_geometries: {},
        steps: procedure.steps.map((step) => ({
          id: step.id,
          description: step.description,
          evidence: [{
            kind: step.kind,
            ...(step.object ? { object: step.object } : {}),
            ...(step.label ? { label: step.label } : {}),
            ...(step.state ? { state: step.state } : {}),
            min_frames: Number(step.min_frames) || 1,
          }],
          next: splitValues(step.next),
          timeout_s: Number(step.timeout_s) || 60,
          expected_duration_s: Number(step.expected_duration_s) || 5,
        })),
        alert_policy: {
          skip_confidence_threshold: 0.85,
          skip_persistence_frames: 5,
          rate_limit_s: 5,
          silence_window_s: 60,
          pause_tolerance_s: 30,
        },
      };
      await readJson(`/api/activities/${encodeURIComponent(selectedId)}/plan`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(plan),
      });
      setProcedureExists(true);
      setMessage("Procedure validated and saved to the activity package.");
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  async function prepareDataset() {
    if (!selectedId) return;
    setProcedureBusy(true);
    setError("");
    setMessage("");
    try {
      await readJson(`/api/activities/${encodeURIComponent(selectedId)}/dataset/prepare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_every: 5, val_ratio: 0.2, test_ratio: 0.1 }),
      });
      setMessage("Dataset preparation started. The status will update automatically.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  async function startTraining() {
    if (!selectedId || !dataset) return;
    setProcedureBusy(true);
    setError("");
    setMessage("");
    try {
      await readJson(`/api/activities/${encodeURIComponent(selectedId)}/training`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset: "laptop_safe", device: "auto" }),
      });
      setMessage("CUDA-aware training started with the laptop-safe preset.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  function pointFromEvent(event) {
    if (!activeFrame) return null;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(activeFrame.width, (event.clientX - bounds.left) * activeFrame.width / bounds.width));
    const y = Math.max(0, Math.min(activeFrame.height, (event.clientY - bounds.top) * activeFrame.height / bounds.height));
    return { x, y };
  }

  function boxFromPoints(first, second) {
    if (!first || !second) return null;
    return {
      x1: Math.min(first.x, second.x),
      y1: Math.min(first.y, second.y),
      x2: Math.max(first.x, second.x),
      y2: Math.max(first.y, second.y),
    };
  }

  function handleFramePointerDown(event) {
    event.currentTarget.focus();
    const point = pointFromEvent(event);
    if (!point) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragStart(point);
    setDraftBox(null);
  }

  function handleFramePointerMove(event) {
    if (!dragStart) return;
    setDraftBox(boxFromPoints(dragStart, pointFromEvent(event)));
  }

  function handleFramePointerUp(event) {
    if (!dragStart) return;
    setDraftBox(boxFromPoints(dragStart, pointFromEvent(event)));
    setDragStart(null);
  }

  async function saveFrameAnnotation() {
    if (!selectedId || !selectedTakeId || !activeFrame || !draftBox) return;
    setProcedureBusy(true);
    setError("");
    try {
      const saved = await readJson(`/api/activities/${encodeURIComponent(selectedId)}/annotations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: `annotation-${Date.now()}`,
          take_id: selectedTakeId,
          frame_id: activeFrame.frame_id,
          time_s: activeFrame.time_s,
          kind: "object_box",
          label: annotationLabel || detectorClasses[0] || "object",
          bbox: draftBox,
          source: "human",
        }),
      });
      setAnnotations((current) => [...current.filter((item) => item.id !== saved.id), saved]);
      setDraftBox(null);
      setDragStart(null);
      const frameIndex = keyframes.findIndex((frame) => frame.frame_id === activeFrame.frame_id);
      const nextFrame = keyframes[frameIndex + 1];
      if (nextFrame) {
        setActiveFrame(nextFrame);
        setMessage(`Saved ${saved.label} at ${saved.time_s.toFixed(2)}s. Next frame ${nextFrame.time_s.toFixed(2)}s loaded.`);
      } else {
        setMessage(`Saved ${saved.label} at ${saved.time_s.toFixed(2)}s. Final frame complete.`);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  useEffect(() => {
    function handleAnnotationShortcut(event) {
      const tagName = event.target?.tagName || "";
      if (event.key !== "Enter" || event.repeat || event.ctrlKey || event.altKey || event.shiftKey || event.metaKey) return;
      if (["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(tagName)) return;
      if (!draftBox || procedureBusy || !activeFrame) return;
      event.preventDefault();
      void saveFrameAnnotation();
    }

    window.addEventListener("keydown", handleAnnotationShortcut);
    return () => window.removeEventListener("keydown", handleAnnotationShortcut);
  }, [activeFrame, draftBox, procedureBusy, saveFrameAnnotation]);

  async function checkQuality() {
    if (!selectedId) return;
    setProcedureBusy(true);
    setError("");
    try {
      const report = await readJson(`/api/activities/${encodeURIComponent(selectedId)}/dataset/quality/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      setQuality(report);
      setMessage(report.passed ? "Dataset quality gate passed." : "Dataset quality gate found issues to fix.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  async function startEvaluation() {
    if (!selectedId) return;
    setProcedureBusy(true);
    setError("");
    try {
      await readJson(`/api/activities/${encodeURIComponent(selectedId)}/evaluation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device: "auto" }),
      });
      setMessage("Held-out evaluation started. Results will appear here when complete.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  async function createRelease() {
    if (!selectedId || !evaluationReport?.passed || !latestEvaluationJob?.report_id) return;
    setProcedureBusy(true);
    setError("");
    try {
      const release = await readJson(`/api/activities/${encodeURIComponent(selectedId)}/releases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          evaluation_report_id: latestEvaluationJob.report_id,
          model_path: latestEvaluationJob.model_path,
          version: `0.1.${releases.length + 1}`,
        }),
      });
      setReleases((current) => [...current, release]);
      setMessage(`Release candidate ${release.version} created with a checksum.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  async function approveRelease(releaseId) {
    if (!selectedId || !reviewer.trim()) return;
    setProcedureBusy(true);
    setError("");
    try {
      const approved = await readJson(`/api/activities/${encodeURIComponent(selectedId)}/releases/${encodeURIComponent(releaseId)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewer }),
      });
      setReleases((current) => current.map((release) => release.id === approved.id ? approved : release));
      setMessage(`Release ${approved.version} approved by ${approved.approved_by}.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcedureBusy(false);
    }
  }

  const selected = activities.find((activity) => activity.id === selectedId);
  const latestDatasetJob = datasetJobs[datasetJobs.length - 1];
  const latestTrainingJob = trainingJobs[trainingJobs.length - 1];
  const latestEvaluationJob = evaluationJobs[evaluationJobs.length - 1];
  const detectorClasses = [...new Set(procedure.objects.flatMap((object) => splitValues(object.classes)))];
  const activeFrameAnnotations = annotations.filter((annotation) => annotation.frame_id === activeFrame?.frame_id);

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
              <div className="upload-block procedure-block">
                <div className="panel-heading compact">
                  <div><span className="section-kicker">STEP 01</span><h2>Approved procedure</h2></div>
                  <span className="step-count">{procedureExists ? "SAVED" : "DRAFT"}</span>
                </div>
                <div className="procedure-fields">
                  <label>Procedure name<input value={procedure.name} onChange={(event) => setProcedure((current) => ({ ...current, name: event.target.value }))} placeholder={selected.name} /></label>
                  <label>Description<textarea value={procedure.description} onChange={(event) => setProcedure((current) => ({ ...current, description: event.target.value }))} rows="2" placeholder="What must be completed?" /></label>
                </div>
                <div className="builder-heading"><span className="section-kicker">OBJECTS</span><button className="text-button" onClick={addObject} type="button">+ Add object</button></div>
                {procedure.objects.map((object, index) => (
                  <div className="builder-row object-builder-row" key={`object-${index}`}>
                    <input value={object.id} onChange={(event) => updateObject(index, "id", event.target.value)} placeholder="logical_object_id" aria-label="Object ID" />
                    <input value={object.classes} onChange={(event) => updateObject(index, "classes", event.target.value)} placeholder="detector_class" aria-label="Detector classes" />
                    <input value={object.colors_any} onChange={(event) => updateObject(index, "colors_any", event.target.value)} placeholder="colors, optional" aria-label="Object colors" />
                    <button className="remove-button" onClick={() => removeObject(index)} type="button">Remove</button>
                  </div>
                ))}
                <div className="builder-heading"><span className="section-kicker">STEPS</span><button className="text-button" onClick={addStep} type="button">+ Add step</button></div>
                {procedure.steps.map((step, index) => (
                  <div className="step-builder" key={`step-${index}`}>
                    <div className="builder-row step-header-row">
                      <input value={step.id} onChange={(event) => updateStep(index, "id", event.target.value)} placeholder="step_id" aria-label="Step ID" />
                      <input value={step.description} onChange={(event) => updateStep(index, "description", event.target.value)} placeholder="What should happen?" aria-label="Step description" />
                      <button className="remove-button" onClick={() => removeStep(index)} type="button">Remove</button>
                    </div>
                    <div className="builder-row">
                      <select value={step.kind} onChange={(event) => updateStep(index, "kind", event.target.value)} aria-label="Evidence kind">
                        <option value="actor_visible">Actor visible</option>
                        <option value="object_visible">Object visible</option>
                        <option value="hand_object_interaction">Hand-object action</option>
                        <option value="object_state">Object state</option>
                      </select>
                      <input value={step.object} onChange={(event) => updateStep(index, "object", event.target.value)} placeholder="object ID" aria-label="Evidence object" />
                      <input value={step.label} onChange={(event) => updateStep(index, "label", event.target.value)} placeholder="action label" aria-label="Evidence label" />
                    </div>
                    <div className="builder-row builder-row-small">
                      <input type="number" min="1" value={step.min_frames} onChange={(event) => updateStep(index, "min_frames", event.target.value)} placeholder="min frames" aria-label="Minimum frames" />
                      <input type="number" min="1" value={step.expected_duration_s} onChange={(event) => updateStep(index, "expected_duration_s", event.target.value)} placeholder="expected seconds" aria-label="Expected duration" />
                      <input value={step.next} onChange={(event) => updateStep(index, "next", event.target.value)} placeholder="next step IDs, comma-separated" aria-label="Next steps" />
                    </div>
                  </div>
                ))}
                <button className="button button-primary" onClick={saveProcedure} disabled={procedureBusy} type="button">{procedureBusy ? "Validating…" : "Validate and save procedure"}</button>
              </div>
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
              <div className="upload-block">
                <div className="panel-heading compact">
                  <div><span className="section-kicker">STEP 04</span><h2>Prepare and train</h2></div>
                  <span className="step-count">{hardware?.device || "CHECKING"}</span>
                </div>
                <p className="workflow-copy">The Studio keeps recording sessions together, prepares the dataset, and trains a laptop-sized detector with CUDA when available.</p>
                <div className="training-actions">
                  <button className="button button-quiet" onClick={prepareDataset} disabled={procedureBusy || !procedureExists || takes.length === 0}>Prepare dataset</button>
                  <button className="button button-primary" onClick={startTraining} disabled={procedureBusy || !dataset}>Start laptop-safe training</button>
                </div>
                <div className="job-status-grid">
                  <div><span>GPU</span><strong>{hardware?.device_name || (hardware?.cuda_available ? hardware.device : "CPU fallback")}</strong></div>
                  <div><span>VRAM</span><strong>{hardware?.vram_gb ? `${hardware.vram_gb} GB` : "--"}</strong></div>
                  <div><span>Dataset</span><strong>{dataset ? `${dataset.dataset.id} ready` : latestDatasetJob?.status || "not prepared"}</strong></div>
                  <div><span>Training</span><strong>{latestTrainingJob?.status || "not started"}</strong></div>
                </div>
              </div>
              <div className="upload-block annotation-block">
                <div className="panel-heading compact">
                  <div><span className="section-kicker">STEP 05</span><h2>Assist frame annotation</h2></div>
                  <span className="step-count">{annotations.length}</span>
                </div>
                <p className="workflow-copy">Choose a take and frame, drag around each object, and save the human-reviewed box. These labels are the trusted correction layer for training.</p>
                <div className="annotation-controls">
                  <label>Take
                    <select value={selectedTakeId} onChange={(event) => setSelectedTakeId(event.target.value)}>
                      {takes.map((take) => <option key={take.id} value={take.id}>{take.id}</option>)}
                    </select>
                  </label>
                  <label>Sample every frames
                    <input type="number" min="1" max="300" value={frameEvery} onChange={(event) => setFrameEvery(Number(event.target.value) || 30)} />
                  </label>
                  <label>Label
                    <select value={annotationLabel} onChange={(event) => setAnnotationLabel(event.target.value)}>
                      <option value="">Choose detector class</option>
                      {detectorClasses.map((label) => <option key={label} value={label}>{label}</option>)}
                    </select>
                  </label>
                  <label>Frame
                    <select
                      value={activeFrame ? String(activeFrame.frame_id) : ""}
                      onChange={(event) => {
                        const frame = keyframes.find((item) => String(item.frame_id) === event.target.value);
                        if (!frame) return;
                        setActiveFrame(frame);
                        setDraftBox(null);
                        setDragStart(null);
                      }}
                      disabled={keyframes.length === 0}
                    >
                      <option value="" disabled>Choose frame</option>
                      {keyframes.map((frame, index) => {
                        const savedCount = annotations.filter((annotation) => annotation.frame_id === frame.frame_id).length;
                        return <option key={frame.frame_id} value={frame.frame_id}>{`${String(index + 1).padStart(2, "0")} · ${frame.time_s.toFixed(2)}s${savedCount ? ` · ${savedCount} saved` : ""}`}</option>;
                      })}
                    </select>
                  </label>
                </div>
                {activeFrame && (
                  <div className="annotation-editor">
                    <div className="annotation-image-wrap">
                      <img
                        src={activeFrame.image_url}
                        alt={`Annotation frame at ${activeFrame.time_s.toFixed(2)} seconds`}
                        onPointerDown={handleFramePointerDown}
                        onPointerMove={handleFramePointerMove}
                        onPointerUp={handleFramePointerUp}
                        draggable="false"
                        tabIndex="0"
                      />
                      {activeFrameAnnotations.map((annotation) => (
                        <span className="annotation-box saved" key={annotation.id} style={{ left: `${annotation.bbox.x1 / activeFrame.width * 100}%`, top: `${annotation.bbox.y1 / activeFrame.height * 100}%`, width: `${(annotation.bbox.x2 - annotation.bbox.x1) / activeFrame.width * 100}%`, height: `${(annotation.bbox.y2 - annotation.bbox.y1) / activeFrame.height * 100}%` }}><b>{annotation.label}</b></span>
                      ))}
                      {draftBox && <span className="annotation-box draft" style={{ left: `${draftBox.x1 / activeFrame.width * 100}%`, top: `${draftBox.y1 / activeFrame.height * 100}%`, width: `${(draftBox.x2 - draftBox.x1) / activeFrame.width * 100}%`, height: `${(draftBox.y2 - draftBox.y1) / activeFrame.height * 100}%` }} />}
                    </div>
                    <div className="annotation-actions">
                      <span>{activeFrame.time_s.toFixed(2)}s · {activeFrameAnnotations.length} saved label(s) · Press Enter to save and load next</span>
                      <button className="button button-primary" onClick={saveFrameAnnotation} disabled={!draftBox || procedureBusy} type="button">Save &amp; next frame</button>
                    </div>
                  </div>
                )}
                {keyframes.length === 0 && <div className="studio-empty">Upload a take to load sampled keyframes.</div>}
              </div>
              <div className="upload-block">
                <div className="panel-heading compact">
                  <div><span className="section-kicker">STEP 06</span><h2>Quality gate and evaluation</h2></div>
                  <span className={`step-count ${quality?.passed ? "passed" : ""}`}>{quality ? (quality.passed ? "PASS" : "FIX") : "NOT RUN"}</span>
                </div>
                <p className="workflow-copy">Run integrity checks before training, then score the trained detector only on held-out takes. A release is not approved automatically.</p>
                <div className="training-actions">
                  <button className="button button-quiet" onClick={checkQuality} disabled={!dataset || procedureBusy}>Run dataset quality check</button>
                  <button className="button button-primary" onClick={startEvaluation} disabled={procedureBusy || latestTrainingJob?.status !== "completed" || !quality?.passed}>Evaluate held-out test split</button>
                </div>
                {quality && <div className="quality-summary"><span>{quality.images_by_split.train} train · {quality.images_by_split.val} val · {quality.images_by_split.test} test</span><span>{Object.entries(quality.sessions_by_split || {}).map(([split, sessions]) => `${split}: ${sessions.length} session(s)`).join(" · ")}</span><span>{Object.entries(quality.class_counts).map(([label, count]) => `${label}: ${count}`).join(" · ")}</span></div>}
                {quality?.warnings?.map((warning) => <div className="warning-banner" key={warning}>{warning}</div>)}
                <div className="job-status-grid">
                  <div><span>Evaluation</span><strong>{latestEvaluationJob?.status || "not started"}</strong></div>
                  <div><span>Result</span><strong>{evaluationReport ? (evaluationReport.passed ? "PASS" : "REVIEW") : "--"}</strong></div>
                  <div><span>Precision</span><strong>{evaluationReport ? `${(evaluationReport.metrics.precision * 100).toFixed(1)}%` : "--"}</strong></div>
                  <div><span>Recall</span><strong>{evaluationReport ? `${(evaluationReport.metrics.recall * 100).toFixed(1)}%` : "--"}</strong></div>
                </div>
                {evaluationReport && <div className="evaluation-summary"><a className="button button-quiet" href={`/api/activities/${encodeURIComponent(selectedId)}/evaluation/reports/${encodeURIComponent(evaluationReport.id)}.csv`}>Download evaluation CSV</a><span>{evaluationReport.failure_gallery.length} failing test image(s)</span></div>}
                {evaluationReport?.failure_gallery?.slice(0, 5).map((failure) => <div className="failure-row" key={failure.image}><span>{failure.image}</span><em>FP {failure.false_positive} · FN {failure.false_negative}</em></div>)}
                <div className="release-controls">
                  <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="Reviewer name for approval" aria-label="Reviewer name" />
                  <button className="button button-quiet" onClick={createRelease} disabled={procedureBusy || !evaluationReport?.passed || !latestEvaluationJob?.report_id}>Create checksummed candidate</button>
                </div>
                {releases.map((release) => (
                  <div className="release-row" key={release.id}>
                    <span><strong>{release.version}</strong><small>{release.status} · {release.model_sha256?.slice(0, 16)}…</small></span>
                    {release.status === "candidate" && <button className="text-button" onClick={() => approveRelease(release.id)} disabled={procedureBusy || !reviewer.trim()} type="button">Approve</button>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}

export default TrainingStudio;
