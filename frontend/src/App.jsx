import { useEffect, useState } from "react";
import {
  BookOpen,
  Brain,
  CalendarCheck,
  Clock,
  GraduationCap,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Megaphone,
  Network,
  PhoneCall,
  Radio,
  Shield,
  Upload,
  UserCheck,
  Users,
} from "lucide-react";
import { api, clearToken, getToken } from "./api/client";
import CampaignPage from "./features/CampaignPage";
import CallOperationsPage from "./features/CallOperationsPage";
import ClassesPage from "./features/ClassesPage";
import DepartmentsPage from "./features/DepartmentsPage";
import DashboardPage from "./features/DashboardPage";
import FollowupsPage from "./features/FollowupsPage";
import ImportPage from "./features/ImportPage";
import LoginPage from "./features/LoginPage";
import ParentsPage from "./features/ParentsPage";
import PasswordPage from "./features/PasswordPage";
import PeoplePage from "./features/PeoplePage";
import StudentsPage from "./features/StudentsPage";
import AttendanceTerminal from "./features/AttendanceTerminal";
import MLRiskPage from "./features/MLRiskPage";
import VoiceStudioPage from "./features/VoiceStudioPage";
import Notice from "./components/Notice";
import "./App.css";
import "./styles/workspace.css";
import "./styles/futuristic2026.css";

const navigation = [
  { id: "overview", label: "Dashboard", icon: LayoutDashboard, permission: "reports.read" },
  { id: "terminal", label: "Roll Call Terminal", icon: CalendarCheck, permission: "attendance.read" },
  { id: "calls", label: "Call Operations", icon: PhoneCall, permission: "calls.read" },
  { id: "campaigns", label: "Campaigns", icon: Megaphone, permission: "campaign.create" },
  { id: "followups", label: "Follow-ups", icon: Clock, permission: "calls.read" },
  { id: "parents", label: "Parents & Consent", icon: UserCheck, permission: "student.read" },
  { id: "students", label: "Students", icon: Users, permission: "student.read" },
  { id: "classes", label: "Classes", icon: BookOpen, permission: "class.read" },
  { id: "imports", label: "Batch Imports", icon: Upload, anyPermission: ["attendance.import", "student.create"] },
  { id: "ml_risk", label: "ML Risk Radar", icon: Brain, permission: "reports.read" },
  { id: "voice", label: "Voice Studio (Demo)", icon: Radio, permission: "reports.read" },
  { id: "people", label: "People & Roles", icon: Shield, permission: "users.read" },
  { id: "departments", label: "Departments", icon: Network, permission: "scopes.manage" },
  { id: "security", label: "Security & Keys", icon: LockKeyhole },
];

