import { useEffect, useState } from "react";
import {
  Check,
  X,
  Clock,
  Save,
  PhoneCall,
  Calendar,
  Users,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { api } from "../api/client";

export default function AttendanceTerminal({ user, onNavigateToVoice }) {
  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [roster, setRoster] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState({ message: "", type: "" });

  useEffect(() => {
    let active = true;
    api.classes()
      .then((clsList) => {
        if (!active) return;
        setClasses(clsList);
        if (clsList.length > 0) {
          setSelectedClassId(clsList[0].id);
        }
      })
      .catch((err) => {
        if (active) setNotice({ message: err.message, type: "error" });
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedClassId) return;
    let active = true;

    api.attendanceList(selectedClassId, selectedDate)
      .then((data) => {
        if (!active) return;
        setNotice({ message: "", type: "" });
        setRoster(
          data.map((item) => ({
            ...item,
          }))
        );
      })
      .catch((err) => {
        if (active) setNotice({ message: err.message, type: "error" });
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedClassId, selectedDate]);

  function setStudentStatus(studentId, newStatus) {
    setRoster((prev) =>
      prev.map((s) => (s.student_id === studentId ? { ...s, status: newStatus } : s))
    );
  }

  function markAll(status) {
    setRoster((prev) => prev.map((s) => ({ ...s, status })));
  }

  async function saveAttendance() {
    if (!selectedClassId || roster.length === 0) return;
    const markedRoster = roster.filter((student) => student.status !== "NOT_MARKED");
    if (!markedRoster.length) {
      setNotice({ message: "Mark at least one student's attendance before saving.", type: "error" });
      return;
    }
    setSaving(true);
    setNotice({ message: "", type: "" });

    try {
      const payload = {
        class_id: selectedClassId,
        attendance_date: selectedDate,
        source_reference: `2026 Smart Terminal (${user.full_name})`,
        records: markedRoster.map((s) => ({
          student_id: s.student_id,
          status: s.status,
        })),
      };

      const res = await api.saveBulkAttendance(payload);
      setNotice({
        message: `Attendance synchronized successfully: ${res.total_marked} marked, ${res.absent_count} absentees logged for follow-up.`,
        type: "success",
      });
    } catch (err) {
      setNotice({ message: err.message, type: "error" });
    } finally {
      setSaving(false);
    }
  }

  const presentCount = roster.filter((s) => s.status === "PRESENT").length;
  const absentCount = roster.filter((s) => s.status === "ABSENT").length;
  const lateCount = roster.filter((s) => s.status === "LATE").length;
  const total = roster.filter((s) => s.status !== "NOT_MARKED").length || 1;
  const attendanceRate = Math.round(((presentCount + lateCount) / total) * 100);

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* Control Header & Filters */}
      <div className="bento-card glow-cyan" style={{ padding: 22 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="brand-hologram-cube" style={{ width: 44, height: 44, borderRadius: 12 }}>
              <Users size={22} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "#fff" }}>
                Smart Roll Call Terminal · 2026
              </h2>
              <p style={{ margin: "3px 0 0", fontSize: 12, color: "#94a3b8" }}>
                Mark attendance by class and date. Unmarked students are not saved.
              </p>
            </div>
          </div>

          {/* Controls: Class & Date */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#94a3b8" }}>
              <span>Class:</span>
              <select
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(e.target.value)}
                style={{
                  background: "rgba(15, 23, 42, 0.9)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "#fff",
                  borderRadius: 8,
                  padding: "6px 12px",
                  fontSize: 12,
                }}
              >
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.course_name} · Sec {c.section} (Sem {c.semester})
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#94a3b8" }}>
              <Calendar size={14} />
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                style={{
                  background: "rgba(15, 23, 42, 0.9)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "#fff",
                  borderRadius: 8,
                  padding: "6px 10px",
                  fontSize: 12,
                }}
              />
            </label>

            <button
              onClick={() => markAll("PRESENT")}
              className="btn-quantum btn-quantum-glass"
              style={{ padding: "6px 12px", fontSize: 11 }}
            >
              <CheckCircle2 size={14} color="#10b981" />
              Mark All Present
            </button>

            <button
              onClick={saveAttendance}
              disabled={saving || roster.length === 0}
              className="btn-quantum btn-quantum-primary"
              style={{ padding: "7px 18px", fontSize: 12 }}
            >
              <Save size={15} />
              {saving ? "Saving…" : "Save Attendance"}
            </button>
          </div>
        </div>

        {/* Live Metrics Pill Strip */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: 12,
            marginTop: 18,
            paddingTop: 16,
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "10px 14px", borderRadius: 10 }}>
            <span style={{ fontSize: 11, color: "#94a3b8" }}>Total Enrolled</span>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#fff" }}>{roster.length}</div>
          </div>
          <div style={{ background: "rgba(16, 185, 129, 0.08)", padding: "10px 14px", borderRadius: 10, borderLeft: "3px solid #10b981" }}>
            <span style={{ fontSize: 11, color: "#34d399" }}>Present</span>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#34d399" }}>{presentCount}</div>
          </div>
          <div style={{ background: "rgba(239, 68, 68, 0.08)", padding: "10px 14px", borderRadius: 10, borderLeft: "3px solid #ef4444" }}>
            <span style={{ fontSize: 11, color: "#f87171" }}>Absent</span>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#f87171" }}>{absentCount}</div>
          </div>
          <div style={{ background: "rgba(245, 158, 11, 0.08)", padding: "10px 14px", borderRadius: 10, borderLeft: "3px solid #f59e0b" }}>
            <span style={{ fontSize: 11, color: "#fbbf24" }}>Late Arrival</span>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#fbbf24" }}>{lateCount}</div>
          </div>
          <div style={{ background: "rgba(6, 182, 212, 0.08)", padding: "10px 14px", borderRadius: 10, borderLeft: "3px solid #06b6d4" }}>
            <span style={{ fontSize: 11, color: "#38bdf8" }}>Marked Attendance Rate</span>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#38bdf8" }}>{attendanceRate}%</div>
          </div>
        </div>
      </div>

      {notice.message && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: 10,
            fontSize: 12,
            background: notice.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            color: notice.type === "success" ? "#34d399" : "#f87171",
            border: `1px solid ${notice.type === "success" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
          }}
        >
          {notice.message}
        </div>
      )}

      {/* Roster Grid Table */}
      <div className="bento-card" style={{ padding: 20 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>
            <RefreshCw size={24} className="pulse-beacon" />
            <p>Loading classroom roster…</p>
          </div>
        ) : roster.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, color: "#64748b" }}>
            <AlertCircle size={28} />
            <p>No active students found in this class.</p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="terminal-roster-table">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>Roll #</th>
                  <th>Student Name</th>
                  <th>Code</th>
                  <th style={{ textAlign: "center" }}>1-Tap Attendance State</th>
                  <th style={{ textAlign: "right" }}>Autonomous Action</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((s) => (
                  <tr key={s.student_id} className="terminal-roster-row">
                    <td style={{ fontWeight: 800, color: "#38bdf8", fontFamily: "monospace" }}>
                      #{s.roll_number}
                    </td>
                    <td>
                      <div style={{ fontWeight: 650, color: "#fff", fontSize: 13 }}>
                        {s.student_name}
                      </div>
                      <span style={{ fontSize: 10, color: "#64748b" }}>Registered Scholar</span>
                    </td>
                    <td style={{ color: "#94a3b8", fontSize: 11, fontFamily: "monospace" }}>
                      {s.student_code}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      <div className="toggle-btn-group">
                        <button
                          type="button"
                          className={`toggle-chip ${s.status === "PRESENT" ? "active-present" : ""}`}
                          onClick={() => setStudentStatus(s.student_id, "PRESENT")}
                        >
                          <Check size={12} style={{ display: "inline", marginRight: 3 }} />
                          Present
                        </button>
                        <button
                          type="button"
                          className={`toggle-chip ${s.status === "ABSENT" ? "active-absent" : ""}`}
                          onClick={() => setStudentStatus(s.student_id, "ABSENT")}
                        >
                          <X size={12} style={{ display: "inline", marginRight: 3 }} />
                          Absent
                        </button>
                        <button
                          type="button"
                          className={`toggle-chip ${s.status === "LATE" ? "active-late" : ""}`}
                          onClick={() => setStudentStatus(s.student_id, "LATE")}
                        >
                          <Clock size={12} style={{ display: "inline", marginRight: 3 }} />
                          Late
                        </button>
                        <button
                          type="button"
                          className={`toggle-chip ${s.status === "EXCUSED" ? "active-excused" : ""}`}
                          onClick={() => setStudentStatus(s.student_id, "EXCUSED")}
                        >
                          Excused
                        </button>
                      </div>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {s.status === "ABSENT" ? (
                        <button
                          onClick={() => onNavigateToVoice && onNavigateToVoice(s.student_id)}
                          className="btn-quantum btn-quantum-glass"
                          style={{
                            padding: "5px 12px",
                            fontSize: 11,
                            color: "#fb7185",
                            borderColor: "rgba(244, 63, 94, 0.3)",
                            background: "rgba(244, 63, 94, 0.08)",
                          }}
                        >
                          <PhoneCall size={12} />
                          Review voice options
                        </button>
                      ) : (
                        <span style={{ fontSize: 11, color: s.status === "NOT_MARKED" ? "#94a3b8" : "#10b981", display: "inline-flex", alignItems: "center", gap: 4 }}>
                          {s.status === "NOT_MARKED" ? "Not marked" : <><CheckCircle2 size={13} /> Recorded in roster</>}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
