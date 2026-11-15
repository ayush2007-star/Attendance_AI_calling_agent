import { useEffect, useState } from "react";
import {
  Brain,
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  Search,
  PhoneCall,
} from "lucide-react";
import { api } from "../api/client";

export default function MLRiskPage({ onSelectStudentForVoice }) {
  const [insights, setInsights] = useState(null);
  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [selectedRiskTier, setSelectedRiskTier] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.classes()
      .then((clsList) => {
        if (active) setClasses(clsList);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    api.mlRiskAnalysis(
      selectedClassId || undefined,
      selectedRiskTier === "ALL" ? undefined : selectedRiskTier,
      searchQuery || undefined
    )
      .then((data) => {
        if (active) {
          setInsights(data);
          setError("");
        }
      })
      .catch((err) => {
        if (active) {
          setInsights(null);
          setError(err.message);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedClassId, selectedRiskTier, searchQuery]);

  const metrics = insights?.metrics;
  const students = insights?.students || [];

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* ML Executive Banner */}
      <div className="bento-card glow-violet" style={{ padding: 26 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="brand-hologram-cube" style={{ width: 48, height: 48, borderRadius: 14, background: "var(--grad-violet)" }}>
              <Brain size={26} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="role-clearance-pill admin" style={{ fontSize: 10, padding: "2px 8px" }}>
                  Rule-based attendance indicators
                </span>
                <span style={{ fontSize: 10, color: "#64748b" }}>Advisory · not a trained ML prediction</span>
              </div>
              <h2 style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800, color: "#fff" }}>
                Attendance Risk Review
              </h2>
              <p style={{ margin: "3px 0 0", fontSize: 12, color: "#94a3b8" }}>
                Calculated from saved attendance records. Review the underlying data before acting.
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 11, color: "#94a3b8", display: "flex", alignItems: "center", gap: 5 }}>
            Current saved records
            </span>
          </div>
        </div>

        {/* Metric Cards Row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(145px, 1fr))",
            gap: 14,
            marginTop: 22,
          }}
        >
          <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "14px 18px", borderRadius: 12, border: "1px solid rgba(255, 255, 255, 0.06)" }}>
            <span style={{ fontSize: 11, color: "#94a3b8" }}>Average recorded attendance</span>
            <div style={{ fontSize: 26, fontWeight: 800, color: "#fff", marginTop: 4 }}>
              {metrics?.average_attendance == null ? "—" : `${metrics.average_attendance}%`}
            </div>
            <span style={{ fontSize: 10, color: "#34d399", display: "inline-flex", alignItems: "center", gap: 3 }}>
              {metrics?.students_with_attendance ?? 0} students with attendance data
            </span>
          </div>

          <div style={{ background: "rgba(239, 68, 68, 0.08)", padding: "14px 18px", borderRadius: 12, border: "1px solid rgba(239, 68, 68, 0.2)" }}>
            <span style={{ fontSize: 11, color: "#f87171" }}>Critical attendance risk</span>
            <div style={{ fontSize: 26, fontWeight: 800, color: "#f87171", marginTop: 4 }}>
              {metrics?.critical_risk_count ?? 0} <small style={{ fontSize: 13, fontWeight: 500 }}>students</small>
            </div>
            <span style={{ fontSize: 10, color: "#fda4af" }}>Urgent intervention required</span>
          </div>

          <div style={{ background: "rgba(245, 158, 11, 0.08)", padding: "14px 18px", borderRadius: 12, border: "1px solid rgba(245, 158, 11, 0.2)" }}>
            <span style={{ fontSize: 11, color: "#fbbf24" }}>Elevated Warning Zone</span>
            <div style={{ fontSize: 26, fontWeight: 800, color: "#fbbf24", marginTop: 4 }}>
              {metrics?.elevated_risk_count ?? 0} <small style={{ fontSize: 13, fontWeight: 500 }}>students</small>
            </div>
            <span style={{ fontSize: 10, color: "#fde68a" }}>Between 60% and 75%</span>
          </div>

          <div style={{ background: "rgba(139, 92, 246, 0.08)", padding: "14px 18px", borderRadius: 12, border: "1px solid rgba(139, 92, 246, 0.2)" }}>
            <span style={{ fontSize: 11, color: "#c084fc" }}>Anomaly Flags</span>
            <div style={{ fontSize: 26, fontWeight: 800, color: "#c084fc", marginTop: 4 }}>
              {metrics?.anomalies_detected ?? 0} <small style={{ fontSize: 13, fontWeight: 500 }}>flags</small>
            </div>
            <span style={{ fontSize: 10, color: "#d8b4fe" }}>Sharp drops & streaks</span>
          </div>
          <div style={{ background: "rgba(148, 163, 184, 0.08)", padding: "14px 18px", borderRadius: 12, border: "1px solid rgba(148, 163, 184, 0.2)" }}>
            <span style={{ fontSize: 11, color: "#cbd5e1" }}>Needs attendance data</span>
            <div style={{ fontSize: 26, fontWeight: 800, color: "#cbd5e1", marginTop: 4 }}>
              {metrics?.no_attendance_data_count ?? 0} <small style={{ fontSize: 13, fontWeight: 500 }}>students</small>
            </div>
            <span style={{ fontSize: 10, color: "#94a3b8" }}>No risk score assigned</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bento-card" style={{ padding: 18 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
          {/* Risk Tier Tabs */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "#94a3b8", marginRight: 4 }}>Risk Filter:</span>
            {["ALL", "CRITICAL", "ELEVATED", "NORMAL"].map((tier) => (
              <button
                key={tier}
                onClick={() => setSelectedRiskTier(tier)}
                className={`nav-pill ${selectedRiskTier === tier ? "active" : ""}`}
                style={{ fontSize: 11, padding: "5px 12px" }}
              >
                {tier}
              </button>
            ))}
          </div>

          {/* Class Filter & Search */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
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
              <option value="">All Academic Classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.course_name} · Sec {c.section}
                </option>
              ))}
            </select>

            <div style={{ position: "relative" }}>
              <input
                type="text"
                placeholder="Search name or roll #"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: "rgba(15, 23, 42, 0.9)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "#fff",
                  borderRadius: 8,
                  padding: "6px 12px 6px 32px",
                  fontSize: 12,
                  width: 190,
                }}
              />
              <Search
                size={14}
                style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#64748b" }}
              />
            </div>
          </div>
        </div>
      </div>

      {error && <div className="notice">{error}</div>}

      {/* Attendance Risk Students */}
      <div className="bento-card" style={{ padding: 22 }}>
        {loading ? (
          <div className="page-state">Loading attendance risk indicators…</div>
        ) : !error && !students.length ? (
          <div className="empty-state">No matching students. Add attendance records to calculate risk indicators.</div>
        ) : !error && (
        <div style={{ overflowX: "auto" }}>
          <table className="terminal-roster-table">
            <thead>
              <tr>
                <th>Scholar</th>
                <th>Cumulative Att.</th>
                <th>Recent change (pp/day)</th>
                <th>Streak / Leaves</th>
                <th>Risk Classification</th>
                <th>AI Action Recommendation</th>
                <th style={{ textAlign: "right" }}>Next step</th>
              </tr>
            </thead>
            <tbody>
              {students.map((st) => (
                <tr key={st.id} className="terminal-roster-row">
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: 8,
                          background:
                            st.risk_tier === "CRITICAL"
                              ? "rgba(239, 68, 68, 0.2)"
                              : st.risk_tier === "ELEVATED"
                              ? "rgba(245, 158, 11, 0.2)"
                              : "rgba(16, 185, 129, 0.2)",
                          color:
                            st.risk_tier === "CRITICAL"
                              ? "#f87171"
                              : st.risk_tier === "ELEVATED"
                              ? "#fbbf24"
                              : "#34d399",
                          display: "grid",
                          placeItems: "center",
                          fontWeight: 800,
                          fontSize: 11,
                        }}
                      >
                        #{st.roll_number}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, color: "#fff", fontSize: 13 }}>
                          {st.full_name}
                        </div>
                        <span style={{ fontSize: 10, color: "#94a3b8" }}>
                          {st.class_name} · Parent: {st.parent?.name}
                        </span>
                      </div>
                    </div>
                  </td>

                  {/* Attendance with progress gauge */}
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 800, fontSize: 14, color: st.attendance_percentage == null ? "#94a3b8" : st.attendance_percentage < 60 ? "#ef4444" : st.attendance_percentage < 75 ? "#f59e0b" : "#10b981" }}>
                        {st.attendance_percentage == null ? "—" : `${st.attendance_percentage}%`}
                      </span>
                      <div style={{ width: 60, height: 6, background: "rgba(255, 255, 255, 0.08)", borderRadius: 3, overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${Math.min(100, st.attendance_percentage || 0)}%`,
                            height: "100%",
                            background:
                              st.attendance_percentage == null
                                ? "#64748b"
                                : st.attendance_percentage < 60
                                ? "#ef4444"
                                : st.attendance_percentage < 75
                                ? "#f59e0b"
                                : "#10b981",
                          }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Trend Velocity */}
                  <td>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 3,
                        fontSize: 11,
                        fontWeight: 650,
                        color: st.trend_slope == null ? "#94a3b8" : st.trend_slope < 0 ? "#f87171" : "#34d399",
                      }}
                    >
                      {st.trend_slope == null ? "—" : (
                        <>
                          {st.trend_slope < 0 ? <TrendingDown size={13} /> : <TrendingUp size={13} />}
                          {st.trend_slope > 0 ? `+${st.trend_slope}` : st.trend_slope}
                        </>
                      )}
                    </span>
                  </td>

                  {/* Streak & Leaves */}
                  <td>
                    <div style={{ fontSize: 11, color: "#cbd5e1" }}>
                      {st.consecutive_absent > 0 ? (
                        <span style={{ color: "#f87171", fontWeight: 700 }}>
                          {st.consecutive_absent} days streak
                        </span>
                      ) : (
                        <span style={{ color: "#64748b" }}>No active streak</span>
                      )}
                    </div>
                    <span style={{ fontSize: 10, color: "#94a3b8" }}>
                      {st.approved_leaves} approved leaves
                    </span>
                  </td>

                  {/* Risk Classification & Anomalies */}
                  <td>
                    <span className={`risk-tag ${st.risk_tier.toLowerCase()}`}>
                      {st.risk_tier === "CRITICAL" && <AlertTriangle size={11} />}
                      {st.risk_tier === "NO_DATA" ? "NO DATA" : st.risk_tier}
                    </span>
                    {st.anomalies && st.anomalies.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        {st.anomalies.map((a, idx) => (
                          <span
                            key={idx}
                            style={{
                              display: "inline-block",
                              fontSize: 9,
                              padding: "2px 6px",
                              borderRadius: 4,
                              background: "rgba(239, 68, 68, 0.15)",
                              color: "#fca5a5",
                              marginRight: 4,
                            }}
                          >
                            {a.label}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>

                  {/* Recommendation */}
                  <td style={{ maxWidth: 260 }}>
                    <p style={{ margin: 0, fontSize: 11, color: "#cbd5e1", lineHeight: 1.4 }}>
                      {st.ai_recommendation}
                    </p>
                  </td>

                  {/* Outreach Button */}
                  <td style={{ textAlign: "right" }}>
                    <button
                      onClick={() => onSelectStudentForVoice && onSelectStudentForVoice(st.id)}
                      className="btn-quantum btn-quantum-glass"
                      style={{
                        padding: "6px 12px",
                        fontSize: 11,
                        color: st.risk_tier === "CRITICAL" ? "#38bdf8" : "#cbd5e1",
                        borderColor: st.risk_tier === "CRITICAL" ? "rgba(56, 189, 248, 0.3)" : "rgba(255, 255, 255, 0.1)",
                      }}
                    >
                      <PhoneCall size={12} />
                      Review voice preview
                    </button>
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
