import { useState } from "react";
import {
  ShieldCheck,
  Sparkles,
  Lock,
  User,
  Eye,
  EyeOff,
  Fingerprint,
  ChevronRight,
} from "lucide-react";
import { signIn } from "../api/client";
import Notice from "../components/Notice";

export default function LoginPage({ onSignedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    setScanning(true);

    try {
      const user = await signIn(username.trim(), password);
      onSignedIn(user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      setScanning(false);
    }
  }

  return (
    <main className="quantum-auth-backdrop">
      <section className="quantum-login-card">
        {/* Holographic Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div className="login-security-beacon">
            <span className="pulse-beacon gold" />
            ATTENDWISE QUANTUM 2026 · SECURITY GATEWAY
          </div>
          <span style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace" }}>RBAC v2.6.4</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
          <div className="brand-hologram-cube" style={{ width: 44, height: 44, borderRadius: 14 }}>
            <Sparkles size={22} />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, letterSpacing: "-0.5px", color: "#fff" }}>
              Academic Command Center
            </h1>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "#94a3b8" }}>
              Sign in using your institution account
            </p>
          </div>
        </div>

        <Notice>{error}</Notice>

        {/* Auth Form */}
        <form className="stack-form" onSubmit={submit}>
          <label style={{ color: "#cbd5e1", fontSize: 12 }}>
            Email or Username
            <div style={{ position: "relative" }}>
              <input
                autoComplete="username"
                required
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your email or username"
                style={{
                  background: "rgba(15, 23, 42, 0.8)",
                  borderColor: "rgba(255, 255, 255, 0.12)",
                  color: "#fff",
                  paddingLeft: 38,
                }}
              />
              <User
                size={16}
                style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#64748b" }}
              />
            </div>
          </label>

          <label style={{ color: "#cbd5e1", fontSize: 12 }}>
            Password
            <div style={{ position: "relative" }}>
              <input
                autoComplete="current-password"
                required
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                style={{
                  background: "rgba(15, 23, 42, 0.8)",
                  borderColor: "rgba(255, 255, 255, 0.12)",
                  color: "#fff",
                  paddingLeft: 38,
                  paddingRight: 40,
                }}
              />
              <Lock
                size={16}
                style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#64748b" }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: 10,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: 0,
                  color: "#64748b",
                  padding: 4,
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          <button
            className="btn-quantum btn-quantum-primary"
            style={{ width: "100%", padding: 13, marginTop: 6 }}
            disabled={busy}
          >
            {scanning ? (
              <>
                <Fingerprint size={18} className="pulse-beacon" />
                <span>Verifying Biometric & RBAC Credentials…</span>
              </>
            ) : (
              <>
                <ShieldCheck size={18} />
                <span>Authorize & Enter Workspace</span>
                <ChevronRight size={16} />
              </>
            )}
          </button>
        </form>

        <div style={{ marginTop: 20, textAlign: "center", fontSize: 11, color: "#64748b" }}>
          <span>Institution Access Control Protocol 2026. All operations audited in real-time.</span>
        </div>
      </section>
    </main>
  );
}