function Workspace({ user, onSignOut, onUserUpdate }) {
  const [activePage, setActivePage] = useState("overview");
  const [selectedStudentForVoice, setSelectedStudentForVoice] = useState(null);

  const visibleNavigation = navigation.filter(
    (item) =>
      (!item.permission || user.permissions.includes(item.permission)) &&
      (!item.anyPermission || item.anyPermission.some((permission) => user.permissions.includes(permission)))
  );

  const isDirector = user.role === "SUPER_ADMIN";
  const isHOD = user.role === "ADMIN";

  function handleNavigateToVoice(studentId) {
    setSelectedStudentForVoice(studentId);
    setActivePage("calls");
  }

  return (
    <div className="quantum-app">
      {/* 2026 TOP FLOATING QUANTUM ISLAND DOCK */}
      <header className="quantum-island-dock">
        {/* Brand Capsule */}
        <div
          className="quantum-brand"
          onClick={() => setActivePage("overview")}
          title="Return to Command HUD"
        >
          <div className="brand-hologram-cube">
            <GraduationCap size={22} />
          </div>
          <div className="brand-info">
            <strong>AttendWise AI · 2026</strong>
            <small>
              <span className="pulse-beacon emerald" style={{ width: 5, height: 5 }} />
              Autonomous Attendance OS
            </small>
          </div>
        </div>

        {/* Role Clearance Pill */}
        <div
          className={`role-clearance-pill ${
            isDirector ? "director" : isHOD ? "admin" : "staff"
          }`}
          title="Current RBAC clearance level"
        >
          <span
            className={`pulse-beacon ${
              isDirector ? "gold" : isHOD ? "violet" : "emerald"
            }`}
          />
          {isDirector ? "Director General" : isHOD ? "Department HOD" : "Local Faculty"}
        </div>

        {/* Fluid Horizontal Nav Strip */}
        <nav className="quantum-nav-strip" aria-label="Quantum Main Navigation">
          {visibleNavigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-pill ${activePage === id ? "active" : ""}`}
              onClick={() => setActivePage(id)}
            >
              <Icon size={14} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        {/* Right Dock Controls Tray */}
        <div className="quantum-dock-tray">
          {/* Quick AI Calling / Voice Agent Button */}
          {user.permissions.includes("calls.read") && <button
            onClick={() => setActivePage("calls")}
            className="ai-voice-trigger"
            title="Open AI Call Operations"
          >
            <div className="soundwave-ring">
              <span />
              <span />
              <span />
            </div>
            <span>AI Calling</span>
          </button>}

          {/* User Profile Capsule */}
          <div className="user-capsule">
            <div className="user-avatar-glow">
              {(user.full_name || user.username).slice(0, 1).toUpperCase()}
            </div>
            <div className="user-text-meta">
              <strong>{user.full_name || user.username}</strong>
            </div>
            <button
              className="signout-icon-btn"
              onClick={onSignOut}
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Stage */}
      <main className="quantum-content-canvas">
        {activePage === "overview" && (
          <DashboardPage user={user} onNavigate={setActivePage} />
        )}
        {activePage === "terminal" && (
          <AttendanceTerminal user={user} onNavigateToVoice={handleNavigateToVoice} />
        )}
        {activePage === "calls" && (
          <CallOperationsPage user={user} initialStudentId={selectedStudentForVoice} />
        )}
        {activePage === "campaigns" && <CampaignPage user={user} />}
        {activePage === "followups" && (
          <FollowupsPage onNavigateToVoice={handleNavigateToVoice} />
        )}
        {activePage === "parents" && <ParentsPage user={user} />}
        {activePage === "ml_risk" && (
          <MLRiskPage user={user} onSelectStudentForVoice={handleNavigateToVoice} />
        )}
        {activePage === "voice" && (
          <VoiceStudioPage user={user} initialStudentId={selectedStudentForVoice} />
        )}
        {activePage === "students" && <StudentsPage user={user} />}
        {activePage === "classes" && <ClassesPage user={user} />}
        {activePage === "imports" && <ImportPage user={user} />}
        {activePage === "people" && <PeoplePage user={user} />}
        {activePage === "departments" && (
          <DepartmentsPage user={user} onUserUpdate={onUserUpdate} />
        )}
        {activePage === "security" && (
          <PasswordPage onPasswordChanged={() => {}} />
        )}
      </main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(() => Boolean(getToken()));
  const [startupError, setStartupError] = useState("");

  useEffect(() => {
    let active = true;
    if (!getToken()) return () => { active = false; };
    api.currentUser()
      .then((currentUser) => { if (active) setUser(currentUser); })
      .catch((error) => {
        clearToken();
        if (active) setStartupError(error.message);
      })
      .finally(() => { if (active) setCheckingSession(false); });
    return () => { active = false; };
  }, []);

  function signOut() {
    clearToken();
    setUser(null);
  }

  function updatePassword() {
    setUser((current) => ({ ...current, must_change_password: false }));
  }

  if (checkingSession) {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "#080c14",
          color: "#38bdf8",
          fontFamily: "Inter, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="pulse-beacon emerald" style={{ width: 12, height: 12 }} />
          <span>Initializing Quantum 2026 Academic Session…</span>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <>
        {startupError && <Notice>{startupError}</Notice>}
        <LoginPage onSignedIn={setUser} />
      </>
    );
  }

  if (user.must_change_password) {
    return (
      <main className="quantum-auth-backdrop">
        <PasswordPage mustChange onPasswordChanged={updatePassword} />
      </main>
    );
  }

  return <Workspace user={user} onSignOut={signOut} onUserUpdate={setUser} />;
}
