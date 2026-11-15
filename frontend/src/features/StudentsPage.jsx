import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import Notice from "../components/Notice";
import PageState from "../components/PageState";

const emptyForm = {
  student_code: "",
  roll_number: "",
  first_name: "",
  last_name: "",
  class_id: "",
  email: "",
  parent_name: "",
  parent_phone: "",
  relationship: "Guardian",
};

function downloadCsv(rows) {
  const columns = ["student_code", "roll_number", "first_name", "last_name", "class_id", "email"];
  const quote = (value) => {
    let text = String(value ?? "");
    if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  const contents = [columns.join(","), ...rows.map((row) => columns.map((key) => quote(row[key])).join(","))].join("\r\n");
  const url = URL.createObjectURL(new Blob([contents], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "students.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export default function StudentsPage({ user }) {
  const [students, setStudents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [studentRows, classRows] = await Promise.all([api.students(), api.classes()]);
      setStudents(studentRows);
      setClasses(classRows);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    Promise.all([api.students(), api.classes()])
      .then(([studentRows, classRows]) => {
        if (active) {
          setStudents(studentRows);
          setClasses(classRows);
        }
      })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return students.filter((student) =>
      `${student.student_code} ${student.roll_number} ${student.first_name} ${student.last_name || ""}`
        .toLowerCase().includes(query)
    );
  }, [students, search]);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await api.createStudent({ ...form, last_name: form.last_name || null, email: form.email || null });
      setForm(emptyForm);
      setSuccess("Student added.");
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-columns">
      {user.permissions.includes("student.create") && <section className="content-card">
        <div className="section-heading">
          <div><h3>Student directory</h3><p>{students.length} student records in your scope</p></div>
          <button className="button button-secondary" disabled={!students.length} onClick={() => downloadCsv(filtered)}>Export CSV</button>
        </div>
        <label className="search-field">Search students<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, student ID, or roll number" /></label>
        <Notice>{error}</Notice>
        <Notice tone="success">{success}</Notice>
        <PageState loading={loading}>
          {!error && <div className="table-scroll"><table><thead><tr><th>Student ID</th><th>Name</th><th>Roll number</th><th>Class</th><th>Email</th><th>Guardian</th><th>Phone</th></tr></thead>
            <tbody>{filtered.map((student) => (
              <tr key={student.id}>
                <td>{student.student_code}</td>
                <td>{student.first_name} {student.last_name || ""}</td>
                <td>{student.roll_number}</td>
                <td>{classes.find((item) => item.id === student.class_id)?.section || "—"}</td>
                <td>{student.email || "—"}</td>
                <td>{student.parent_name || "—"}</td>
                <td><code>{student.parent_phone || "—"}</code></td>
              </tr>
            ))}</tbody></table>
            {!filtered.length && <p className="empty-state">{students.length ? "No students match your search." : "No student records yet. Add a class, then add students here."}</p>}
          </div>}
        </PageState>
      </section>}
      <section className="content-card">
        <div className="section-heading"><div><h3>Add a student</h3><p>Student records are saved by the backend.</p></div></div>
        {!classes.length && !loading && <Notice tone="info">Create a class first on the Classes page.</Notice>}
        <form className="stack-form" onSubmit={submit}>
          <label>Student ID<input required maxLength={100} value={form.student_code} onChange={(event) => setForm({ ...form, student_code: event.target.value })} /></label>
          <label>Roll number<input required maxLength={100} value={form.roll_number} onChange={(event) => setForm({ ...form, roll_number: event.target.value })} /></label>
          <label>First name<input required maxLength={100} value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></label>
          <label>Last name<input maxLength={100} value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></label>
          <label>Class<select required value={form.class_id} onChange={(event) => setForm({ ...form, class_id: event.target.value })}><option value="">Choose a class</option>{classes.map((item) => <option value={item.id} key={item.id}>{item.course_name} · {item.section} · Year {item.year}</option>)}</select></label>
          <label>Email (optional)<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
          <label>Parent / guardian name (optional)<input maxLength={200} value={form.parent_name} onChange={(event) => setForm({ ...form, parent_name: event.target.value })} /></label>
          <label>Parent / guardian phone (optional)<input type="tel" maxLength={30} value={form.parent_phone} onChange={(event) => setForm({ ...form, parent_phone: event.target.value })} /></label>
          <label>Relationship<select value={form.relationship} onChange={(event) => setForm({ ...form, relationship: event.target.value })}><option>Guardian</option><option>Mother</option><option>Father</option><option>Other</option></select></label>
          <button className="button button-primary" disabled={saving || !classes.length}>{saving ? "Saving…" : "Add student"}</button>
        </form>
      </section>
    </div>
  );
}
