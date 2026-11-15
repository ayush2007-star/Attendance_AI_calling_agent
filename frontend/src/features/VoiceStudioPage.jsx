import { useEffect, useState, useRef, useCallback } from "react";
import {
  Mic,
  MicOff,
  PhoneCall,
  Volume2,
  Sparkles,
  Bot,
  User,
  Play,
  Headphones,
  Radio,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api/client";

export default function VoiceStudioPage({ initialStudentId }) {
  const [activeTab, setActiveTab] = useState(initialStudentId ? "SIMULATOR" : "ASSISTANT");

  // Mode 1: Voice Assistant State
  const [isListening, setIsListening] = useState(false);
  const [voiceQuery, setVoiceQuery] = useState("");
  const [conversationHistory, setConversationHistory] = useState([
    {
      role: "agent",
      text: "Namaste! Main aapka AI Attendance Voice Assistant hoon. Aap bolkar attendance mark kar sakte hain ya students ka record pooch sakte hain.",
      time: "Just now",
    },
  ]);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Mode 2: Call Simulator State
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState(initialStudentId || "");
  const [reasonPreset, setReasonPreset] = useState("MEDICAL_REASON");
  const [callInProgress, setCallInProgress] = useState(false);
  const [callResult, setCallResult] = useState(null);
  const audioRef = useRef(null);

  const loadStudents = useCallback(async () => {
    try {
      const data = await api.students();
      setStudents(data);
      if (data.length > 0 && !selectedStudentId) {
        setSelectedStudentId(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }, [selectedStudentId]);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  // Speak text using browser speech synthesis
  function speakResponse(text) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "hi-IN";
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }

  // Web Speech API Voice Recognition
  function toggleListening() {
    if (isListening) {
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Web Speech API is not supported in this browser. You can type commands below!");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "hi-IN";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = async (event) => {
      const transcript = event.results[0][0].transcript;
      setVoiceQuery(transcript);
      setIsListening(false);
      await executeVoiceCommand(transcript);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  }

  async function executeVoiceCommand(textToRun) {
    const query = textToRun || voiceQuery;
    if (!query.trim()) return;

    const userEntry = {
      role: "user",
      text: query,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setConversationHistory((prev) => [...prev, userEntry]);
    setVoiceQuery("");

    try {
      const res = await api.voiceCommand(query);
      const agentEntry = {
        role: "agent",
        text: res.spoken_response,
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        intent: res.intent,
      };

      setConversationHistory((prev) => [...prev, agentEntry]);
      speakResponse(res.spoken_response);
    } catch (err) {
      setConversationHistory((prev) => [
        ...prev,
        {
          role: "agent",
          text: `Command execute nahi ho saka: ${err.message}`,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  }

  // Mode 2: Run Telephony Simulator
  async function triggerSimulatedCall() {
    if (!selectedStudentId) return;
    setCallInProgress(true);
    setCallResult(null);

    try {
      const result = await api.simulateVoiceCall(selectedStudentId, reasonPreset);
      setCallResult(result);

      if (audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play().catch(() => {});
      }
    } catch (err) {
      alert(`Call simulation failed: ${err.message}`);
    } finally {
      setCallInProgress(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* Hidden Audio Element for Neural Voice Playback */}
      <audio ref={audioRef} src="/audio/test_hindi_greeting.mp3" preload="auto" />

      {/* Studio Header & Mode Switcher */}
      <div className="bento-card glow-cyan" style={{ padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="brand-hologram-cube" style={{ width: 48, height: 48, borderRadius: 14 }}>
              <Radio size={24} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="role-clearance-pill staff" style={{ fontSize: 10, padding: "2px 8px" }}>
                  Demo only · no live calls
                </span>
                <span style={{ fontSize: 10, color: "#64748b" }}>Swara Neural Hindi Engine</span>
              </div>
              <h2 style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800, color: "#fff" }}>
                AI Voice Agent & Telephony Studio · 2026
              </h2>
              <p style={{ margin: "3px 0 0", fontSize: 12, color: "#94a3b8" }}>
                Voice assistant tools and scripted parent-call previews
              </p>
            </div>
          </div>

          {/* Mode Switch Tabs */}
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setActiveTab("ASSISTANT")}
              className={`nav-pill ${activeTab === "ASSISTANT" ? "active" : ""}`}
              style={{ fontSize: 12, padding: "8px 16px" }}
            >
              <Mic size={14} /> Voice Assistant
            </button>
            <button
              onClick={() => setActiveTab("SIMULATOR")}
              className={`nav-pill ${activeTab === "SIMULATOR" ? "active" : ""}`}
              style={{ fontSize: 12, padding: "8px 16px" }}
            >
              <PhoneCall size={14} /> Call Preview (Demo)
            </button>
          </div>
        </div>
      </div>

      {/* MODE A: LIVE VOICE ASSISTANT */}
      {activeTab === "ASSISTANT" && (
        <div className="bento-grid">
          {/* Conversation Stream */}
          <div className="bento-card col-span-8" style={{ padding: 24, gridColumn: "span 8" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 750, color: "#fff", display: "flex", alignItems: "center", gap: 8 }}>
                <Bot size={18} color="#38bdf8" /> Conversational Audio Terminal
              </h3>
              {isSpeaking && (
                <span style={{ fontSize: 11, color: "#38bdf8", display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <Volume2 size={14} className="pulse-beacon" /> Speaking Hindi Audio…
                </span>
              )}
            </div>

            <div
              style={{
                height: 380,
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: 14,
                padding: "12px 6px",
              }}
            >
              {conversationHistory.map((msg, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    gap: 12,
                    alignItems: "flex-start",
                    alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                    maxWidth: "85%",
                  }}
                >
                  {msg.role === "agent" && (
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: 10,
                        background: "rgba(6, 182, 212, 0.15)",
                        color: "#38bdf8",
                        display: "grid",
                        placeItems: "center",
                        flexShrink: 0,
                      }}
                    >
                      <Bot size={18} />
                    </div>
                  )}

                  <div
                    style={{
                      background: msg.role === "user" ? "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)" : "rgba(30, 41, 59, 0.6)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      borderRadius: 14,
                      padding: "12px 16px",
                      color: "#fff",
                      fontSize: 13,
                      lineHeight: 1.5,
                      boxShadow: msg.role === "user" ? "0 4px 15px rgba(37, 99, 235, 0.3)" : "none",
                    }}
                  >
                    <div>{msg.text}</div>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 6, gap: 10 }}>
                      <span style={{ fontSize: 9, color: "rgba(255, 255, 255, 0.5)" }}>{msg.time}</span>
                      {msg.role === "agent" && (
                        <button
                          onClick={() => speakResponse(msg.text)}
                          style={{
                            background: "transparent",
                            border: 0,
                            color: "#38bdf8",
                            cursor: "pointer",
                            fontSize: 10,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 3,
                          }}
                        >
                          <Volume2 size={11} /> Replay
                        </button>
                      )}
                    </div>
                  </div>

                  {msg.role === "user" && (
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: 10,
                        background: "var(--grad-violet)",
                        color: "#fff",
                        display: "grid",
                        placeItems: "center",
                        flexShrink: 0,
                      }}
                    >
                      <User size={18} />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Input Bar with Mic */}
            <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 10 }}>
              <button
                onClick={toggleListening}
                className={`btn-quantum ${isListening ? "btn-quantum-violet" : "btn-quantum-primary"}`}
                style={{
                  borderRadius: "50%",
                  width: 48,
                  height: 48,
                  padding: 0,
                  flexShrink: 0,
                }}
                title={isListening ? "Listening… click to stop" : "Click to speak via microphone"}
              >
                {isListening ? <MicOff size={20} /> : <Mic size={20} />}
              </button>

              <input
                type="text"
                placeholder={isListening ? "Sun rahi hoon… boliye (e.g. Roll 102 present)" : "Type or speak instruction in Hindi/English…"}
                value={voiceQuery}
                onChange={(e) => setVoiceQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && executeVoiceCommand()}
                style={{
                  flex: 1,
                  background: "rgba(15, 23, 42, 0.9)",
                  border: isListening ? "1px solid #38bdf8" : "1px solid rgba(255, 255, 255, 0.12)",
                  color: "#fff",
                  borderRadius: 12,
                  padding: "12px 16px",
                  fontSize: 13,
                  boxShadow: isListening ? "0 0 15px rgba(56, 189, 248, 0.3)" : "none",
                }}
              />

              <button
                onClick={() => executeVoiceCommand()}
                className="btn-quantum btn-quantum-primary"
                style={{ padding: "10px 18px" }}
              >
                Send
              </button>
            </div>
          </div>

          {/* Quick Voice Chips */}
          <div className="bento-card col-span-4" style={{ padding: 22, gridColumn: "span 4" }}>
            <h4 style={{ margin: "0 0 12px", fontSize: 13, fontWeight: 700, color: "#fff" }}>
              Suggested Voice Commands
            </h4>
            <p style={{ margin: "0 0 16px", fontSize: 11, color: "#94a3b8" }}>
              Click any chip to test the voice intelligence engine instantly:
            </p>

            <div style={{ display: "grid", gap: 10 }}>
              {[
                "Roll 101 present mark karo",
                "Roll 105 absent mark karo",
                "Kiska attendance 75 se kam hai?",
                "Director summary batao",
                "Aaj kitne students absent hain?",
              ].map((cmd, i) => (
                <button
                  key={i}
                  onClick={() => executeVoiceCommand(cmd)}
                  className="clearance-card-btn"
                  style={{ fontSize: 12, padding: "10px 12px" }}
                >
                  <span style={{ color: "#38bdf8" }}>🎙️</span>
                  <span>{cmd}</span>
                </button>
              ))}
            </div>

            <div
              style={{
                marginTop: 20,
                padding: 14,
                borderRadius: 12,
                background: "rgba(99, 102, 241, 0.08)",
                border: "1px solid rgba(99, 102, 241, 0.2)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#c084fc", fontWeight: 700 }}>
                <Sparkles size={14} /> Bilingual NLP Parser
              </div>
              <p style={{ margin: "6px 0 0", fontSize: 11, color: "#cbd5e1", lineHeight: 1.5 }}>
                Understands natural mixed Hinglish sentences, roll numbers, and attendance keywords without fixed syntax.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* MODE B: PARENT CALL SIMULATOR */}
      {activeTab === "SIMULATOR" && (
        <div className="bento-grid">
          {/* Dialer Configuration Panel */}
          <div className="bento-card col-span-5" style={{ padding: 24, gridColumn: "span 5" }}>
            <h3 style={{ margin: "0 0 14px", fontSize: 16, fontWeight: 750, color: "#fff" }}>
              Autonomous Outreach Setup
            </h3>

            <div style={{ display: "grid", gap: 16 }}>
              <label style={{ display: "grid", gap: 6, fontSize: 12, color: "#94a3b8" }}>
                <span>Select Absent Student:</span>
                <select
                  value={selectedStudentId}
                  onChange={(e) => setSelectedStudentId(e.target.value)}
                  style={{
                    background: "rgba(15, 23, 42, 0.9)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    color: "#fff",
                    borderRadius: 10,
                    padding: "10px 14px",
                    fontSize: 13,
                  }}
                >
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      Roll #{s.roll_number} · {s.first_name} {s.last_name || ""} ({s.student_code})
                    </option>
                  ))}
                </select>
              </label>

              <label style={{ display: "grid", gap: 6, fontSize: 12, color: "#94a3b8" }}>
                <span>Choose a scripted scenario:</span>
                <select
                  value={reasonPreset}
                  onChange={(e) => setReasonPreset(e.target.value)}
                  style={{
                    background: "rgba(15, 23, 42, 0.9)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    color: "#fff",
                    borderRadius: 10,
                    padding: "10px 14px",
                    fontSize: 13,
                  }}
                >
                  <option value="MEDICAL_REASON">Medical Reason (Fever/Doctor visit)</option>
                  <option value="WILL_ATTEND">Will Attend (Bus delay / arriving late)</option>
                  <option value="OUT_OF_STATION">Family Function / Out of Station</option>
                  <option value="WRONG_NUMBER">Wrong Number / Unrecognized</option>
                </select>
              </label>

              <button
                onClick={triggerSimulatedCall}
                disabled={callInProgress || !selectedStudentId}
                className="btn-quantum btn-quantum-primary"
                style={{ padding: "13px", marginTop: 8 }}
              >
                <PhoneCall size={16} />
                {callInProgress ? "Preparing preview…" : "Preview simulated dialogue"}
              </button>

              <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: 14, borderRadius: 10, fontSize: 11, color: "#94a3b8" }}>
                <strong>Demo only:</strong> No phone number is dialed and scripted replies are not saved as real call outcomes.
              </div>
            </div>
          </div>

          {/* Call Output & Transcript Terminal */}
          <div className="bento-card col-span-7" style={{ padding: 24, gridColumn: "span 7" }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 750, color: "#fff", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>Scripted Conversation Preview</span>
              {callResult && (
                <span className="role-clearance-pill staff" style={{ fontSize: 10, padding: "3px 8px" }}>
                  Simulation only
                </span>
              )}
            </h3>

            {!callResult && !callInProgress && (
              <div style={{ textAlign: "center", padding: "60px 20px", color: "#64748b" }}>
                <Headphones size={36} style={{ marginBottom: 12, opacity: 0.5 }} />
                <p style={{ margin: 0, fontSize: 13 }}>
                  Select a student and choose a scripted scenario to preview the conversation.
                </p>
              </div>
            )}

            {callInProgress && (
              <div style={{ textAlign: "center", padding: "60px 20px", color: "#38bdf8" }}>
                <Radio size={36} className="pulse-beacon" style={{ marginBottom: 12 }} />
                <p style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>Preparing a scripted preview…</p>
                <span style={{ fontSize: 11, color: "#94a3b8" }}>No call is being placed</span>
              </div>
            )}

            {callResult && (
              <div style={{ display: "grid", gap: 14 }}>
                {/* AI Classification Pill Strip */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: 10,
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: "rgba(16, 185, 129, 0.1)",
                    border: "1px solid rgba(16, 185, 129, 0.25)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#34d399", fontWeight: 700 }}>
                    <ShieldCheck size={16} />
                    Category: {callResult.extracted_intent.category}
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8" }}>
                    Action: <strong style={{ color: "#fff" }}>{callResult.extracted_intent.action_taken}</strong> · Sentiment: {callResult.extracted_intent.sentiment}
                  </div>
                </div>

                {/* Dialog Turns */}
                <div style={{ display: "grid", gap: 10, maxHeight: 300, overflowY: "auto", paddingRight: 4 }}>
                  {callResult.dialogue.map((turn, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: turn.speaker.includes("AI Voice") ? "rgba(6, 182, 212, 0.08)" : "rgba(255, 255, 255, 0.04)",
                        border: "1px solid rgba(255, 255, 255, 0.06)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                        <strong style={{ fontSize: 11, color: turn.speaker.includes("AI Voice") ? "#38bdf8" : "#fbbf24" }}>
                          {turn.speaker}
                        </strong>
                        <span style={{ fontSize: 10, color: "#64748b" }}>{turn.time}</span>
                      </div>
                      <p style={{ margin: 0, fontSize: 12, color: "#e2e8f0", lineHeight: 1.5 }}>
                        {turn.text}
                      </p>
                    </div>
                  ))}
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 11, color: "#64748b", marginTop: 4 }}>
                  <span>Synthetic preview only · not saved as an actual call</span>
                  <button
                    onClick={() => {
                      if (audioRef.current) {
                        audioRef.current.currentTime = 0;
                        audioRef.current.play().catch(() => {});
                      }
                    }}
                    style={{
                      background: "transparent",
                      border: 0,
                      color: "#38bdf8",
                      cursor: "pointer",
                      fontSize: 11,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <Play size={12} /> Play Neural Audio Recording
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
