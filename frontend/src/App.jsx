import React, { useMemo, useState } from "react";
import {
  LayoutDashboard,
  Users,
  ClipboardCheck,
  Upload,
  Megaphone,
  Phone,
  PhoneCall,
  PhoneOff,
  MessageSquare,
  CheckSquare,
  BarChart3,
  UserCog,
  ShieldCheck,
  FileClock,
  Settings,
  Bell,
  BellRing,
  Search,
  ChevronDown,
  Plus,
  Eye,
  Pencil,
  ArrowLeft,
  Save,
  X,
  Activity,
  Clock3,
  CheckCircle2,
  UploadCloud,
  FileSpreadsheet,
  RefreshCw,
  Database,
  AlertTriangle,
  XCircle,
  Download,
  Play,
  Pause,
  Target,
  CalendarDays,
  Filter,
  MoreHorizontal,
  UserRound,
  User,
  Lock,
  History,
  SlidersHorizontal,
  Sparkles,
  Bot,
} from "lucide-react";

const initialStudents = [
  { id: "STU001", name: "Aarav Sharma", phone: "9876543210", branch: "CSE", year: "3rd Year", semester: "6th", attendance: 91, status: "Eligible" },
  { id: "STU002", name: "Ananya Singh", phone: "9876543211", branch: "CSE", year: "2nd Year", semester: "4th", attendance: 86, status: "Eligible" },
  { id: "STU003", name: "Rohan Verma", phone: "9876543212", branch: "AI/ML", year: "3rd Year", semester: "6th", attendance: 73, status: "Not Eligible" },
  { id: "STU004", name: "Priya Gupta", phone: "9876543213", branch: "ECE", year: "1st Year", semester: "2nd", attendance: 94, status: "Eligible" },
  { id: "STU005", name: "Aditya Mishra", phone: "9876543214", branch: "CSE", year: "2nd Year", semester: "4th", attendance: 68, status: "Not Eligible" },
  { id: "STU006", name: "Sneha Yadav", phone: "9876543215", branch: "AI/ML", year: "2nd Year", semester: "4th", attendance: 82, status: "Eligible" },
  { id: "STU007", name: "Kunal Patel", phone: "9876543216", branch: "ME", year: "3rd Year", semester: "6th", attendance: 77, status: "Eligible" },
  { id: "STU008", name: "Neha Agarwal", phone: "9876543217", branch: "CSE", year: "1st Year", semester: "2nd", attendance: 89, status: "Eligible" },
];

const menuSections = [
  {
    title: "MAIN",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "students", label: "Students", icon: Users },
      { id: "attendance", label: "Attendance", icon: ClipboardCheck },
      { id: "imports", label: "Imports", icon: Upload },
      { id: "campaigns", label: "Campaigns", icon: Megaphone },
    ],
  },
  {
    title: "COMMUNICATION",
    items: [
      { id: "calls", label: "Calls", icon: Phone },
      { id: "conversations", label: "Conversations", icon: MessageSquare },
      { id: "followups", label: "Follow-ups", icon: CheckSquare },
    ],
  },
  {
    title: "MANAGEMENT",
    items: [
      { id: "reports", label: "Reports", icon: BarChart3 },
      { id: "users", label: "Users", icon: UserCog },
      { id: "roles", label: "Roles & Scopes", icon: ShieldCheck },
      { id: "audit", label: "Audit Logs", icon: FileClock },
      { id: "settings", label: "Settings", icon: Settings },
    ],
  },
];

const navLabels = Object.fromEntries(
  menuSections.flatMap((section) => section.items.map((item) => [item.id, item.label]))
);

