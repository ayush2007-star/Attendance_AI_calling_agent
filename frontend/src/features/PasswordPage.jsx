import { useState } from "react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function PasswordPage({ mustChange = false, onPasswordChanged }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmation) {
      setError("The new passwords do not match.");
      return;
    }
    if (newPassword.length < 14) {
      setError("Use at least 14 characters.");
      return;
    }
    setBusy(true);
    try {
      await api.changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      onPasswordChanged();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="content-card narrow-card">
      <div className="section-heading"><div><h3>{mustChange ? "Set your private password" : "Change your password"}</h3><p>{mustChange ? "Your one-time password must be replaced before you continue." : "Use a password you do not use on another site."}</p></div></div>
      <Notice>{error}</Notice>
      <form className="stack-form" onSubmit={submit}>
        <label>Current or temporary password<input required type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
        <label>New password (14+ characters)<input required minLength={14} maxLength={128} type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
        <label>Confirm new password<input required minLength={14} maxLength={128} type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>
        <button className="button button-primary" disabled={busy}>{busy ? "Updating…" : "Update password"}</button>
      </form>
    </section>
  );
}
