import { useEffect, useState } from "react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function DepartmentsPage({ user, onUserUpdate }) {
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState(user.scopes);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function reload() {
    const [scopeList, currentUser] = await Promise.all([api.scopes(), api.currentUser()]);
    setScopes(scopeList);
    onUserUpdate(currentUser);
  }

  useEffect(() => {
    let active = true;
    api.scopes()
      .then((items) => { if (active) setScopes(items); })
      .catch((requestError) => { if (active) setError(requestError.message); });
    return () => { active = false; };
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await api.createScope({ scope_type: "department", scope_value: name });
      setName("");
      setSuccess("Department added. It can now be assigned to an HOD or teacher.");
      await reload();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-columns">
      <section className="content-card">
        <div className="section-heading"><div><h3>College departments</h3><p>Each department is an access boundary for its HOD and teachers.</p></div></div>
        <Notice>{error}</Notice>
        {!scopes.length && !error && <p className="empty-state">Create the first department to set up college access.</p>}
        <div className="class-grid">{scopes.map((scope) => (
          <article className="class-card" key={scope.id}><span className="class-tag">{scope.scope_type === "college" ? "COLLEGE" : "DEPARTMENT"}</span><h4>{scope.scope_value}</h4><p>Access scope</p></article>
        ))}</div>
      </section>
      <section className="content-card">
        <div className="section-heading"><div><h3>Add department</h3><p>Only the college Director can create departments.</p></div></div>
        <Notice tone="success">{success}</Notice>
        <form className="stack-form" onSubmit={submit}>
          <label>Department name<input required minLength={2} maxLength={150} value={name} onChange={(event) => setName(event.target.value)} placeholder="Computer Science" /></label>
          <button className="button button-primary" disabled={busy}>{busy ? "Saving…" : "Create department"}</button>
        </form>
      </section>
    </div>
  );
}