function initials(name = "") {
  return name
    .split(" ")
    .map((x) => x[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function statusClass(value = "") {
  const v = value.toLowerCase().replace(/\s+/g, "-");
  if (["eligible", "completed", "active", "success", "connected", "resolved"].includes(v)) return "status-pill success";
  if (["pending", "processing", "follow-up-required", "unanswered", "scheduled"].includes(v)) return "status-pill warning";
  if (["failed", "not-eligible", "inactive", "error"].includes(v)) return "status-pill danger";
  return "status-pill neutral";
}

function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, note, tone = "" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-top">
        <div className="stat-icon"><Icon size={20} /></div>
        {note && <span className="stat-note">{note}</span>}
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function SummaryCard({ label, value, icon: Icon }) {
  return (
    <div className="summary-card">
      <div className="summary-icon"><Icon size={18} /></div>
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ icon: Icon = Database, title = "No data found", text = "There is nothing to show here yet." }) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><Icon size={24} /></div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function FormInput({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="form-field">
      <span>{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </label>
  );
}

function FormSelect({ label, value, onChange, children }) {
  return (
    <label className="form-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {children}
      </select>
    </label>
  );
}

function App() {
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [students, setStudents] = useState(initialStudents);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentMode, setStudentMode] = useState(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const navigate = (page) => {
    setCurrentPage(page);
    setStudentMode(null);
    setSelectedStudent(null);
  };

  const openStudent = (student, mode = "details") => {
    setSelectedStudent(student);
    setStudentMode(mode);
    setCurrentPage("students");
  };

  const saveStudent = (data) => {
    setStudents((prev) => {
      const exists = prev.some((s) => s.id === data.id);
      return exists ? prev.map((s) => (s.id === data.id ? data : s)) : [...prev, data];
    });
    setStudentMode(null);
    setSelectedStudent(null);
  };

  const pageTitle = studentMode
    ? studentMode === "add"
      ? "Add Student"
      : studentMode === "edit"
      ? "Edit Student"
      : selectedStudent?.name || "Student Details"
    : navLabels[currentPage] || "Dashboard";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-logo"><Bot size={27} strokeWidth={2.2} /></div>
          <div className="brand-text">
            <div className="brand-name">Attendance AI Calling</div>
            <div className="brand-subtitle">Smart Attendance System</div>
          </div>
        </div>

        <div className="sidebar-menu">
          {menuSections.map((section) => (
            <div className="menu-section" key={section.title}>
              <div className="menu-section-title">{section.title}</div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const active =
                  currentPage === item.id ||
                  (item.id === "students" && currentPage === "students");
                return (
                  <button
                    key={item.id}
                    className={`sidebar-item ${active ? "active" : ""}`}
                    onClick={() => navigate(item.id)}
                  >
                    <Icon size={18} strokeWidth={2} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot"></span>
            <span>System Online</span>
          </div>
          <button className="sidebar-user" onClick={() => navigate("profile")}>
            <div className="user-avatar">SM</div>
            <div className="user-info">
              <strong>Shantanu Mishra</strong>
              <span>Administrator</span>
            </div>
            <ChevronDown size={15} />
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            <span>AttendAI</span>
            <span>/</span>
            <strong>{pageTitle}</strong>
          </div>
          <div className="topbar-right">
            <div className="notification-wrap">
              <button className="icon-button" onClick={() => setNotificationsOpen((v) => !v)}>
                <Bell size={20} />
                <span className="notification-dot"></span>
              </button>
              {notificationsOpen && (
                <div className="notification-popover">
                  <div className="popover-head"><strong>Notifications</strong><span>3 new</span></div>
                  <div className="notification-item"><BellRing size={17} /><div><strong>Import completed</strong><span>Attendance file processed successfully.</span></div></div>
                  <div className="notification-item"><PhoneOff size={17} /><div><strong>Call failed</strong><span>One call needs a retry.</span></div></div>
                  <div className="notification-item"><CheckCircle2 size={17} /><div><strong>Follow-up due</strong><span>2 follow-ups are pending.</span></div></div>
                </div>
              )}
            </div>
            <div className="top-user">
              <div className="top-avatar">SM</div>
              <div><strong>Shantanu Mishra</strong><span>Administrator</span></div>
              <ChevronDown size={16} />
            </div>
          </div>
        </header>

        <section className="page-content">
          {currentPage === "dashboard" && <Dashboard students={students} navigate={navigate} />}
          {currentPage === "students" && !studentMode && <StudentsPage students={students} openStudent={openStudent} navigate={navigate} />}
          {currentPage === "students" && studentMode === "details" && <StudentDetails student={selectedStudent} onBack={() => setStudentMode(null)} onEdit={() => setStudentMode("edit")} />}
          {currentPage === "students" && (studentMode === "add" || studentMode === "edit") && (
            <StudentForm student={selectedStudent} mode={studentMode} onBack={() => setStudentMode(null)} onSave={saveStudent} />
          )}
          {currentPage === "attendance" && <AttendancePage students={students} />}
          {currentPage === "imports" && <ImportsPage />}
          {currentPage === "campaigns" && <CampaignsPage students={students} />}
          {currentPage === "calls" && <CallsPage />}
          {currentPage === "conversations" && <ConversationsPage />}
          {currentPage === "followups" && <FollowUpsPage />}
          {currentPage === "reports" && <ReportsPage />}
          {currentPage === "users" && <UsersPage />}
          {currentPage === "roles" && <RolesPage />}
          {currentPage === "audit" && <AuditLogsPage />}
          {currentPage === "settings" && <SettingsPage />}
          {currentPage === "profile" && <ProfilePage />}
        </section>
      </main>
    </div>
  );
}

function Dashboard({ students, navigate }) {
  const eligible = students.filter((s) => s.attendance >= 75).length;
  return (
    <>
      <div className="welcome-banner">
        <div>
          <span className="eyebrow">SMART ATTENDANCE • AI CALLING</span>
          <h1>Good evening, Shantanu 👋</h1>
          <p>Monitor attendance, manage campaigns and track parent communication from one place.</p>
        </div>
        <div className="banner-orb"><Sparkles size={30} /></div>
      </div>

      <PageHeader title="Dashboard" subtitle="Overview of your attendance operations" />

      <div className="stats-grid">
        <StatCard icon={Users} label="Total Students" value={students.length} note="+4.2%" tone="blue" />
        <StatCard icon={Target} label="Eligible Students" value={eligible} note="75% threshold" tone="green" />
        <StatCard icon={Megaphone} label="Active Campaigns" value="3" note="2 running" tone="purple" />
        <StatCard icon={PhoneCall} label="Calls Completed" value="124" note="+18 today" tone="orange" />
      </div>

      <div className="dashboard-grid">
        <div className="card chart-card">
          <div className="card-head"><div><h3>Attendance Overview</h3><p>Average attendance by recent period</p></div><select><option>Current Month</option><option>Last Month</option></select></div>
          <div className="line-chart">
            <div className="chart-y"><span>100%</span><span>80%</span><span>60%</span><span>40%</span><span>20%</span></div>
            <div className="chart-area">
              <div className="grid-line"></div><div className="grid-line"></div><div className="grid-line"></div><div className="grid-line"></div><div className="grid-line"></div>
              <svg viewBox="0 0 700 250" preserveAspectRatio="none" className="chart-svg">
                <polyline points="0,125 90,112 180,130 270,92 360,105 450,76 540,84 630,58 700,70" fill="none" stroke="currentColor" strokeWidth="4" />
                <polygon points="0,125 90,112 180,130 270,92 360,105 450,76 540,84 630,58 700,70 700,250 0,250" fill="currentColor" opacity=".08" />
              </svg>
              <div className="chart-labels"><span>Aug 1</span><span>Aug 8</span><span>Aug 15</span><span>Aug 22</span><span>Aug 29</span></div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head"><div><h3>Campaign Performance</h3><p>This month</p></div><button className="text-button" onClick={() => navigate("campaigns")}>View all</button></div>
          <div className="performance-list">
            <div className="performance-row"><span>Low Attendance Alert</span><strong>86%</strong><div className="mini-progress"><i style={{ width: "86%" }} /></div></div>
            <div className="performance-row"><span>Parent Reminder</span><strong>72%</strong><div className="mini-progress"><i style={{ width: "72%" }} /></div></div>
            <div className="performance-row"><span>Exam Attendance</span><strong>94%</strong><div className="mini-progress"><i style={{ width: "94%" }} /></div></div>
          </div>
        </div>
      </div>

      <div className="three-grid">
        <div className="card">
          <div className="card-head"><div><h3>Current User Scope</h3><p>Access assigned to you</p></div><ShieldCheck size={19} /></div>
          <div className="scope-box"><span>Role</span><strong>Administrator</strong></div>
          <div className="scope-box"><span>Department</span><strong>Computer Science</strong></div>
          <div className="scope-box"><span>Branches</span><strong>CSE • AI/ML • ECE</strong></div>
        </div>

        <div className="card">
          <div className="card-head"><div><h3>Recent Activity</h3><p>Latest system actions</p></div><Activity size={19} /></div>
          <ActivityItem icon={UploadCloud} title="Attendance imported" time="10 min ago" />
          <ActivityItem icon={PhoneCall} title="Campaign call completed" time="28 min ago" />
          <ActivityItem icon={UserRound} title="Student record updated" time="1 hr ago" />
        </div>

        <div className="card">
          <div className="card-head"><div><h3>Quick Actions</h3><p>Common tasks</p></div></div>
          <div className="quick-actions">
            <button onClick={() => navigate("students")}><Users size={18} />Manage Students</button>
            <button onClick={() => navigate("imports")}><Upload size={18} />Import Attendance</button>
            <button onClick={() => navigate("campaigns")}><Megaphone size={18} />Create Campaign</button>
          </div>
        </div>
      </div>
    </>
  );
}

function ActivityItem({ icon: Icon, title, time }) {
  return <div className="activity-item"><div className="activity-icon"><Icon size={16} /></div><div><strong>{title}</strong><span>{time}</span></div></div>;
}

function StudentsPage({ students, openStudent, navigate }) {
  const [search, setSearch] = useState("");
  const [branch, setBranch] = useState("All");
  const filtered = useMemo(() => students.filter((s) => {
    const text = `${s.name} ${s.id} ${s.phone}`.toLowerCase();
    return text.includes(search.toLowerCase()) && (branch === "All" || s.branch === branch);
  }), [students, search, branch]);

  return (
    <>
      <PageHeader title="Students" subtitle="Manage student records and academic information" actions={<button className="primary-button" onClick={() => navigate("students-add")}><Plus size={17} />Add Student</button>} />
      <div className="card filter-card">
        <div className="search-box"><Search size={18} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by student ID, name or phone..." /></div>
        <select value={branch} onChange={(e) => setBranch(e.target.value)}><option>All</option><option>CSE</option><option>AI/ML</option><option>ECE</option><option>ME</option></select>
        <button className="secondary-button"><Filter size={17} />More Filters</button>
        <button className="secondary-button"><Download size={17} />Export</button>
      </div>
      <div className="card table-card">
        <div className="card-head"><div><h3>Student List</h3><p>{filtered.length} students found</p></div><button className="icon-button plain"><MoreHorizontal size={19} /></button></div>
        {filtered.length ? (
          <div className="table-wrap"><table><thead><tr><th>Student</th><th>Student ID</th><th>Branch</th><th>Year</th><th>Attendance</th><th>Status</th><th>Action</th></tr></thead><tbody>
            {filtered.map((s) => <tr key={s.id}><td><div className="student-cell"><div className="avatar">{initials(s.name)}</div><div><strong>{s.name}</strong><span>{s.phone}</span></div></div></td><td>{s.id}</td><td>{s.branch}</td><td>{s.year}</td><td><strong>{s.attendance}%</strong></td><td><span className={statusClass(s.status)}>{s.status}</span></td><td><div className="row-actions"><button onClick={() => openStudent(s, "details")}><Eye size={16} /></button><button onClick={() => openStudent(s, "edit")}><Pencil size={16} /></button></div></td></tr>)}
          </tbody></table></div>
        ) : <EmptyState icon={Users} title="No students found" text="Try changing your search or filters." />}
      </div>
    </>
  );
}

function StudentDetails({ student, onBack, onEdit }) {
  if (!student) return <EmptyState />;
  return (
    <>
      <PageHeader title="Student Details" subtitle={`Student ID: ${student.id}`} actions={<><button className="secondary-button" onClick={onBack}><ArrowLeft size={17} />Back</button><button className="primary-button" onClick={onEdit}><Pencil size={17} />Edit</button></>} />
      <div className="detail-hero card">
        <div className="large-avatar">{initials(student.name)}</div><div><h2>{student.name}</h2><p>{student.id} • {student.branch} • {student.year}</p><span className={statusClass(student.status)}>{student.status}</span></div>
      </div>
      <div className="two-grid">
        <div className="card"><div className="card-head"><h3>Basic Information</h3><User size={19} /></div><DetailRow label="Student ID" value={student.id} /><DetailRow label="Mobile" value={student.phone} /><DetailRow label="Branch" value={student.branch} /><DetailRow label="Year" value={student.year} /></div>
        <div className="card"><div className="card-head"><h3>Academic Record</h3><ClipboardCheck size={19} /></div><DetailRow label="Semester" value={student.semester} /><DetailRow label="Attendance" value={`${student.attendance}%`} /><DetailRow label="Threshold" value="75%" /><DetailRow label="Eligibility" value={student.status} /></div>
      </div>
      <div className="card"><div className="card-head"><h3>Academic History</h3><History size={19} /></div><div className="history-row"><span>2025–26 • {student.semester}</span><strong>{student.attendance}% attendance</strong><span className="status-pill neutral">Current</span></div><div className="history-row"><span>2024–25 • Previous Session</span><strong>88% attendance</strong><span className="status-pill neutral">Archived</span></div></div>
    </>
  );
}

function StudentForm({ student, mode, onBack, onSave }) {
  const [form, setForm] = useState(student || { id: `STU00${initialStudents.length + 1}`, name: "", phone: "", branch: "CSE", year: "1st Year", semester: "2nd", attendance: 0, status: "Not Eligible" });
  const set = (key, value) => setForm((p) => ({ ...p, [key]: value }));
  return (
    <>
      <PageHeader title={mode === "add" ? "Add Student" : "Edit Student"} subtitle="Enter student and academic information" actions={<button className="secondary-button" onClick={onBack}><ArrowLeft size={17} />Back</button>} />
      <div className="card form-card">
        <div className="form-grid">
          <FormInput label="Student ID" value={form.id} onChange={(v) => set("id", v)} />
          <FormInput label="Student Name" value={form.name} onChange={(v) => set("name", v)} />
          <FormInput label="Mobile Number" value={form.phone} onChange={(v) => set("phone", v)} />
          <FormSelect label="Branch" value={form.branch} onChange={(v) => set("branch", v)}><option>CSE</option><option>AI/ML</option><option>ECE</option><option>ME</option></FormSelect>
          <FormSelect label="Year" value={form.year} onChange={(v) => set("year", v)}><option>1st Year</option><option>2nd Year</option><option>3rd Year</option><option>4th Year</option></FormSelect>
          <FormSelect label="Semester" value={form.semester} onChange={(v) => set("semester", v)}><option>2nd</option><option>4th</option><option>6th</option><option>8th</option></FormSelect>
          <FormInput label="Attendance %" type="number" value={form.attendance} onChange={(v) => set("attendance", Number(v))} />
        </div>
        <div className="form-note"><AlertTriangle size={17} />Status will be calculated from the configured attendance threshold.</div>
        <div className="form-actions"><button className="secondary-button" onClick={onBack}><X size={17} />Cancel</button><button className="primary-button" onClick={() => onSave({ ...form, status: Number(form.attendance) >= 75 ? "Eligible" : "Not Eligible" })}><Save size={17} />Save Student</button></div>
      </div>
    </>
  );
}

function AttendancePage({ students }) {
  const [search, setSearch] = useState("");
  const [branch, setBranch] = useState("All");
  const [threshold, setThreshold] = useState(75);
  const filtered = students.filter((s) => `${s.name} ${s.id}`.toLowerCase().includes(search.toLowerCase()) && (branch === "All" || s.branch === branch));
  const eligible = students.filter((s) => s.attendance >= threshold).length;
  const low = students.length - eligible;
  return (
    <>
      <PageHeader title="Attendance" subtitle="Monitor attendance percentage and eligibility" actions={<button className="secondary-button"><Download size={17} />Export</button>} />
      <div className="card attendance-controls">
        <div className="search-box"><Search size={18} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search student..." /></div>
        <select value={branch} onChange={(e) => setBranch(e.target.value)}><option>All</option><option>CSE</option><option>AI/ML</option><option>ECE</option><option>ME</option></select>
        <label className="threshold-box"><span>Threshold</span><strong>{threshold}%</strong><input type="range" min="50" max="95" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} /></label>
      </div>
      <div className="summary-grid"><SummaryCard icon={Users} label="Total Students" value={students.length} /><SummaryCard icon={CheckCircle2} label="Eligible" value={eligible} /><SummaryCard icon={XCircle} label="Not Eligible" value={low} /><SummaryCard icon={Target} label="Threshold" value={`${threshold}%`} /></div>
      <div className="card table-card">
        <div className="card-head"><div><h3>Attendance Overview</h3><p>Current academic period</p></div><span className="period-chip">Current Semester</span></div>
        <div className="table-wrap"><table><thead><tr><th>Student</th><th>Student ID</th><th>Branch</th><th>Year</th><th>Attendance</th><th>Threshold</th><th>Status</th></tr></thead><tbody>
          {filtered.map((s) => { const ok = s.attendance >= threshold; return <tr key={s.id}><td><div className="student-cell"><div className="avatar">{initials(s.name)}</div><strong>{s.name}</strong></div></td><td>{s.id}</td><td>{s.branch}</td><td>{s.year}</td><td><div className="attendance-value"><strong>{s.attendance}%</strong><div className="mini-progress"><i style={{ width: `${Math.min(s.attendance, 100)}%` }} /></div></div></td><td>{threshold}%</td><td><span className={statusClass(ok ? "Eligible" : "Not Eligible")}>{ok ? "Eligible" : "Not Eligible"}</span></td></tr>; })}
        </tbody></table></div>
      </div>
    </>
  );
}

function ImportsPage() {
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [done, setDone] = useState(false);
  const startImport = () => { if (!file) return; setProcessing(true); setDone(false); setTimeout(() => { setProcessing(false); setDone(true); }, 1200); };
  return (
    <>
      <PageHeader title="Attendance Imports" subtitle="Upload and validate Excel attendance data" actions={<button className="secondary-button"><Download size={17} />Import History</button>} />
      <div className="two-grid">
        <div className="card upload-card">
          <div className="upload-icon"><FileSpreadsheet size={30} /></div><h3>Upload Attendance File</h3><p>Supported format: Excel (.xlsx, .xls)</p>
          <label className="dropzone"><UploadCloud size={28} /><strong>{file ? file.name : "Choose an Excel file"}</strong><span>{file ? "File selected" : "Click to browse from your computer"}</span><input type="file" accept=".xlsx,.xls" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label>
          <button className="primary-button full" onClick={startImport} disabled={!file || processing}>{processing ? <><RefreshCw size={17} className="spin" />Processing...</> : <><Upload size={17} />Start Import</>}</button>
          {done && <div className="success-box"><CheckCircle2 size={18} /><div><strong>Import completed</strong><span>186 valid rows processed successfully.</span></div></div>}
        </div>
        <div className="card">
          <div className="card-head"><div><h3>Import Summary</h3><p>Latest processed file</p></div><Database size={19} /></div>
          <div className="import-stat"><span>Total Rows</span><strong>200</strong></div><div className="import-stat"><span>Valid Rows</span><strong>186</strong></div><div className="import-stat"><span>Invalid Rows</span><strong>8</strong></div><div className="import-stat"><span>Duplicates</span><strong>6</strong></div>
        </div>
      </div>
      <div className="card table-card"><div className="card-head"><div><h3>Recent Imports</h3><p>Previous attendance files</p></div></div><div className="table-wrap"><table><thead><tr><th>File</th><th>Period</th><th>Uploaded By</th><th>Rows</th><th>Status</th><th>Date</th></tr></thead><tbody>
        <tr><td><strong>attendance_aug_2026.xlsx</strong></td><td>Aug 2026</td><td>Shantanu Mishra</td><td>200</td><td><span className="status-pill success">Completed</span></td><td>18 Sep 2026</td></tr>
        <tr><td><strong>attendance_jul_2026.xlsx</strong></td><td>Jul 2026</td><td>Admin</td><td>196</td><td><span className="status-pill warning">Partial Success</span></td><td>31 Aug 2026</td></tr>
      </tbody></table></div></div>
    </>
  );
}

function CampaignsPage({ students }) {
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState(null);
  if (showCreate) return <CreateCampaign students={students} onBack={() => setShowCreate(false)} onCreated={() => setShowCreate(false)} />;
  if (selected) return <CampaignDetails campaign={selected} onBack={() => setSelected(null)} />;
  const campaigns = [
    { id: 1, name: "Low Attendance Alert", period: "Aug 2026", scope: "CSE • AI/ML", threshold: "75%", targets: 42, completed: 36, failed: 3, status: "Active" },
    { id: 2, name: "Parent Reminder", period: "Aug 2026", scope: "All Branches", threshold: "80%", targets: 64, completed: 58, failed: 2, status: "Active" },
    { id: 3, name: "Exam Attendance", period: "Jul 2026", scope: "CSE", threshold: "70%", targets: 31, completed: 31, failed: 0, status: "Completed" },
  ];
  return (
    <>
      <PageHeader title="Campaigns" subtitle="Create and manage AI calling campaigns" actions={<button className="primary-button" onClick={() => setShowCreate(true)}><Plus size={17} />Create Campaign</button>} />
      <div className="stats-grid three-stats"><StatCard icon={Megaphone} label="Total Campaigns" value="12" note="This year" /><StatCard icon={Play} label="Active Campaigns" value="2" note="Running now" /><StatCard icon={CheckCircle2} label="Completed" value="9" note="This year" /></div>
      <div className="card table-card"><div className="card-head"><div><h3>Campaign List</h3><p>Attendance-based communication campaigns</p></div><div className="table-tools"><Search size={17} /><input placeholder="Search campaigns..." /></div></div><div className="table-wrap"><table><thead><tr><th>Campaign</th><th>Period</th><th>Scope</th><th>Threshold</th><th>Targets</th><th>Completed</th><th>Status</th><th></th></tr></thead><tbody>
        {campaigns.map((c) => <tr key={c.id}><td><strong>{c.name}</strong></td><td>{c.period}</td><td>{c.scope}</td><td>{c.threshold}</td><td>{c.targets}</td><td>{c.completed}/{c.targets}</td><td><span className={statusClass(c.status)}>{c.status}</span></td><td><button className="icon-button plain" onClick={() => setSelected(c)}><Eye size={17} /></button></td></tr>)}
      </tbody></table></div></div>
    </>
  );
}

function CreateCampaign({ students, onBack, onCreated }) {
  const [name, setName] = useState("");
  const [threshold, setThreshold] = useState("75");
  const [scope, setScope] = useState("All Branches");
  const eligible = students.filter((s) => s.attendance < Number(threshold) && (scope === "All Branches" || s.branch === scope));
  return (
    <>
      <PageHeader title="Create Campaign" subtitle="Configure an attendance-based AI calling campaign" actions={<button className="secondary-button" onClick={onBack}><ArrowLeft size={17} />Back</button>} />
      <div className="two-grid">
        <div className="card form-card">
          <div className="form-grid">
            <FormInput label="Campaign Name" value={name} onChange={setName} placeholder="e.g. Low Attendance Alert" />
            <FormSelect label="Attendance Period" value="Aug 2026" onChange={() => {}}><option>Aug 2026</option><option>Jul 2026</option></FormSelect>
            <FormSelect label="Academic Scope" value={scope} onChange={setScope}><option>All Branches</option><option>CSE</option><option>AI/ML</option><option>ECE</option><option>ME</option></FormSelect>
            <FormInput label="Attendance Threshold %" type="number" value={threshold} onChange={setThreshold} />
            <FormSelect label="Schedule" value="Start Now" onChange={() => {}}><option>Start Now</option><option>Schedule Later</option></FormSelect>
            <FormSelect label="Retry Policy" value="3 Attempts" onChange={() => {}}><option>3 Attempts</option><option>2 Attempts</option><option>1 Attempt</option></FormSelect>
          </div>
          <div className="form-actions"><button className="secondary-button" onClick={onBack}>Cancel</button><button className="primary-button" onClick={onCreated} disabled={!name}><Megaphone size={17} />Create Campaign</button></div>
        </div>
        <div className="card">
          <div className="card-head"><div><h3>Eligible Preview</h3><p>Students matching current rules</p></div><Target size={19} /></div>
          <div className="preview-count">{eligible.length}<span>students</span></div>
          {eligible.slice(0, 5).map((s) => <div className="queue-row" key={s.id}><div className="avatar small">{initials(s.name)}</div><div><strong>{s.name}</strong><span>{s.branch} • {s.attendance}%</span></div><span className="status-pill warning">Target</span></div>)}
        </div>
      </div>
    </>
  );
}

function CampaignDetails({ campaign, onBack }) {
  const [running, setRunning] = useState(campaign.status === "Active");
  return (
    <>
      <PageHeader title="Campaign Details" subtitle={campaign.name} actions={<button className="secondary-button" onClick={onBack}><ArrowLeft size={17} />Back</button>} />
      <div className="detail-hero card"><div className="campaign-icon"><Megaphone size={27} /></div><div><h2>{campaign.name}</h2><p>{campaign.period} • {campaign.scope} • Threshold {campaign.threshold}</p><span className={statusClass(running ? "Active" : "Completed")}>{running ? "Active" : "Paused"}</span></div><div className="hero-actions"><button className="secondary-button" onClick={() => setRunning((v) => !v)}>{running ? <><Pause size={17} />Pause</> : <><Play size={17} />Resume</>}</button></div></div>
      <div className="summary-grid"><SummaryCard icon={Target} label="Targets" value={campaign.targets} /><SummaryCard icon={CheckCircle2} label="Completed" value={campaign.completed} /><SummaryCard icon={PhoneOff} label="Failed" value={campaign.failed} /><SummaryCard icon={Clock3} label="Follow-ups" value="7" /></div>
      <div className="two-grid"><div className="card"><div className="card-head"><h3>Frozen Target List</h3><Users size={19} /></div><div className="queue-row"><div className="avatar small">AS</div><div><strong>Aarav Sharma</strong><span>91% attendance</span></div><span className="status-pill success">Completed</span></div><div className="queue-row"><div className="avatar small">RV</div><div><strong>Rohan Verma</strong><span>73% attendance</span></div><span className="status-pill warning">Follow-up</span></div></div><div className="card"><div className="card-head"><h3>Workflow</h3><Activity size={19} /></div><WorkflowCard number="01" title="Eligibility" text="Attendance threshold applied" done /><WorkflowCard number="02" title="AI Call Queue" text="Students added to calling queue" done /><WorkflowCard number="03" title="Parent Contact" text="Calling and retry policy" /></div></div>
    </>
  );
}

function WorkflowCard({ number, title, text, done }) {
  return <div className="workflow-card"><div className={`workflow-number ${done ? "done" : ""}`}>{done ? <CheckCircle2 size={17} /> : number}</div><div><strong>{title}</strong><span>{text}</span></div></div>;
}

const callRows = [
  { student: "Aarav Sharma", parent: "Rajesh Sharma", duration: "02:48", status: "Completed", time: "10:42 AM", outcome: "Connected" },
  { student: "Rohan Verma", parent: "Sunil Verma", duration: "01:32", status: "Follow-up Required", time: "10:28 AM", outcome: "Connected" },
  { student: "Aditya Mishra", parent: "Vivek Mishra", duration: "00:00", status: "Failed", time: "10:11 AM", outcome: "No Answer" },
  { student: "Sneha Yadav", parent: "Mahesh Yadav", duration: "03:17", status: "Completed", time: "09:54 AM", outcome: "Connected" },
];

function CallsPage() {
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState("All");
  if (selected) return <CallDetails call={selected} onBack={() => setSelected(null)} />;
  const rows = status === "All" ? callRows : callRows.filter((c) => c.status === status);
  return (
    <>
      <PageHeader title="Calls" subtitle="Monitor AI calling activity and outcomes" />
      <div className="summary-grid"><SummaryCard icon={PhoneCall} label="Total Calls" value="148" /><SummaryCard icon={CheckCircle2} label="Completed" value="124" /><SummaryCard icon={PhoneOff} label="Failed" value="9" /><SummaryCard icon={Clock3} label="Follow-up Required" value="15" /></div>
      <div className="card filter-card"><div className="search-box"><Search size={18} /><input placeholder="Search student or parent..." /></div><select value={status} onChange={(e) => setStatus(e.target.value)}><option>All</option><option>Completed</option><option>Failed</option><option>Follow-up Required</option></select><button className="secondary-button"><CalendarDays size={17} />Today</button></div>
      <div className="card table-card"><div className="card-head"><div><h3>Call Activity</h3><p>Latest AI calling attempts</p></div></div><div className="table-wrap"><table><thead><tr><th>Student</th><th>Parent / Guardian</th><th>Duration</th><th>Outcome</th><th>Status</th><th>Time</th><th></th></tr></thead><tbody>{rows.map((c, i) => <tr key={i}><td><div className="student-cell"><div className="avatar">{initials(c.student)}</div><strong>{c.student}</strong></div></td><td>{c.parent}</td><td>{c.duration}</td><td>{c.outcome}</td><td><span className={statusClass(c.status)}>{c.status}</span></td><td>{c.time}</td><td><button className="icon-button plain" onClick={() => setSelected(c)}><Eye size={17} /></button></td></tr>)}</tbody></table></div></div>
    </>
  );
}

function CallDetails({ call, onBack }) {
  return (
    <>
      <PageHeader title="Call Details" subtitle={`${call.student} • AI Calling Record`} actions={<button className="secondary-button" onClick={onBack}><ArrowLeft size={17} />Back</button>} />
      <div className="two-grid">
        <div className="card">
          <div className="call-profile"><div className="large-avatar">{initials(call.student)}</div><div><h2>{call.student}</h2><p>Parent: {call.parent}</p><span className={statusClass(call.status)}>{call.status}</span></div></div>
          <div className="detail-grid"><DetailRow label="Call Duration" value={call.duration} /><DetailRow label="Started At" value={call.time} /><DetailRow label="Outcome" value={call.outcome} /><DetailRow label="Attempts" value="2" /></div>
        </div>
        <div className="card ai-card"><div className="ai-heading"><div className="ai-icon"><Sparkles size={20} /></div><div><h3>AI Analysis</h3><p>Generated from conversation</p></div></div><div className="analysis-box"><strong>Summary</strong><p>Parent was informed about the current attendance level and the importance of regular attendance. Follow-up is recommended.</p></div><div className="analysis-tags"><span>Attendance Alert</span><span>Parent Informed</span><span>Follow-up</span></div></div>
      </div>
      <div className="two-grid">
        <div className="card"><div className="card-head"><h3>Call Timeline</h3><Clock3 size={19} /></div><div className="timeline"><div><i></i><strong>Call started</strong><span>{call.time}</span></div><div><i></i><strong>Parent connected</strong><span>+00:08</span></div><div><i></i><strong>Attendance message delivered</strong><span>+01:02</span></div><div><i></i><strong>Call ended</strong><span>{call.duration}</span></div></div></div>
        <div className="card transcript"><div className="card-head"><h3>Conversation Transcript</h3><MessageSquare size={19} /></div><div className="chat-bubble ai">Hello, this is the Attendance AI calling regarding the attendance of the student.</div><div className="chat-bubble parent">Yes, please tell me the current attendance status.</div><div className="chat-bubble ai">The current attendance is below the configured threshold. Regular attendance is recommended.</div></div>
      </div>
    </>
  );
}

function ConversationsPage() {
  const conversations = [
    { name: "Aarav Sharma", parent: "Rajesh Sharma", time: "10:42 AM", status: "Completed", summary: "Parent acknowledged the attendance alert." },
    { name: "Rohan Verma", parent: "Sunil Verma", time: "10:28 AM", status: "Follow-up Required", summary: "Parent requested a follow-up from college staff." },
    { name: "Sneha Yadav", parent: "Mahesh Yadav", time: "09:54 AM", status: "Completed", summary: "Attendance information was communicated successfully." },
  ];
  return (
    <>
      <PageHeader title="Conversations" subtitle="Review AI calling conversations and summaries" />
      <div className="summary-grid"><SummaryCard icon={MessageSquare} label="Conversations" value="124" /><SummaryCard icon={CheckCircle2} label="Resolved" value="107" /><SummaryCard icon={Clock3} label="Follow-ups" value="15" /><SummaryCard icon={PhoneOff} label="Unanswered" value="9" /></div>
      <div className="card filter-card"><div className="search-box"><Search size={18} /><input placeholder="Search conversations..." /></div><select><option>All Status</option><option>Completed</option><option>Follow-up Required</option></select><button className="secondary-button"><Filter size={17} />Filters</button></div>
      <div className="conversation-list">{conversations.map((c, i) => <div className="card conversation-card" key={i}><div className="conversation-left"><div className="avatar">{initials(c.name)}</div><div><div className="conversation-title"><strong>{c.name}</strong><span>{c.parent}</span></div><p>{c.summary}</p><span className="conversation-time"><Clock3 size={14} />{c.time}</span></div></div><div className="conversation-right"><span className={statusClass(c.status)}>{c.status}</span><button className="secondary-button small-button"><Eye size={16} />View</button></div></div>)}</div>
    </>
  );
}

function FollowUpsPage() {
  const [items, setItems] = useState([
    { name: "Rohan Verma", parent: "Sunil Verma", due: "Today", priority: "High", assigned: "Shantanu Mishra", status: "Pending" },
    { name: "Aditya Mishra", parent: "Vivek Mishra", due: "Today", priority: "Medium", assigned: "Priya Admin", status: "Pending" },
    { name: "Kunal Patel", parent: "Raj Patel", due: "Tomorrow", priority: "Low", assigned: "Shantanu Mishra", status: "Pending" },
  ]);
  const complete = (name) => setItems((prev) => prev.map((x) => x.name === name ? { ...x, status: "Completed" } : x));
  return (
    <>
      <PageHeader title="Follow-ups" subtitle="Track pending parent and student follow-up tasks" />
      <div className="summary-grid"><SummaryCard icon={Clock3} label="Pending" value={items.filter((x) => x.status === "Pending").length} /><SummaryCard icon={CheckCircle2} label="Completed" value="38" /><SummaryCard icon={AlertTriangle} label="High Priority" value="4" /><SummaryCard icon={CalendarDays} label="Due Today" value="2" /></div>
      <div className="insight-banner"><div className="insight-icon"><Sparkles size={20} /></div><div><strong>Follow-up insight</strong><span>Some parents requested personal contact from college staff after the AI call.</span></div></div>
      <div className="card table-card"><div className="card-head"><div><h3>Follow-up Queue</h3><p>Tasks assigned to staff</p></div><select><option>All Priorities</option><option>High</option><option>Medium</option><option>Low</option></select></div><div className="table-wrap"><table><thead><tr><th>Student</th><th>Parent / Guardian</th><th>Priority</th><th>Assigned To</th><th>Due</th><th>Status</th><th>Action</th></tr></thead><tbody>{items.map((x) => <tr key={x.name}><td><div className="student-cell"><div className="avatar">{initials(x.name)}</div><strong>{x.name}</strong></div></td><td>{x.parent}</td><td><span className={`priority ${x.priority.toLowerCase()}`}>{x.priority}</span></td><td>{x.assigned}</td><td>{x.due}</td><td><span className={statusClass(x.status)}>{x.status}</span></td><td>{x.status === "Pending" ? <button className="primary-button compact" onClick={() => complete(x.name)}><CheckCircle2 size={15} />Complete</button> : <span className="completed-text"><CheckCircle2 size={16} />Done</span>}</td></tr>)}</tbody></table></div></div>
    </>
  );
}

function ReportsPage() {
  return (
    <>
      <PageHeader title="Reports" subtitle="Attendance, campaign and communication reports" actions={<button className="secondary-button"><Download size={17} />Export Report</button>} />
      <div className="card filter-card"><select><option>All Branches</option><option>CSE</option><option>AI/ML</option><option>ECE</option></select><select><option>Current Semester</option><option>Previous Semester</option></select><select><option>All Campaigns</option><option>Low Attendance Alert</option></select><button className="secondary-button"><Filter size={17} />Apply</button></div>
      <div className="stats-grid"><StatCard icon={ClipboardCheck} label="Average Attendance" value="82%" note="+3.4%" /><StatCard icon={PhoneCall} label="Call Success Rate" value="84%" note="This period" /><StatCard icon={CheckSquare} label="Follow-ups Completed" value="71%" note="38 completed" /><StatCard icon={Target} label="Eligible Students" value="76%" note="75% threshold" /></div>
      <div className="two-grid"><div className="card"><div className="card-head"><div><h3>Attendance by Branch</h3><p>Current semester</p></div></div><div className="report-bars"><ReportBar label="CSE" value={87} /><ReportBar label="AI/ML" value={79} /><ReportBar label="ECE" value={84} /><ReportBar label="ME" value={76} /></div></div><div className="card"><div className="card-head"><div><h3>Campaign Outcomes</h3><p>Latest campaigns</p></div></div><div className="donut-wrap"><div className="donut"><strong>84%</strong><span>Success</span></div><div className="legend"><span><i></i>Completed 84%</span><span><i></i>Follow-up 10%</span><span><i></i>Failed 6%</span></div></div></div></div>
    </>
  );
}

function ReportBar({ label, value }) {
  return <div className="report-bar"><div><span>{label}</span><strong>{value}%</strong></div><div className="bar-track"><i style={{ width: `${value}%` }} /></div></div>;
}

function UsersPage() {
  const users = [
    ["Shantanu Mishra", "Administrator", "Active", "All Departments"],
    ["Priya Admin", "Staff", "Active", "CSE"],
    ["Rahul Verma", "Staff", "Active", "AI/ML"],
    ["Demo User", "Viewer", "Inactive", "ECE"],
  ];
  return (
    <>
      <PageHeader title="Users" subtitle="Manage system users and access" actions={<button className="primary-button"><Plus size={17} />Create User</button>} />
      <div className="card table-card"><div className="card-head"><div><h3>User List</h3><p>Users with system access</p></div><div className="table-tools"><Search size={17} /><input placeholder="Search users..." /></div></div><div className="table-wrap"><table><thead><tr><th>User</th><th>Role</th><th>Status</th><th>Scope</th><th>Action</th></tr></thead><tbody>{users.map((u) => <tr key={u[0]}><td><div className="student-cell"><div className="avatar">{initials(u[0])}</div><div><strong>{u[0]}</strong><span>{u[0].toLowerCase().replace(" ", ".")}@attendai.local</span></div></div></td><td>{u[1]}</td><td><span className={statusClass(u[2])}>{u[2]}</span></td><td>{u[3]}</td><td><div className="row-actions"><button><Eye size={16} /></button><button><Pencil size={16} /></button></div></td></tr>)}</tbody></table></div></div>
    </>
  );
}

function RolesPage() {
  const permissions = ["View Students", "Edit Students", "Import Attendance", "Create Campaigns", "View Calls", "Manage Follow-ups", "Export Reports", "Manage Users"];
  return (
    <>
      <PageHeader title="Roles & Scopes" subtitle="Configure role permissions and effective access" actions={<button className="primary-button"><Save size={17} />Save Changes</button>} />
      <div className="two-grid"><div className="card"><div className="card-head"><h3>Role Assignment</h3><UserCog size={19} /></div><FormSelect label="Select Role" value="Administrator" onChange={() => {}}><option>Administrator</option><option>Staff</option><option>Viewer</option></FormSelect><FormSelect label="Department Scope" value="Computer Science" onChange={() => {}}><option>Computer Science</option><option>All Departments</option></FormSelect><FormSelect label="Branch Scope" value="All Branches" onChange={() => {}}><option>All Branches</option><option>CSE</option><option>AI/ML</option><option>ECE</option></FormSelect></div><div className="card"><div className="card-head"><h3>Permission Matrix</h3><ShieldCheck size={19} /></div>{permissions.map((p) => <label className="permission-row" key={p}><span>{p}</span><input type="checkbox" defaultChecked /></label>)}</div></div>
    </>
  );
}

function AuditLogsPage() {
  const logs = [
    ["Shantanu Mishra", "Updated student", "STU005", "18 Sep 2026, 10:12 AM"],
    ["Shantanu Mishra", "Imported attendance", "attendance_aug_2026.xlsx", "18 Sep 2026, 09:48 AM"],
    ["Priya Admin", "Created campaign", "Low Attendance Alert", "17 Sep 2026, 04:20 PM"],
    ["Admin", "Changed settings", "Default threshold", "17 Sep 2026, 02:05 PM"],
  ];
  return (
    <>
      <PageHeader title="Audit Logs" subtitle="Track important system actions and changes" actions={<button className="secondary-button"><Download size={17} />Export</button>} />
      <div className="card filter-card"><div className="search-box"><Search size={18} /><input placeholder="Search audit logs..." /></div><select><option>All Actions</option><option>Create</option><option>Update</option><option>Delete</option></select><button className="secondary-button"><CalendarDays size={17} />Date Range</button></div>
      <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>User</th><th>Action</th><th>Entity</th><th>Date & Time</th><th></th></tr></thead><tbody>{logs.map((l, i) => <tr key={i}><td><strong>{l[0]}</strong></td><td>{l[1]}</td><td>{l[2]}</td><td>{l[3]}</td><td><button className="icon-button plain"><Eye size={17} /></button></td></tr>)}</tbody></table></div></div>
    </>
  );
}

function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" subtitle="Configure attendance and communication behavior" actions={<button className="primary-button"><Save size={17} />Save Settings</button>} />
      <div className="two-grid"><div className="card form-card"><div className="card-head"><h3>Attendance Settings</h3><SlidersHorizontal size={19} /></div><div className="form-grid one"><FormInput label="Default Attendance Threshold %" value="75" onChange={() => {}} type="number" /><FormSelect label="Default Language" value="English" onChange={() => {}}><option>English</option><option>Hindi</option><option>Hinglish</option></FormSelect></div><div className="toggle-row"><div><strong>Enable Automatic Eligibility</strong><span>Use threshold for campaign target selection.</span></div><input type="checkbox" defaultChecked /></div></div><div className="card form-card"><div className="card-head"><h3>Calling Settings</h3><PhoneCall size={19} /></div><div className="form-grid one"><FormSelect label="Retry Policy" value="3 Attempts" onChange={() => {}}><option>3 Attempts</option><option>2 Attempts</option><option>1 Attempt</option></FormSelect><FormInput label="Calling Window" value="10:00 AM – 06:00 PM" onChange={() => {}} /></div><div className="service-status"><div><span className="service-dot"></span><strong>Calling Provider</strong></div><span className="status-pill success">Connected</span></div></div></div>
    </>
  );
}

function ProfilePage() {
  return (
    <>
      <PageHeader title="Profile" subtitle="Your account information and preferences" />
      <div className="two-grid"><div className="card profile-card"><div className="profile-avatar">SM</div><h2>Shantanu Mishra</h2><p>Administrator</p><div className="profile-info"><DetailRow label="Username" value="shantanu" /><DetailRow label="Email" value="shantanu@attendai.local" /><DetailRow label="Scope" value="All Departments" /></div></div><div className="card form-card"><div className="card-head"><h3>Security</h3><Lock size={19} /></div><FormInput label="Current Password" value="" onChange={() => {}} type="password" placeholder="••••••••" /><FormInput label="New Password" value="" onChange={() => {}} type="password" placeholder="••••••••" /><button className="primary-button"><Lock size={17} />Change Password</button></div></div>
    </>
  );
}

export default App;
