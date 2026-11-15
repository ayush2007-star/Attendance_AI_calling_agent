import { useCallback, useEffect, useState } from "react";
import {
  Bot,
  FileText,
  Mic,
  MicOff,
  Pause,
  PhoneCall,
  PhoneForwarded,
  Play,
  Radio,
  RefreshCw,
  Square,
} from "lucide-react";
import { api } from "../api/client";
import Notice from "../components/Notice";

export default function CallOperationsPage({ user, initialStudentId }) {
  // Service status
  const [serviceStatus, setServiceStatus] = useState(null);
  const [serviceLoading, setServiceLoading] = useState(false);

  // Campaigns & targets
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState("");
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [targets, setTargets] = useState([]);
  const [targetsLoading, setTargetsLoading] = useState(false);

  // Call history
  const [callHistory, setCallHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Call detail modal
  const [attemptDetail, setAttemptDetail] = useState(null);

  // Action states
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Demo call modal
  const [demoModalTarget, setDemoModalTarget] = useState(null);
  const [demoPreset, setDemoPreset] = useState("MEDICAL_REASON");
  const [demoCustomReply, setDemoCustomReply] = useState("");

  // Faculty voice command assistant (secondary feature)
  const [showVoiceCommands, setShowVoiceCommands] = useState(false);
  const [voiceQuery, setVoiceQuery] = useState("");
  const [voiceFeedback, setVoiceFeedback] = useState(null);
  const [isListening, setIsListening] = useState(false);

  // Load voice service health (for manual refresh / actions)
  const loadServiceStatus = useCallback(async () => {
    setServiceLoading(true);
    try {
      const statusData = await api.voiceServiceStatus();
      setServiceStatus(statusData);
    } catch {
      setServiceStatus({
        service_online: false,
        voice_agent_url: "http://127.0.0.1:8001",
        real_calls_enabled: false,
        configured_model: "openai/gpt-oss-20b",
      });
    } finally {
      setServiceLoading(false);
    }
  }, []);

  // Load campaigns (for manual refresh)
  const loadCampaigns = useCallback(async () => {
    try {
      const data = await api.campaigns();
      setCampaigns(data);
      if (data.length > 0 && !selectedCampaignId) {
        setSelectedCampaignId(data[0].id);
      }
    } catch (err) {
      setError(err.message);
    }
  }, [selectedCampaignId]);

  // Load targets for selected campaign (for manual refresh)
  const loadTargets = useCallback(async (campaignId) => {
    if (!campaignId) {
      setTargets([]);
      return;
    }
    setTargetsLoading(true);
    try {
      const [targetList, campData] = await Promise.all([
        api.campaignTargets(campaignId),
        api.campaignDetails(campaignId).catch(() => null),
      ]);
      setTargets(targetList);
      if (campData) setSelectedCampaign(campData);
    } catch (err) {
      setError(err.message);
    } finally {
      setTargetsLoading(false);
    }
  }, []);

  // Load recent call history (for manual refresh)
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const attempts = await api.callAttempts({ limit: 20 });
      setCallHistory(attempts);
    } catch (err) {
      console.error(err);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.voiceServiceStatus()
      .then((statusData) => { if (active) setServiceStatus(statusData); })
      .catch(() => {
        if (active) setServiceStatus({
          service_online: false,
          voice_agent_url: "http://127.0.0.1:8001",
          real_calls_enabled: false,
          configured_model: "openai/gpt-oss-20b",
        });
      });

    api.campaigns()
      .then((data) => {
        if (active) {
          setCampaigns(data);
          if (data.length > 0) setSelectedCampaignId((prev) => prev || data[0].id);
        }
      })
      .catch((err) => { if (active) setError(err.message); });

    api.callAttempts({ limit: 20 })
      .then((attempts) => { if (active) setCallHistory(attempts); })
      .catch((err) => console.error(err));

    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedCampaignId) {
      return;
    }
    let active = true;
    Promise.all([
      api.campaignTargets(selectedCampaignId),
      api.campaignDetails(selectedCampaignId).catch(() => null),
    ])
      .then(([targetList, campData]) => {
        if (active) {
          setTargets(targetList);
          if (campData) setSelectedCampaign(campData);
        }
      })
      .catch((err) => { if (active) setError(err.message); });

    return () => { active = false; };
  }, [selectedCampaignId]);

  useEffect(() => {
    if (initialStudentId && targets.length > 0) {
      const match = targets.find((t) => t.student_id === initialStudentId);
      if (match) {
        queueMicrotask(() => setDemoModalTarget(match));
      }
    }
  }, [initialStudentId, targets]);

  // Open full attempt details
  async function viewAttemptDetails(attemptId) {
    try {
      const detail = await api.callAttemptDetail(attemptId);
      setAttemptDetail(detail);
    } catch (err) {
      setError(err.message);
    }
  }

  // Start campaign sequential calling
  async function handleStartCampaign() {
    if (!selectedCampaignId) return;
    setBusyAction("start");
    setError("");
    setSuccess("");
    try {
      await api.startCampaign(selectedCampaignId);
      setSuccess("Campaign calling started. Sequential dispatch engaged (concurrency: 1).");
      await loadTargets(selectedCampaignId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAction("");
    }
  }

  // Pause campaign
  async function handlePauseCampaign() {
    if (!selectedCampaignId) return;
    setBusyAction("pause");
    try {
      await api.pauseCampaign(selectedCampaignId);
      setSuccess("Campaign paused.");
      await loadTargets(selectedCampaignId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAction("");
    }
  }

  // Stop campaign
  async function handleStopCampaign() {
    if (!selectedCampaignId) return;
    setBusyAction("stop");
    try {
      await api.stopCampaign(selectedCampaignId);
      setSuccess("Campaign stopped and completed.");
      await loadTargets(selectedCampaignId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAction("");
    }
  }

  // Dispatch next eligible target in campaign
  async function handleDispatchNext() {
    if (!selectedCampaignId) return;
    setBusyAction("dispatch-next");
    setError("");
    setSuccess("");
    try {
      const res = await api.dispatchNextCampaignTarget(selectedCampaignId);
      setSuccess(
        res.is_demo
          ? `Demo Call Completed for ${res.phone_number}. Full Hindi conversation and AI classification stored in PostgreSQL.`
          : `Live Call Dispatched via Twilio to ${res.phone_number} (Provider Call SID: ${res.provider_call_id}).`
      );
      await loadTargets(selectedCampaignId);
      await loadHistory();
      if (res.attempt_id) {
        viewAttemptDetails(res.attempt_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAction("");
    }
  }

  // Single target direct dispatch
  async function handleDirectDispatch(target) {
    setBusyAction(`call-${target.id}`);
    setError("");
    setSuccess("");
    try {
      const res = await api.dispatchTargetDirect(target.id);
      setSuccess(
        res.is_demo
          ? `[DEMO MODE] Call conversation simulated and saved for ${target.student_name}. Review transcript below.`
          : `Call dispatched to ${target.phone_number}. Twilio Call SID: ${res.provider_call_id}`
      );
      await loadTargets(selectedCampaignId);
      await loadHistory();
      if (res.attempt_id) {
        viewAttemptDetails(res.attempt_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAction("");
    }
  }

  // Execute demo simulation with chosen preset
  async function handleRunDemoSimulation() {
    if (!demoModalTarget) return;
    setBusyAction("running-demo");
    setError("");
    setSuccess("");
    try {
      const detail = await api.simulateDemoCall({
        campaign_target_id: demoModalTarget.id,
        reason_preset: demoPreset,
        custom_parent_reply: demoCustomReply.trim() || undefined,
      });
      setDemoModalTarget(null);
      setSuccess(`Completed demo call for ${detail.student_name}. Response classified as ${detail.conversation?.analysis?.category || "RECORDED"}.`);
      await loadTargets(selectedCampaignId);
      await loadHistory();
      setAttemptDetail(detail);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAction("");
    }
  }

  // Execute voice command
  async function handleVoiceCommand(cmdText) {
    const text = (cmdText || voiceQuery).trim();
    if (!text) return;
    try {
      const res = await api.voiceCommand(text);
      setVoiceFeedback(res);
      if (res.spoken_response && "speechSynthesis" in window) {
        const u = new SpeechSynthesisUtterance(res.spoken_response);
        u.lang = "hi-IN";
        window.speechSynthesis.speak(u);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  function toggleSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      alert("Browser speech recognition not available. Please type your command.");
      return;
    }
    if (isListening) {
      setIsListening(false);
      return;
    }
    const rec = new SpeechRec();
    rec.lang = "hi-IN";
    rec.onstart = () => setIsListening(true);
    rec.onresult = (e) => {
      const t = e.results[0][0].transcript;
      setVoiceQuery(t);
      setIsListening(false);
      handleVoiceCommand(t);
    };
    rec.onerror = () => setIsListening(false);
    rec.start();
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* 1. TOP TELEPHONY & SERVICE HEALTH DOCK */}
      <section className="content-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <Radio size={20} className={serviceStatus?.service_online ? "text-emerald" : "text-amber"} />
              <h3 style={{ margin: 0 }}>Call Operations & AI Voice Agent</h3>
            </div>
            <p className="call-safety-note" style={{ margin: 0 }}>
              Live autonomous outbound calling & natural Hindi/Hinglish dialog management for BBS College of Engineering and Technology.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span className={`role-clearance-pill ${serviceStatus?.service_online ? "admin" : "staff"}`}>
              <span className={`pulse-beacon ${serviceStatus?.service_online ? "emerald" : "amber"}`} />
              Telephony Service: {serviceStatus?.service_online ? "ONLINE (Port 8001)" : "OFFLINE"}
            </span>

            <span className={`role-clearance-pill ${serviceStatus?.real_calls_enabled ? "director" : "staff"}`}>
              {serviceStatus?.real_calls_enabled ? "REAL TELEPHONY ACTIVE" : "LOCAL DEMO MODE"}
            </span>

            <button
              className="button button-secondary"
              onClick={loadServiceStatus}
              disabled={serviceLoading}
              title="Refresh Voice Service Status"
              style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 12px" }}
            >
              <RefreshCw size={14} className={serviceLoading ? "spinning" : ""} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Technical Architecture Info Strip */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, marginTop: 14, padding: "10px 14px", background: "rgba(15,23,42,0.6)", borderRadius: 8, border: "1px solid rgba(56,189,248,0.15)", fontSize: "0.85rem" }}>
          <div><strong>STT Engine:</strong> Deepgram Nova-3 (Multilingual Streaming)</div>
          <div><strong>LLM Reasoning:</strong> Groq API ({serviceStatus?.configured_model || "openai/gpt-oss-20b"})</div>
          <div><strong>Speech Synthesis:</strong> Edge Neural TTS (hi-IN-MadhurNeural / +25%)</div>
          <div><strong>Telephony Gateway:</strong> Twilio Bi-directional Audio WSS</div>
        </div>
      </section>

      <Notice>{error}</Notice>
      {success && <Notice tone="success">{success}</Notice>}

      {/* 2. CAMPAIGN SELECTION & SEQUENTIAL CONTROLS */}
      <section className="content-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 14, marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <PhoneCall size={18} className="text-cyan" />
            <h4 style={{ margin: 0 }}>Active Absence Outreach Campaign</h4>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <label style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Select Campaign:</label>
            <select
              value={selectedCampaignId}
              onChange={(e) => setSelectedCampaignId(e.target.value)}
              style={{ padding: "6px 12px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", borderRadius: 6 }}
            >
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.attendance_date}) · {c.total_targets} targets
                </option>
              ))}
            </select>
            <button
              className="button button-secondary"
              onClick={loadCampaigns}
              title="Refresh Campaigns"
              style={{ display: "flex", alignItems: "center", gap: 4, padding: "6px 10px" }}
            >
              <RefreshCw size={13} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {selectedCampaign && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, marginBottom: 16 }}>
            <div style={{ padding: 10, background: "rgba(30,41,59,0.5)", borderRadius: 6, border: "1px solid rgba(51,65,85,0.7)" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Status</div>
              <strong style={{ color: selectedCampaign.status === "RUNNING" ? "#34d399" : "#38bdf8" }}>{selectedCampaign.status}</strong>
            </div>
            <div style={{ padding: 10, background: "rgba(30,41,59,0.5)", borderRadius: 6, border: "1px solid rgba(51,65,85,0.7)" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Total Targets</div>
              <strong>{selectedCampaign.total_targets}</strong>
            </div>
            <div style={{ padding: 10, background: "rgba(30,41,59,0.5)", borderRadius: 6, border: "1px solid rgba(51,65,85,0.7)" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Completed</div>
              <strong style={{ color: "#34d399" }}>{selectedCampaign.completed_calls}</strong>
            </div>
            <div style={{ padding: 10, background: "rgba(30,41,59,0.5)", borderRadius: 6, border: "1px solid rgba(51,65,85,0.7)" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Failed / Unreachable</div>
              <strong style={{ color: "#f87171" }}>{selectedCampaign.failed_calls}</strong>
            </div>
            <div style={{ padding: 10, background: "rgba(30,41,59,0.5)", borderRadius: 6, border: "1px solid rgba(51,65,85,0.7)" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Date</div>
              <strong>{selectedCampaign.attendance_date}</strong>
            </div>
          </div>
        )}

        {/* Campaign Action Toolbar */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {user.permissions.includes("calls.manage") && (
            <>
              {selectedCampaign?.status !== "RUNNING" ? (
                <button
                  className="button button-primary"
                  onClick={handleStartCampaign}
                  disabled={busyAction === "start" || !selectedCampaignId}
                  style={{ display: "flex", alignItems: "center", gap: 6 }}
                >
                  <Play size={14} />
                  <span>{busyAction === "start" ? "Starting…" : "Start Campaign Calls"}</span>
                </button>
              ) : (
                <button
                  className="button button-secondary"
                  onClick={handlePauseCampaign}
                  disabled={busyAction === "pause"}
                  style={{ display: "flex", alignItems: "center", gap: 6 }}
                >
                  <Pause size={14} />
                  <span>Pause</span>
                </button>
              )}

              <button
                className="button button-secondary"
                onClick={handleStopCampaign}
                disabled={busyAction === "stop" || selectedCampaign?.status === "COMPLETED"}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                <Square size={14} />
                <span>Stop Campaign</span>
              </button>

              <button
                className="button button-primary"
                onClick={handleDispatchNext}
                disabled={busyAction === "dispatch-next" || !selectedCampaignId}
                style={{ display: "flex", alignItems: "center", gap: 6, background: "linear-gradient(135deg, #0284c7, #0369a1)" }}
              >
                <PhoneForwarded size={14} />
                <span>{busyAction === "dispatch-next" ? "Dispatching…" : "Dispatch Next Call (Sequential)"}</span>
              </button>
            </>
          )}

          <button
            className="button button-secondary"
            onClick={() => loadTargets(selectedCampaignId)}
            disabled={targetsLoading}
            style={{ marginLeft: "auto" }}
          >
            Refresh Queue
          </button>
        </div>
      </section>

      {/* 3. ELIGIBLE TARGETS & CALL QUEUE TABLE */}
      <section className="content-card">
        <div className="section-heading">
          <div>
            <h3>Eligible Absent Students & Parent Contacts</h3>
            <p>Review contact authorization and queue status before calling. Concurrency is limited to 1 call at a time for safety.</p>
          </div>
        </div>

        {targetsLoading ? (
          <p className="empty-state">Loading campaign queue…</p>
        ) : !targets.length ? (
          <p className="empty-state">No absent student targets in this campaign. Create a campaign from the Campaigns tab.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Roll No</th>
                  <th>Student</th>
                  <th>Guardian</th>
                  <th>Phone Number</th>
                  <th>Attendance</th>
                  <th>Consent</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {targets.map((t) => {
                  const hasContact = Boolean(t.phone_number);
                  const isQueued = t.status === "QUEUED";
                  const isRinging = t.status === "RINGING";
                  const isCompleted = t.status === "COMPLETED";
                  const isFailed = t.status === "FAILED";

                  return (
                    <tr key={t.id} style={{ background: isRinging ? "rgba(56,189,248,0.08)" : undefined }}>
                      <td><strong>{t.roll_number}</strong></td>
                      <td>{t.student_name}</td>
                      <td>{t.parent_name || <span style={{ color: "#f87171" }}>No guardian saved</span>}</td>
                      <td>
                        {t.phone_number ? (
                          <code>{t.phone_number}</code>
                        ) : (
                          <span style={{ color: "#f87171", fontSize: "0.8rem" }}>Missing Phone</span>
                        )}
                      </td>
                      <td>
                        <span style={{ color: t.attendance_percentage < 75 ? "#f87171" : "#34d399", fontWeight: 600 }}>
                          {t.attendance_percentage}%
                        </span>
                      </td>
                      <td>
                        {t.contact_authorized !== false ? (
                          <span className="badge badge-emerald" style={{ fontSize: "0.7rem", padding: "2px 6px" }}>Authorized</span>
                        ) : (
                          <span className="badge badge-amber" style={{ fontSize: "0.7rem", padding: "2px 6px" }}>Opted Out</span>
                        )}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isCompleted ? "badge-emerald" : isRinging ? "badge-cyan" : isQueued ? "badge-amber" : isFailed ? "badge-rose" : "badge-gray"
                          }`}
                          style={{ padding: "3px 8px", fontSize: "0.75rem", borderRadius: 4 }}
                        >
                          {t.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          {user.permissions.includes("calls.manage") && (
                            <>
                              <button
                                className="button button-primary"
                                style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                                disabled={!hasContact || isCompleted || busyAction === `call-${t.id}`}
                                onClick={() => handleDirectDispatch(t)}
                                title="Dispatch AI voice call immediately"
                              >
                                {busyAction === `call-${t.id}` ? "Calling…" : "Call Now"}
                              </button>

                              <button
                                className="button button-secondary"
                                style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                                onClick={() => setDemoModalTarget(t)}
                                title="Run simulated test call with selectable parent response"
                              >
                                Test Demo
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

      {/* 4. MODAL: CALL ATTEMPT DETAIL & CONVERSATION TRANSCRIPT */}
      {attemptDetail && (
        <section className="content-card" style={{ border: "1px solid #38bdf8", boxShadow: "0 0 20px rgba(56,189,248,0.15)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <FileText size={20} className="text-cyan" />
              <h3 style={{ margin: 0 }}>Call Attempt & Multi-Turn Transcript Detail</h3>
            </div>
            <button
              className="button button-secondary"
              onClick={() => setAttemptDetail(null)}
              style={{ padding: "4px 10px" }}
            >
              Close
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16, background: "rgba(15,23,42,0.8)", padding: 14, borderRadius: 8, border: "1px solid #334155" }}>
            <div><span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Student:</span><br /><strong>{attemptDetail.student_name} ({attemptDetail.student_roll})</strong></div>
            <div><span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Guardian:</span><br /><strong>{attemptDetail.parent_name}</strong></div>
            <div><span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Phone Dialed:</span><br /><code>{attemptDetail.phone_number}</code></div>
            <div><span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Call Duration:</span><br /><strong>{attemptDetail.duration_seconds || 0} seconds</strong></div>
            <div><span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Execution Type:</span><br /><span className={attemptDetail.is_demo ? "badge badge-amber" : "badge badge-emerald"}>{attemptDetail.is_demo ? "DEMO CALL (SIMULATED)" : "REAL TELEPHONY CALL"}</span></div>
            <div><span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Provider SID:</span><br /><code style={{ fontSize: "0.75rem" }}>{attemptDetail.provider_call_id || "N/A"}</code></div>
          </div>

          {/* AI Analysis Result Card */}
          {attemptDetail.conversation?.analysis && (
            <div style={{ padding: 16, background: "rgba(30,41,59,0.7)", borderRadius: 8, border: "1px solid rgba(56,189,248,0.25)", marginBottom: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Bot size={18} className="text-cyan" />
                  <strong style={{ fontSize: "1rem" }}>Groq AI Response Analysis & Classification</strong>
                </div>
                <span className="badge badge-cyan" style={{ fontSize: "0.8rem", padding: "4px 8px" }}>
                  Category: {attemptDetail.conversation.analysis.category}
                </span>
              </div>
              <p style={{ margin: "6px 0", color: "#e2e8f0" }}>
                <strong>Reason Summary:</strong> {attemptDetail.conversation.analysis.summary}
              </p>
              <div style={{ display: "flex", gap: 16, fontSize: "0.85rem", color: "#94a3b8", marginTop: 8 }}>
                <span><strong>Follow-up Required:</strong> {attemptDetail.conversation.analysis.followup_required ? "YES (Added to Follow-ups)" : "NO"}</span>
                <span><strong>Model:</strong> {attemptDetail.conversation.analysis.model_name}</span>
                <span><strong>Confidence:</strong> {((attemptDetail.conversation.analysis.confidence || 0.94) * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}

          {/* Multi-turn Dialogue Transcript */}
          <div>
            <h4 style={{ margin: "0 0 10px 0" }}>Verbatim Spoken Dialogue Transcript</h4>
            {attemptDetail.conversation?.transcripts?.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: 14, background: "#0b1329", borderRadius: 8, border: "1px solid #1e293b", maxHeight: 360, overflowY: "auto" }}>
                {attemptDetail.conversation.transcripts.map((t) => {
                  const isAgent = t.speaker === "AGENT";
                  return (
                    <div
                      key={t.id}
                      style={{
                        alignSelf: isAgent ? "flex-start" : "flex-end",
                        maxWidth: "80%",
                        padding: "10px 14px",
                        borderRadius: 12,
                        background: isAgent ? "rgba(14,165,233,0.15)" : "rgba(30,41,59,0.8)",
                        border: isAgent ? "1px solid rgba(56,189,248,0.3)" : "1px solid rgba(148,163,184,0.2)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 4, fontSize: "0.75rem", color: isAgent ? "#38bdf8" : "#94a3b8" }}>
                        <strong>{isAgent ? "Agent (BBS College Voice)" : `Guardian (${attemptDetail.parent_name})`}</strong>
                        <span>Confidence: {((t.confidence || 0.95) * 100).toFixed(0)}%</span>
                      </div>
                      <div style={{ color: "#f8fafc", fontSize: "0.92rem", lineHeight: 1.4 }}>{t.text}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="empty-state">No spoken audio turns recorded for this attempt.</p>
            )}
          </div>
        </section>
      )}

      {/* 5. CALL HISTORY & AUDIT LOG TABLE */}
      <section className="content-card">
        <div className="section-heading">
          <div>
            <h3>Recent Outreach Call History</h3>
            <p>Every completed, unanswered, and failed call is recorded in the PostgreSQL database.</p>
          </div>
          <button className="button button-secondary" onClick={loadHistory} disabled={historyLoading}>
            Refresh History
          </button>
        </div>

        {!callHistory.length ? (
          <p className="empty-state">No call attempts recorded yet. Queue or dispatch a call to begin.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Student</th>
                  <th>Guardian</th>
                  <th>Phone Number</th>
                  <th>Duration</th>
                  <th>Mode</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {callHistory.map((h) => (
                  <tr key={h.id}>
                    <td><small>{h.started_at ? new Date(h.started_at).toLocaleTimeString() : "Pending"}</small></td>
                    <td><strong>{h.student_name}</strong> {h.student_roll && `(${h.student_roll})`}</td>
                    <td>{h.parent_name}</td>
                    <td><code>{h.phone_number}</code></td>
                    <td>{h.duration_seconds ? `${h.duration_seconds}s` : "—"}</td>
                    <td>
                      <span className={h.is_demo ? "badge badge-amber" : "badge badge-emerald"} style={{ fontSize: "0.7rem", padding: "2px 6px" }}>
                        {h.is_demo ? "DEMO" : "REAL"}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${h.status === "COMPLETED" ? "badge-emerald" : h.status === "RINGING" ? "badge-cyan" : "badge-rose"}`} style={{ fontSize: "0.75rem", padding: "2px 6px" }}>
                        {h.status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="button button-secondary"
                        style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                        onClick={() => viewAttemptDetails(h.id)}
                      >
                        View Transcript
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 6. MODAL: RUN CONTROLLED DEMO SIMULATION */}
      {demoModalTarget && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "grid", placeItems: "center", zIndex: 9999, padding: 20 }}>
          <div style={{ background: "#0f172a", border: "1px solid #38bdf8", borderRadius: 12, padding: 24, maxWidth: 520, width: "100%", boxShadow: "0 10px 40px rgba(0,0,0,0.8)" }}>
            <h3 style={{ margin: "0 0 8px 0" }}>Simulate Demonstration Voice Call</h3>
            <p className="call-safety-note" style={{ marginBottom: 16 }}>
              Runs the full BBS College Hindi conversational state machine and Groq AI classifier offline. Preserves transcripts and follow-ups in PostgreSQL.
            </p>

            <div style={{ marginBottom: 12, fontSize: "0.9rem" }}>
              <div><strong>Target:</strong> {demoModalTarget.student_name} (Roll: {demoModalTarget.roll_number})</div>
              <div><strong>Guardian:</strong> {demoModalTarget.parent_name || "Guardian"} · {demoModalTarget.phone_number}</div>
            </div>

            <label style={{ display: "block", marginBottom: 14 }}>
              <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Parent Response Scenario:</span>
              <select
                value={demoPreset}
                onChange={(e) => setDemoPreset(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", background: "#1e293b", border: "1px solid #334155", color: "#f8fafc", borderRadius: 6, marginTop: 4 }}
              >
                <option value="MEDICAL_REASON">Medical Reason (Fever / Sick / Hospital)</option>
                <option value="CALLBACK_REQUESTED">Callback Requested (Busy at work, call tomorrow morning)</option>
                <option value="WILL_ATTEND">Will Attend (Delayed by bus/transit, arriving in 15 mins)</option>
                <option value="OUT_OF_STATION">Leave / Out of Station (Attending family function)</option>
                <option value="WRONG_NUMBER">Wrong Number (Identity verification fails closed)</option>
                <option value="DISPUTED">Disputed Attendance (Parent claims student went to college)</option>
              </select>
            </label>

            <label style={{ display: "block", marginBottom: 18 }}>
              <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Or Enter Custom Parent Hindi/Hinglish Utterance:</span>
              <input
                type="text"
                placeholder="e.g., Uski tabiyat kharab thi, bukhar tha..."
                value={demoCustomReply}
                onChange={(e) => setDemoCustomReply(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", background: "#1e293b", border: "1px solid #334155", color: "#f8fafc", borderRadius: 6, marginTop: 4 }}
              />
            </label>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                className="button button-secondary"
                onClick={() => setDemoModalTarget(null)}
                disabled={busyAction === "running-demo"}
              >
                Cancel
              </button>
              <button
                className="button button-primary"
                onClick={handleRunDemoSimulation}
                disabled={busyAction === "running-demo"}
              >
                {busyAction === "running-demo" ? "Simulating Call & Analyzing…" : "Execute Demo Call"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. COLLAPSIBLE FACULTY VOICE ASSISTANT TOOL */}
      <section className="content-card" style={{ background: "rgba(15,23,42,0.4)" }}>
        <div
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
          onClick={() => setShowVoiceCommands(!showVoiceCommands)}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Mic size={18} className="text-cyan" />
            <h4 style={{ margin: 0 }}>Faculty Voice Commands Tool (Administrative Convenience)</h4>
          </div>
          <button className="button button-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }}>
            {showVoiceCommands ? "Hide Tool" : "Open Tool"}
          </button>
        </div>

        {showVoiceCommands && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid rgba(51,65,85,0.5)" }}>
            <p className="call-safety-note">
              Teachers can speak commands in Hindi or English (e.g., &quot;Roll 101 absent&quot;, &quot;Mark 102 present&quot;, or &quot;Kiska attendance 75 se kam hai&quot;).
            </p>
            <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
              <button
                className={`button ${isListening ? "button-primary" : "button-secondary"}`}
                onClick={toggleSpeechRecognition}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                <span>{isListening ? "Listening…" : "Speak Command"}</span>
              </button>
              <input
                type="text"
                placeholder="Or type voice command e.g. 'roll 101 absent' or 'kiska attendance 75 se kam hai'..."
                value={voiceQuery}
                onChange={(e) => setVoiceQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleVoiceCommand()}
                style={{ flex: 1, padding: "8px 12px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", borderRadius: 6 }}
              />
              <button className="button button-primary" onClick={() => handleVoiceCommand()}>
                Execute
              </button>
            </div>

            {voiceFeedback && (
              <div style={{ marginTop: 12, padding: 12, background: "rgba(30,41,59,0.7)", borderRadius: 6, border: "1px solid #334155" }}>
                <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Spoken Response:</div>
                <div style={{ color: "#38bdf8", fontWeight: 500, margin: "4px 0" }}>{voiceFeedback.spoken_response}</div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
