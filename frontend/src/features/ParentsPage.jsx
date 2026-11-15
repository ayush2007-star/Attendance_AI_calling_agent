import { useCallback, useEffect, useState } from "react";
import { Edit2, Plus, RefreshCw, Search, Shield, X } from "lucide-react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function ParentsPage({ user }) {
  const [parents, setParents] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busyId, setBusyId] = useState("");

  // Edit contact modal / state
  const [editingParent, setEditingParent] = useState(null);
  const [editForm, setEditForm] = useState({
    name: "",
    primary_phone: "",
    alternate_phone: "",
    preferred_language: "hi-IN",
    call_consent: true,
  });

  // New guardian modal / form
  const [showAddModal, setShowAddModal] = useState(false);
  const [newGuardianForm, setNewGuardianForm] = useState({
    name: "",
    primary_phone: "",
    alternate_phone: "",
    preferred_language: "hi-IN",
    call_consent: true,
  });

  const loadParents = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.parents({ search: search.trim() || undefined });
      setParents(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    let active = true;
    api.parents({ search: search.trim() || undefined })
      .then((data) => {
        if (active) setParents(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => { active = false; };
  }, [search]);

  async function toggleConsent(parent) {
    setBusyId(parent.id);
    setError("");
    setSuccess("");
    const newConsent = !parent.call_consent;
    try {
      await api.updateParent(parent.id, {
        call_consent: newConsent,
        call_opt_out: !newConsent,
      });
      setSuccess(`Updated call consent for ${parent.name} to ${newConsent ? "Authorized" : "Revoked"}.`);
      await loadParents();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId("");
    }
  }

  function startEdit(parent) {
    setEditingParent(parent);
    setEditForm({
      name: parent.name,
      primary_phone: parent.primary_phone,
      alternate_phone: parent.alternate_phone || "",
      preferred_language: parent.preferred_language || "hi-IN",
      call_consent: Boolean(parent.call_consent),
    });
    setError("");
    setSuccess("");
  }

  async function handleSaveEdit(e) {
    e.preventDefault();
    if (!editingParent) return;
    setBusyId(editingParent.id);
    setError("");
    setSuccess("");
    try {
      await api.updateParent(editingParent.id, {
        name: editForm.name.trim(),
        primary_phone: editForm.primary_phone.trim(),
        alternate_phone: editForm.alternate_phone.trim() || null,
        preferred_language: editForm.preferred_language,
        call_consent: editForm.call_consent,
        call_opt_out: !editForm.call_consent,
      });
      setSuccess(`Updated contact details for ${editForm.name}.`);
      setEditingParent(null);
      await loadParents();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId("");
    }
  }

  async function handleCreateGuardian(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await api.createParent({
        name: newGuardianForm.name.trim(),
        primary_phone: newGuardianForm.primary_phone.trim(),
        alternate_phone: newGuardianForm.alternate_phone.trim() || null,
        preferred_language: newGuardianForm.preferred_language,
        call_consent: newGuardianForm.call_consent,
        call_opt_out: !newGuardianForm.call_consent,
      });
      setSuccess(`Successfully registered guardian ${newGuardianForm.name}.`);
      setShowAddModal(false);
      setNewGuardianForm({
        name: "",
        primary_phone: "",
        alternate_phone: "",
        preferred_language: "hi-IN",
        call_consent: true,
      });
      await loadParents();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section className="content-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 14 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <Shield size={20} className="text-cyan" />
              <h3 style={{ margin: 0 }}>Parent & Guardian Directory</h3>
            </div>
            <p className="call-safety-note" style={{ margin: 0 }}>
              Database-backed contact records and explicit call authorization. Live calling fails closed if contact authorization is absent or revoked.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", background: "#0f172a", border: "1px solid #334155", borderRadius: 6, padding: "4px 10px" }}>
              <Search size={14} className="text-muted" style={{ marginRight: 6 }} />
              <input
                type="text"
                placeholder="Search guardian or phone…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ background: "transparent", border: "none", color: "#f8fafc", outline: "none", fontSize: "0.85rem" }}
              />
            </div>
            {user.permissions.includes("student.create") && (
              <button className="button button-primary" onClick={() => setShowAddModal(true)} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Plus size={14} /> Add Guardian
              </button>
            )}
            <button className="button button-secondary" onClick={loadParents} disabled={loading}>
              <RefreshCw size={14} className={loading ? "spinning" : ""} />
            </button>
          </div>
        </div>
      </section>

      <Notice>{error}</Notice>
      {success && <Notice tone="success">{success}</Notice>}

      {/* Edit Parent Modal */}
      {editingParent && (
        <section className="content-card" style={{ border: "1px solid #0284c7", background: "rgba(15, 23, 42, 0.95)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h4 style={{ margin: 0 }}>Edit Guardian Contact & Consent</h4>
            <button className="button button-secondary" style={{ padding: "4px 8px" }} onClick={() => setEditingParent(null)}>
              <X size={14} />
            </button>
          </div>
          <form onSubmit={handleSaveEdit} className="stack-form">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
              <label>
                Guardian Name
                <input
                  type="text"
                  required
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                />
              </label>
              <label>
                Primary Phone (E.164 format, e.g. +91...)
                <input
                  type="tel"
                  required
                  placeholder="+91..."
                  value={editForm.primary_phone}
                  onChange={(e) => setEditForm({ ...editForm, primary_phone: e.target.value })}
                />
              </label>
              <label>
                Alternate Phone (optional)
                <input
                  type="tel"
                  placeholder="+91..."
                  value={editForm.alternate_phone}
                  onChange={(e) => setEditForm({ ...editForm, alternate_phone: e.target.value })}
                />
              </label>
              <label>
                Preferred Language
                <select
                  value={editForm.preferred_language}
                  onChange={(e) => setEditForm({ ...editForm, preferred_language: e.target.value })}
                >
                  <option value="hi-IN">Hindi (hi-IN)</option>
                  <option value="en-IN">English (en-IN)</option>
                </select>
              </label>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
              <input
                type="checkbox"
                id="editCallConsent"
                checked={editForm.call_consent}
                onChange={(e) => setEditForm({ ...editForm, call_consent: e.target.checked })}
              />
              <label htmlFor="editCallConsent" style={{ margin: 0, cursor: "pointer" }}>
                Explicit Call Consent Granted (Allows telephony outreach for attendance absence)
              </label>
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
              <button type="submit" className="button button-primary" disabled={busyId === editingParent.id}>
                {busyId === editingParent.id ? "Saving…" : "Save Changes"}
              </button>
              <button type="button" className="button button-secondary" onClick={() => setEditingParent(null)}>
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Add Guardian Modal */}
      {showAddModal && (
        <section className="content-card" style={{ border: "1px solid #10b981", background: "rgba(15, 23, 42, 0.95)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h4 style={{ margin: 0 }}>Register New Guardian Contact</h4>
            <button className="button button-secondary" style={{ padding: "4px 8px" }} onClick={() => setShowAddModal(false)}>
              <X size={14} />
            </button>
          </div>
          <form onSubmit={handleCreateGuardian} className="stack-form">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
              <label>
                Guardian Name
                <input
                  type="text"
                  required
                  placeholder="e.g. Rajesh Kumar"
                  value={newGuardianForm.name}
                  onChange={(e) => setNewGuardianForm({ ...newGuardianForm, name: e.target.value })}
                />
              </label>
              <label>
                Primary Phone (E.164 format, e.g. +91...)
                <input
                  type="tel"
                  required
                  placeholder="+91..."
                  value={newGuardianForm.primary_phone}
                  onChange={(e) => setNewGuardianForm({ ...newGuardianForm, primary_phone: e.target.value })}
                />
              </label>
              <label>
                Alternate Phone (optional)
                <input
                  type="tel"
                  placeholder="+91..."
                  value={newGuardianForm.alternate_phone}
                  onChange={(e) => setNewGuardianForm({ ...newGuardianForm, alternate_phone: e.target.value })}
                />
              </label>
              <label>
                Preferred Language
                <select
                  value={newGuardianForm.preferred_language}
                  onChange={(e) => setNewGuardianForm({ ...newGuardianForm, preferred_language: e.target.value })}
                >
                  <option value="hi-IN">Hindi (hi-IN)</option>
                  <option value="en-IN">English (en-IN)</option>
                </select>
              </label>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
              <input
                type="checkbox"
                id="newCallConsent"
                checked={newGuardianForm.call_consent}
                onChange={(e) => setNewGuardianForm({ ...newGuardianForm, call_consent: e.target.checked })}
              />
              <label htmlFor="newCallConsent" style={{ margin: 0, cursor: "pointer" }}>
                Explicit Call Consent Granted (Allows telephony outreach for attendance absence)
              </label>
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
              <button type="submit" className="button button-primary">
                Register Guardian
              </button>
              <button type="button" className="button button-secondary" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="content-card">
        {loading ? (
          <p className="empty-state">Loading parents…</p>
        ) : !parents.length ? (
          <p className="empty-state">No parent or guardian records found. Import students with parent contacts in Batch Imports or click Add Guardian.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Guardian Name</th>
                  <th>Primary Phone</th>
                  <th>Alternate Phone</th>
                  <th>Language</th>
                  <th>Call Consent</th>
                  <th>Opt-Out Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {parents.map((p) => {
                  const isAuthorized = p.call_consent && !p.call_opt_out;
                  return (
                    <tr key={p.id}>
                      <td><strong>{p.name}</strong></td>
                      <td><code>{p.primary_phone}</code></td>
                      <td><code>{p.alternate_phone || "—"}</code></td>
                      <td>{p.preferred_language || "hi-IN"}</td>
                      <td>
                        <span className={`badge ${p.call_consent ? "badge-emerald" : "badge-rose"}`} style={{ fontSize: "0.75rem", padding: "2px 6px" }}>
                          {p.call_consent ? "Granted" : "Denied"}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${p.call_opt_out ? "badge-rose" : "badge-emerald"}`} style={{ fontSize: "0.75rem", padding: "2px 6px" }}>
                          {p.call_opt_out ? "Opted Out" : "Enrolled"}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          {user.permissions.includes("student.manage") && (
                            <>
                              <button
                                className="button button-secondary"
                                style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                                disabled={busyId === p.id}
                                onClick={() => toggleConsent(p)}
                              >
                                {isAuthorized ? "Revoke Consent" : "Grant Authorization"}
                              </button>
                              <button
                                className="button button-secondary"
                                style={{ padding: "3px 8px", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: 4 }}
                                onClick={() => startEdit(p)}
                              >
                                <Edit2 size={12} /> Edit
                              </button>
                            </>
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
