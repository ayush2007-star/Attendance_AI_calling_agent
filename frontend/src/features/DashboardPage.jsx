import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Brain,
  Calendar,
  Megaphone,
  PhoneCall,
  Upload,
  Users,
} from "lucide-react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function DashboardPage({ user, onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [mlMetrics, setMlMetrics] = useState(null);
  const [priorityStudents, setPriorityStudents] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.allSettled([api.dashboard(), api.mlRiskAnalysis()])
      .then(([dashboardResult, mlResult]) => {
        if (!active) return;
        const failures = [];
        if (dashboardResult.status === "fulfilled") {
          setSummary(dashboardResult.value);
        } else {
          failures.push(dashboardResult.reason.message);
        }
        if (mlResult.status === "fulfilled") {
          setMlMetrics(mlResult.value.metrics);
          setPriorityStudents(
            mlResult.value.students
              .filter((student) => student.risk_tier === "CRITICAL" || student.risk_tier === "ELEVATED")
              .slice(0, 5),
          );
        } else {
          failures.push(mlResult.reason.message);
        }
        setError(failures.join(" "));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const isDirector = user?.role === "SUPER_ADMIN";
  const isHOD = user?.role === "ADMIN";
  const roleTitle = isDirector ? "Director" : isHOD ? "Head of Department" : "Staff";
  const quickActions = [
    { permission: "attendance.create", page: "terminal", label: "Take attendance", icon: Calendar },
    { permission: "student.read", page: "students", label: "Student directory", icon: Users },
    { permission: "student.create", page: "imports", label: "Import student data", icon: Upload },
    { permission: "attendance.import", page: "imports", label: "Import attendance", icon: Upload },
    { permission: "campaign.create", page: "campaigns", label: "Review absent students", icon: Megaphone },
    { permission: "reports.read", page: "ml_risk", label: "Attendance risk review", icon: Brain },
  ].filter((action) => user?.permissions?.includes(action.permission));

  const statCards = [
    {
      label: "Students in scope",
      value: summary?.students ?? "—",
      detail: "Active academic records",
      icon: Users,
    },
    {
      label: "Average attendance",
      value: mlMetrics?.average_attendance == null ? "—" : `${mlMetrics.average_attendance}%`,
      detail: `${mlMetrics?.students_with_attendance ?? 0} students with recorded attendance`,
      icon: Calendar,
    },
    {
      label: "Critical risk indicators",
      value: mlMetrics?.critical_risk_count ?? "—",
      detail: "Advisory; verify the source attendance",
      icon: AlertTriangle,
    },
    {
      label: "Pending follow-ups",
      value: summary?.pending_followups ?? "—",
      detail: `${summary?.due_followups ?? 0} due · ${summary?.scheduled_followups ?? 0} scheduled`,
      icon: PhoneCall,
    },
  ];

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section className="hero-executive-banner">
        <div className="hero-meta">
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span className={`role-clearance-pill ${isDirector ? "director" : isHOD ? "admin" : "staff"}`}>
              {roleTitle}
            </span>
            <span style={{ fontSize: 11, color: "#94a3b8" }}>
              Scope: {user?.scopes?.map((scope) => scope.scope_value).join(", ") || "Institution"}
            </span>
          </div>
          <h1 style={{ color: "#fff" }}>Welcome back, {user?.full_name || user?.username}</h1>
          <p>
            {isDirector
              ? "Institution-wide student, attendance, and follow-up overview."
              : isHOD
                ? "Department-scoped student and attendance overview."
                : "Review your class records and update attendance."}
          </p>
        </div>
      </section>

      <Notice>{error}</Notice>

      <section className="bento-grid">
        {statCards.map(({ label, value, detail, icon: Icon }) => (
          <article className="bento-card kpi-tile" key={label}>
            <div className="kpi-header">
              <span>{label}</span>
              <div className="kpi-icon-badge cyan"><Icon size={18} /></div>
            </div>
            <div className="kpi-value">{loading ? "…" : value}</div>
            <div className="kpi-subtext">{detail}</div>
          </article>
        ))}
      </section>

      <div className="bento-grid">
        <section className="bento-card col-span-7" style={{ padding: 22, gridColumn: "span 7" }}>
          <div className="section-heading">
            <div>
              <h3>Students to review</h3>
              <p>Attendance-based indicators only; not a trained ML prediction or an automatic call.</p>
            </div>
            {user?.permissions?.includes("reports.read") && (
              <button className="button button-secondary" onClick={() => onNavigate?.("ml_risk")}>
                View risk review
              </button>
            )}
          </div>
          {loading ? <p className="page-state">Loading records…</p> : priorityStudents.length ? (
            <div className="table-scroll">
              <table>
                <thead><tr><th>Student</th><th>Class</th><th>Attendance</th><th>Indicator</th></tr></thead>
                <tbody>{priorityStudents.map((student) => (
                  <tr key={student.id}>
                    <td>{student.full_name} · #{student.roll_number}</td>
                    <td>{student.class_name}</td>
                    <td>{student.attendance_percentage == null ? "—" : `${student.attendance_percentage}%`}</td>
                    <td>{student.risk_tier}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : <p className="empty-state">No elevated indicators in your scope, or no attendance records have been imported.</p>}
        </section>

        <section className="bento-card col-span-5" style={{ padding: 22, gridColumn: "span 5" }}>
          <div className="section-heading">
            <div><h3>Quick actions</h3><p>Actions allowed for your role and assigned scope.</p></div>
          </div>
          <div style={{ display: "grid", gap: 9 }}>
            {quickActions.map(({ page, label, icon: Icon }) => (
              <button className="button button-secondary" key={`${page}-${label}`} onClick={() => onNavigate?.(page)} style={{ justifyContent: "flex-start", gap: 9 }}>
                <Icon size={15} /> {label}
              </button>
            ))}
          </div>
          <p className="call-safety-note" style={{ marginTop: 16 }}>
            Parent-call previews are demos. Live calling is not configured; verify contacts and review each absence before any outreach.
          </p>
        </section>
      </div>
    </div>
  );
}
