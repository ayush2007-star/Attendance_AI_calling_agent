import { useEffect, useState } from "react";
import {
  UserPlus,
  KeyRound,
  Check,
  Copy,
  Briefcase,
  GraduationCap,
  User,
  ShieldCheck,
  Search,
  CheckCircle2,
} from "lucide-react";
import { api } from "../api/client";
import Notice from "../components/Notice";

const roleTitles = {
  SUPER_ADMIN: { label: "Director (Super Admin)", badgeClass: "director", icon: GraduationCap },
  ADMIN: { label: "HOD (Admin)", badgeClass: "admin", icon: Briefcase },
  STAFF: { label: "Teacher (Staff)", badgeClass: "staff", icon: User },
};

export default function PeoplePage({ user }) {
  const allowedRoles = user.role === "SUPER_ADMIN" ? ["ADMIN", "STAFF"] : ["STAFF"];
  const assignableScopes = user.scopes.filter((scope) => scope.scope_type === "department");
  const [people, setPeople] = useState([]);
  const [form, setForm] = useState({
    username: "",
    email: "",
    full_name: "",
    role: allowedRoles[0],
    scope_ids: assignableScopes.length > 0 ? [assignableScopes[0].id] : [],
    password: "",
  });
  const [search, setSearch] = useState("");
  const [credential, setCredential] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function loadPeople() {
    try {
      setPeople(await api.users());
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  useEffect(() => {
    let active = true;
    api.users()
      .then((items) => {
        if (active) setPeople(items);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, []);

  function toggleScope(scopeId) {
    setForm((current) => ({
      ...current,
      scope_ids: current.scope_ids.includes(scopeId)
        ? current.scope_ids.filter((id) => id !== scopeId)
        : [...current.scope_ids, scopeId],
    }));
  }

  async function createPerson(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setCredential(null);
    try {
      const payload = { ...form };
      if (!payload.password || !payload.password.trim()) {
        delete payload.password;
      }
      const created = await api.createUser(payload);
      setCredential(created);
      setForm({
        ...form,
        username: "",
        email: "",
        full_name: "",
        password: "",
      });
      await loadPeople();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(person) {
    setError("");
    try {
      const updated = await api.setUserActive(person.id, !person.is_active);
      setPeople((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function resetPassword(person) {
    setError("");
    setCredential(null);
    const customPass = window.prompt(
      `Enter new password for ${person.full_name} (min 6 characters, or leave blank to auto-generate):`,
      ""
    );
    try {
      const res = await api.resetUserPassword(person.id, customPass || undefined);
      setCredential(res);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function copyTemporaryPassword() {
    try {
      await navigator.clipboard.writeText(credential.temporary_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Clipboard access unavailable.");
    }
  }

  const filteredPeople = people.filter(
    (p) =>
      p.full_name.toLowerCase().includes(search.toLowerCase()) ||
      p.email.toLowerCase().includes(search.toLowerCase()) ||
      p.username.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* Header Banner */}
      <div className="bento-card glow-cyan" style={{ padding: 22 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="brand-hologram-cube" style={{ width: 44, height: 44, borderRadius: 12 }}>
              <ShieldCheck size={24} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "#fff" }}>
                People & Role Access Hierarchy · 2026
              </h2>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "#94a3b8" }}>
                {user.role === "SUPER_ADMIN"
                  ? "Director View: Full institutional access to add Department HODs and Teachers across all departments"
                  : "HOD View: Department-level access to add and manage Teachers in your authorized department"}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="role-clearance-pill director" style={{ fontSize: 10 }}>
              RBAC Policy: Strict Scoped Delegation
            </span>
          </div>
        </div>
      </div>

      <Notice>{error}</Notice>

      {/* Credential Notification Banner */}
      {credential && (
        <div
          style={{
            padding: 16,
            borderRadius: 12,
            background: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div>
            <strong style={{ color: "#34d399", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
              <CheckCircle2 size={16} /> Credentials Ready for {credential.full_name} ({credential.email})
            </strong>
            <p style={{ margin: "4px 0 0", fontSize: 11, color: "#cbd5e1" }}>
              Password: <code style={{ background: "rgba(0,0,0,0.4)", padding: "2px 8px", borderRadius: 4, color: "#fbbf24", fontFamily: "monospace", fontSize: 13 }}>{credential.temporary_password}</code>
            </p>
          </div>
          <button
            onClick={copyTemporaryPassword}
            className="btn-quantum btn-quantum-glass"
            style={{ padding: "6px 14px", fontSize: 11 }}
          >
            {copied ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
            {copied ? "Copied!" : "Copy Password"}
          </button>
        </div>
      )}

      {/* Main Grid: Left Roster, Right Add Form */}
      <div className="bento-grid">
        {/* Roster Column */}
        <div className="bento-card col-span-8" style={{ padding: 22, gridColumn: "span 8" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 750, color: "#fff" }}>
              Active Authorized Personnel ({filteredPeople.length})
            </h3>

            <div style={{ position: "relative" }}>
              <input
                type="text"
                placeholder="Search staff or email…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{
                  background: "rgba(15, 23, 42, 0.9)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "#fff",
                  borderRadius: 8,
                  padding: "6px 12px 6px 30px",
                  fontSize: 12,
                  width: 210,
                }}
              />
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table className="terminal-roster-table">
              <thead>
                <tr>
                  <th>Identity & Role</th>
                  <th>Contact Email</th>
                  <th>Department Scope</th>
                  <th>Status</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPeople.map((person) => {
                  const roleConfig = roleTitles[person.role] || { label: person.role, badgeClass: "staff", icon: User };
                  const Icon = roleConfig.icon;
                  const isSelf = person.id === user.id;

                  return (
                    <tr key={person.id} className="terminal-roster-row">
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <div
                            style={{
                              width: 34,
                              height: 34,
                              borderRadius: 10,
                              background: "rgba(255, 255, 255, 0.05)",
                              color: "#fff",
                              display: "grid",
                              placeItems: "center",
                            }}
                          >
                            <Icon size={16} />
                          </div>
                          <div>
                            <div style={{ fontWeight: 700, color: "#fff", fontSize: 13 }}>
                              {person.full_name} {isSelf && <span style={{ color: "#38bdf8", fontSize: 10 }}>(You)</span>}
                            </div>
                            <span className={`role-clearance-pill ${roleConfig.badgeClass}`} style={{ fontSize: 9, padding: "1px 6px", marginTop: 2 }}>
                              {roleConfig.label}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td style={{ color: "#cbd5e1", fontSize: 12, fontFamily: "monospace" }}>
                        {person.email}
                      </td>

                      <td>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                          {person.scopes?.length > 0 ? (
                            person.scopes.map((s) => (
                              <span
                                key={s.id}
                                style={{
                                  fontSize: 10,
                                  padding: "2px 6px",
                                  borderRadius: 4,
                                  background: "rgba(99, 102, 241, 0.12)",
                                  color: "#a5b4fc",
                                  border: "1px solid rgba(99, 102, 241, 0.2)",
                                }}
                              >
                                {s.scope_value}
                              </span>
                            ))
                          ) : (
                            <span style={{ fontSize: 11, color: "#64748b" }}>Global Scope</span>
                          )}
                        </div>
                      </td>

                      <td>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: 6,
                            background: person.is_active ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                            color: person.is_active ? "#34d399" : "#f87171",
                          }}
                        >
                          {person.is_active ? "Active" : "Deactivated"}
                        </span>
                      </td>

                      <td style={{ textAlign: "right" }}>
                        {!isSelf && (
                          <div style={{ display: "inline-flex", gap: 6 }}>
                            <button
                              onClick={() => resetPassword(person)}
                              className="btn-quantum btn-quantum-glass"
                              style={{ padding: "4px 8px", fontSize: 10 }}
                              title="Reset password"
                            >
                              <KeyRound size={12} /> Reset Pass
                            </button>
                            <button
                              onClick={() => toggleActive(person)}
                              className="btn-quantum btn-quantum-glass"
                              style={{
                                padding: "4px 8px",
                                fontSize: 10,
                                color: person.is_active ? "#f87171" : "#34d399",
                              }}
                            >
                              {person.is_active ? "Deactivate" : "Activate"}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Add Person Form Column */}
        <div className="bento-card col-span-4" style={{ padding: 22, gridColumn: "span 4" }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 750, color: "#fff", display: "flex", alignItems: "center", gap: 8 }}>
            <UserPlus size={18} color="#38bdf8" />
            {user.role === "SUPER_ADMIN" ? "Add HOD or Teacher" : "Add Department Teacher"}
          </h3>
          <p style={{ margin: "0 0 16px", fontSize: 11, color: "#94a3b8" }}>
            Create an authenticated institutional account with departmental boundaries
          </p>

          <form onSubmit={createPerson} className="stack-form">
            <label style={{ color: "#cbd5e1", fontSize: 11 }}>
              Full Name
              <input
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="e.g. Dr. Rajesh Kumar"
                style={{ background: "rgba(15, 23, 42, 0.8)", borderColor: "rgba(255, 255, 255, 0.12)", color: "#fff" }}
              />
            </label>

            <label style={{ color: "#cbd5e1", fontSize: 11 }}>
              Username
              <input
                required
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="e.g. rajesh_hod"
                style={{ background: "rgba(15, 23, 42, 0.8)", borderColor: "rgba(255, 255, 255, 0.12)", color: "#fff" }}
              />
            </label>

            <label style={{ color: "#cbd5e1", fontSize: 11 }}>
              Official Email Address
              <input
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="e.g. rajesh@college.edu"
                style={{ background: "rgba(15, 23, 42, 0.8)", borderColor: "rgba(255, 255, 255, 0.12)", color: "#fff" }}
              />
            </label>

            <label style={{ color: "#cbd5e1", fontSize: 11 }}>
              Assigned Role
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                style={{ background: "rgba(15, 23, 42, 0.8)", borderColor: "rgba(255, 255, 255, 0.12)", color: "#fff" }}
              >
                {allowedRoles.map((r) => (
                  <option key={r} value={r}>
                    {roleTitles[r]?.label || r}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ color: "#cbd5e1", fontSize: 11 }}>
              Initial Password (Optional)
              <input
                type="text"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Min 6 chars (leave blank to auto-generate)"
                style={{ background: "rgba(15, 23, 42, 0.8)", borderColor: "rgba(255, 255, 255, 0.12)", color: "#fff" }}
              />
            </label>

            <div>
              <span style={{ fontSize: 11, color: "#cbd5e1", fontWeight: 650, display: "block", marginBottom: 6 }}>
                Authorized Department Scope
              </span>
              <div style={{ display: "grid", gap: 6 }}>
                {assignableScopes.map((scope) => (
                  <label
                    key={scope.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      fontSize: 11,
                      color: "#cbd5e1",
                      background: "rgba(255, 255, 255, 0.03)",
                      padding: "6px 10px",
                      borderRadius: 6,
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={form.scope_ids.includes(scope.id)}
                      onChange={() => toggleScope(scope.id)}
                    />
                    <span>{scope.scope_value}</span>
                  </label>
                ))}
              </div>
            </div>

            <button
              className="btn-quantum btn-quantum-primary"
              style={{ width: "100%", padding: 11, marginTop: 8 }}
              disabled={busy}
            >
              {busy ? "Authorizing…" : "Authorize & Register Account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
