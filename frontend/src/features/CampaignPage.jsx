import { useEffect, useState } from "react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function CampaignPage({ user }) {
  const [classes, setClasses] = useState([]);
  const [form, setForm] = useState({ name: "", attendance_date: new Date().toISOString().slice(0, 10), class_id: "" });
  const [result, setResult] = useState(null);
  const [targets, setTargets] = useState([]);
  const [targetLoadError, setTargetLoadError] = useState("");
  const [queueingTargetId, setQueueingTargetId] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.classes().then(setClasses).catch((requestError) => setError(requestError.message));
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setTargetLoadError("");
    setResult(null);
    setTargets([]);
    setBusy(true);
    const body = {
      name: form.name,
      attendance_date: form.attendance_date,
      class_id: form.class_id || null,
    };
    try {
      const campaign = await api.createCampaign(body);
      setResult(campaign);
      try {
        setTargets(await api.campaignTargets(campaign.id));
      } catch (requestError) {
        setTargetLoadError(requestError.message);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function queueTarget(targetId) {
    setQueueingTargetId(targetId);
    setError("");
    setSuccess("");
    try {
      const attempt = await api.queueCampaignTarget(targetId);
      setTargets((items) => items.map((item) => item.id === targetId ? { ...item, status: attempt.status } : item));
      setSuccess("Call attempt queued. This does not place a phone call.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setQueueingTargetId("");
    }
  }

  return (
    <>
    <section className="content-card narrow-card">
      <div className="section-heading"><div><h3>Create an absent-student campaign</h3><p>Review students marked absent on the selected date and snapshot their saved guardian contacts.</p></div></div>
      <Notice>{error}</Notice>
      <Notice tone="success">{success}</Notice>
      {result && <Notice tone="success">Campaign created ({result.status}). {result.total_targets} eligible target(s) recorded. This did not place any calls.</Notice>}
      <form className="stack-form" onSubmit={submit}>
        <label>Campaign name<input required maxLength={200} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Low attendance follow-up" /></label>
        <label>Attendance date<input type="date" required value={form.attendance_date} onChange={(event) => setForm({ ...form, attendance_date: event.target.value })} /></label>
        <label>Class or section<select value={form.class_id} onChange={(event) => setForm({ ...form, class_id: event.target.value })}><option value="">Institution-wide (administrator only)</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.course_name} · {item.section} · Year {item.year}</option>)}</select></label>
        <button className="button button-primary" disabled={busy}>{busy ? "Creating…" : "Create campaign"}</button>
      </form>
      <p className="call-safety-note">Only students marked absent for this exact date are included; attendance-percentage thresholds do not add present students. Campaign creation saves a reviewable snapshot and does not place calls. The current backend call provider is local simulation, not a live phone service.</p>
    </section>
    {result && (
      <section className="content-card">
        <div className="section-heading"><div><h3>Review absent students and guardian contacts</h3><p>Confirm each saved contact before an authorized call worker acts.</p></div></div>
        {targetLoadError ? (
          <Notice>
            Campaign was created, but its targets could not be loaded: {targetLoadError}
          </Notice>
        ) : !targets.length ? <p className="empty-state">No absent students were found for this date.</p> : (
          <div className="table-scroll"><table><thead><tr><th>Roll number</th><th>Student</th><th>Guardian</th><th>Phone</th><th>Attendance</th><th>Status</th>{user.permissions.includes("calls.manage") && <th>Action</th>}</tr></thead>
            <tbody>{targets.map((target) => (
              <tr key={target.id}>
                <td>{target.roll_number}</td><td>{target.student_name} · {target.student_code}</td>
                <td>{target.parent_name || "No primary guardian"}</td><td>{target.phone_number || "No phone saved"}</td>
                <td>{target.attendance_percentage}%</td><td>{target.status}</td>
                {user.permissions.includes("calls.manage") && <td><button className="button button-secondary" disabled={!target.phone_number || !["PENDING", "FAILED"].includes(target.status) || queueingTargetId === target.id} onClick={() => queueTarget(target.id)}>{queueingTargetId === target.id ? "Queueing…" : "Queue call"}</button></td>}
              </tr>
            ))}</tbody></table>
          </div>
        )}
        <p className="call-safety-note">Queueing creates a call attempt only. The configured backend provider is local simulation; real calls are not enabled.</p>
      </section>
    )}
    </>
  );
}
