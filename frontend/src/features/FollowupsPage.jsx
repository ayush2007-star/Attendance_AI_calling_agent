import { useCallback, useEffect, useState } from "react";
import { Clock, RefreshCw } from "lucide-react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function FollowupsPage({ onNavigateToVoice }) {
  const [followups, setFollowups] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busyId, setBusyId] = useState("");

  const loadFollowups = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.followups({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      });
      setFollowups(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter]);

  useEffect(() => {
    let active = true;
    api.followups({
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
    })
      .then((data) => {
        if (active) setFollowups(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => { active = false; };
  }, [statusFilter, priorityFilter]);

  async function handleStatusChange(id, newStatus) {
    setBusyId(id);
    setError("");
    setSuccess("");
    try {
      await api.updateFollowupStatus(id, newStatus);
      setSuccess(`Follow-up marked as ${newStatus}.`);
      await loadFollowups();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId("");
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section className="content-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 14 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <Clock size={20} className="text-cyan" />
              <h3 style={{ margin: 0 }}>Parent Follow-up & Callback Management</h3>
            </div>
            <p className="call-safety-note" style={{ margin: 0 }}>
              Track parents who requested callbacks, disputed attendance, or need administrative contact.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ padding: "6px 12px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", borderRadius: 6 }}
            >
              <option value="">All Statuses</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="DUE">Due Today</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              style={{ padding: "6px 12px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", borderRadius: 6 }}
            >
              <option value="">All Priorities</option>
              <option value="HIGH">High Priority</option>
              <option value="MEDIUM">Medium Priority</option>
              <option value="LOW">Low Priority</option>
            </select>

            <button
              className="button button-secondary"
              onClick={loadFollowups}
              disabled={loading}
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              <RefreshCw size={14} className={loading ? "spinning" : ""} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </section>

      <Notice>{error}</Notice>
      {success && <Notice tone="success">{success}</Notice>}

      <section className="content-card">
        {loading ? (
          <p className="empty-state">Loading follow-ups…</p>
        ) : !followups.length ? (
          <p className="empty-state">No follow-ups recorded matching the selected filter.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Student</th>
                  <th>Guardian</th>
                  <th>Contact Number</th>
                  <th>Scheduled Callback</th>
                  <th>Reason / AI Summary</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {followups.map((f) => {
                  const isCompleted = f.status === "COMPLETED";
                  const isCancelled = f.status === "CANCELLED";
                  const isHigh = f.priority === "HIGH";

                  return (
                    <tr key={f.id}>
                      <td>
                        <span className={`badge ${isHigh ? "badge-rose" : "badge-amber"}`} style={{ fontSize: "0.75rem", padding: "2px 6px" }}>
                          {f.priority}
                        </span>
                      </td>
                      <td>
                        <strong>{f.student_name}</strong>
                        {f.roll_number && <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Roll: {f.roll_number}</div>}
                      </td>
                      <td>{f.parent_name || "Guardian"}</td>
                      <td><code>{f.parent_phone || "—"}</code></td>
                      <td>
                        <div style={{ fontSize: "0.85rem", whiteSpace: "nowrap" }}>
                          {f.scheduled_for ? new Date(f.scheduled_for).toLocaleString() : "Not set"}
                        </div>
                      </td>
                      <td style={{ maxWidth: 280 }}>
                        <span style={{ fontSize: "0.85rem", lineHeight: 1.3 }}>{f.reason}</span>
                      </td>
                      <td>
                        <span className={`badge ${isCompleted ? "badge-emerald" : isCancelled ? "badge-gray" : "badge-cyan"}`} style={{ fontSize: "0.75rem", padding: "2px 6px" }}>
                          {f.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          {!isCompleted && !isCancelled && (
                            <>
                              <button
                                className="button button-primary"
                                style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                                disabled={busyId === f.id}
                                onClick={() => handleStatusChange(f.id, "COMPLETED")}
                              >
                                Mark Done
                              </button>
                              <button
                                className="button button-secondary"
                                style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                                disabled={busyId === f.id}
                                onClick={() => handleStatusChange(f.id, "CANCELLED")}
                              >
                                Cancel
                              </button>
                            </>
                          )}
                          {onNavigateToVoice && (
                            <button
                              className="button button-secondary"
                              style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                              onClick={() => onNavigateToVoice(f.student_id)}
                            >
                              Call Screen
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
