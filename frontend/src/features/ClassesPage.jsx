import { useEffect, useState } from "react";
import { api } from "../api/client";
import Notice from "../components/Notice";

const firstAcademicYear = `${new Date().getFullYear()}-${String(new Date().getFullYear() + 1).slice(-2)}`;

export default function ClassesPage({ user }) {
  const [classes, setClasses] = useState([]);
  const defaultScope = user.scopes.find((scope) => scope.scope_type === "department") || user.scopes[0];
  const [form, setForm] = useState({ course_name: "", year: "1", semester: "1", section: "", academic_year: firstAcademicYear, scope_id: defaultScope?.id || "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    try { setClasses(await api.classes()); }
    catch (requestError) { setError(requestError.message); }
  }

  useEffect(() => {
    let active = true;
    api.classes()
      .then((items) => { if (active) setClasses(items); })
      .catch((requestError) => { if (active) setError(requestError.message); });
    return () => { active = false; };
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await api.createClass({ ...form, scope_id: form.scope_id || null, year: Number(form.year), semester: Number(form.semester) });
      setForm({ ...form, course_name: "", section: "" });
      setSuccess("Class created.");
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-columns">
      <section className="content-card">
        <div className="section-heading"><div><h3>Classes and sections</h3><p>Organize students by their academic group.</p></div></div>
        <Notice>{error}</Notice>
        {!error && !classes.length && <p className="empty-state">No classes yet. Create your first class to start organizing students.</p>}
        <div className="class-grid">{classes.map((item) => (
          <article className="class-card" key={item.id}>
            <span className="class-tag">{item.section}</span>
            <h4>{item.course_name}</h4>
            <p>Year {item.year} · Semester {item.semester}</p>
            <span>{item.academic_year}</span>
          </article>
        ))}</div>
      </section>
      {user.permissions.includes("class.create") && <section className="content-card">
        <div className="section-heading"><div><h3>Create a class</h3><p>Keep academic records grouped in one place.</p></div></div>
        <Notice>{error}</Notice>
        <Notice tone="success">{success}</Notice>
        <form className="stack-form" onSubmit={submit}>
          <label>Course or department<input required maxLength={150} value={form.course_name} onChange={(event) => setForm({ ...form, course_name: event.target.value })} placeholder="Computer Science" /></label>
          <label>Year<input type="number" min="1" max="10" required value={form.year} onChange={(event) => setForm({ ...form, year: event.target.value })} /></label>
          <label>Semester<input type="number" min="1" max="20" required value={form.semester} onChange={(event) => setForm({ ...form, semester: event.target.value })} /></label>
          <label>Section<input required maxLength={50} value={form.section} onChange={(event) => setForm({ ...form, section: event.target.value })} placeholder="CSE-A" /></label>
          <label>Academic year<input required maxLength={20} value={form.academic_year} onChange={(event) => setForm({ ...form, academic_year: event.target.value })} /></label>
          {user.scopes.length > 1 && <label>Department access<select required value={form.scope_id} onChange={(event) => setForm({ ...form, scope_id: event.target.value })}>{user.scopes.map((scope) => <option key={scope.id} value={scope.id}>{scope.scope_value}</option>)}</select></label>}
          <button className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Create class"}</button>
        </form>
      </section>}
    </div>
  );
}
