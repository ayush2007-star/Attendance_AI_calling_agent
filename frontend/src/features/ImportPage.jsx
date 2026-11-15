import { useEffect, useState } from "react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function ImportPage({ user }) {
  const [classes, setClasses] = useState([]);
  const [studentFile, setStudentFile] = useState(null);
  const [studentClassId, setStudentClassId] = useState("");
  const [studentResult, setStudentResult] = useState(null);
  const [studentError, setStudentError] = useState("");
  const [studentBusy, setStudentBusy] = useState(false);
  const [file, setFile] = useState(null);
  const [classId, setClassId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitStudents(event) {
    event.preventDefault();
    setStudentError("");
    setStudentResult(null);
    if (!studentFile || !studentClassId) {
      setStudentError("Choose a class and student file first.");
      return;
    }
    if (studentFile.size > 10 * 1024 * 1024) {
      setStudentError("The file is larger than the 10 MB limit.");
      return;
    }
    const body = new FormData();
    body.append("file", studentFile);
    body.append("class_id", studentClassId);
    setStudentBusy(true);
    try {
      setStudentResult(await api.importStudents(body));
    } catch (requestError) {
      setStudentError(requestError.message);
    } finally {
      setStudentBusy(false);
    }
  }

  useEffect(() => {
    api.classes().then(setClasses).catch((requestError) => setError(requestError.message));
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    if (!file) {
      setError("Choose an attendance file first.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("The file is larger than the 10 MB limit.");
      return;
    }
    const body = new FormData();
    body.append("file", file);
    body.append("attendance_date", date);
    if (classId) body.append("class_id", classId);
    setBusy(true);
    try {
      setResult(await api.importAttendance(body));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 20, maxWidth: 820 }}>
    {user.permissions.includes("student.create") && <section className="content-card">
      <div className="section-heading"><div><h3>1. Import student and guardian records</h3><p>Save student IDs, roll numbers, and optional primary guardian contacts before attendance imports.</p></div><span className="file-limit">10 MB max</span></div>
      <p className="call-safety-note">CSV, XLS, or XLSX. Required columns: Roll Number and Name (or First Name). Optional: Student ID, Last Name, Parent Name, Parent Phone, Relationship. If Student ID is omitted, one is generated from this class and roll number. Existing students are not overwritten.</p>
      <Notice>{studentError}</Notice>
      {studentResult && <Notice tone="success">Saved {studentResult.created_rows} of {studentResult.total_rows} rows. {studentResult.duplicate_rows} duplicate and {studentResult.invalid_rows} invalid rows were skipped.</Notice>}
      {studentResult?.errors?.length > 0 && <ul className="muted">{studentResult.errors.slice(0, 8).map((message) => <li key={message}>{message}</li>)}</ul>}
      <form className="stack-form import-form" onSubmit={submitStudents}>
        <label>Class for these students<select required value={studentClassId} onChange={(event) => setStudentClassId(event.target.value)}><option value="">Choose a class</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.course_name} · {item.section} · Year {item.year}</option>)}</select></label>
        <label>Student master file<input required type="file" accept=".xlsx,.xls,.csv" onChange={(event) => setStudentFile(event.target.files?.[0] || null)} /></label>
        <button className="button button-primary" disabled={studentBusy || !classes.length}>{studentBusy ? "Validating and saving…" : "Import student records"}</button>
      </form>
    </section>}
    <section className="content-card narrow-card">
      <div className="section-heading"><div><h3>Import attendance</h3><p>Import date-wise attendance for enrolled students. Parent contacts should be saved in the student directory first.</p></div><span className="file-limit">10 MB max</span></div>
      <p className="call-safety-note">2. After saving student and guardian details, upload their date-wise attendance.</p>
      <p className="call-safety-note">Supported formats: XLSX, XLS, CSV, PDF tables, and DOCX tables. Include a Roll Number (or Student ID), Name, and date columns such as “03 Aug” or “2026-08-27”. The import matches saved roll numbers within the selected class.</p>
      <Notice>{error}</Notice>
      {result && <Notice tone="success">Import {result.status.toLowerCase()}: {result.valid_rows} valid, {result.invalid_rows} invalid, {result.duplicate_rows} duplicate rows.</Notice>}
      <form className="stack-form import-form" onSubmit={submit}>
        <label>Attendance date<input type="date" required value={date} onChange={(event) => setDate(event.target.value)} /></label>
        <label>Class or section<select value={classId} onChange={(event) => setClassId(event.target.value)}><option value="">Institution-wide (administrator only)</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.course_name} · {item.section} · Year {item.year}</option>)}</select></label>
        <label>Attendance file<input required type="file" accept=".xlsx,.xls,.csv,.pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
        <button className="button button-primary" disabled={busy}>{busy ? "Validating and importing…" : "Validate and import"}</button>
      </form>
      <p className="muted">The API applies your account's permissions and class scope. If access is denied, ask an administrator to check your role.</p>
    </section>
    </div>
  );
}
