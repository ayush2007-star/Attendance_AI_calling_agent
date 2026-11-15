const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
const TOKEN_KEY = "attendance-ai.access-token";
const EXPIRY_KEY = "attendance-ai.token-expiry";

export function saveToken(token, expiresIn) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(EXPIRY_KEY, String(Date.now() + expiresIn * 1000));
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(EXPIRY_KEY);
}

export function getToken() {
  const token = sessionStorage.getItem(TOKEN_KEY);
  const expiresAt = Number(sessionStorage.getItem(EXPIRY_KEY));
  if (!token || !expiresAt || Date.now() >= expiresAt) {
    clearToken();
    return null;
  }
  return token;
}

async function request(path, { method = "GET", body, formData = false } = {}) {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (body && !formData) headers.set("Content-Type", "application/json");

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: formData ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Cannot reach the server. Check that the backend is running.");
  }

  const responseBody = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = responseBody?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(", ")
      : detail || `Request failed (${response.status})`;
    if (response.status === 401) clearToken();
    throw new Error(message);
  }
  return responseBody;
}

export async function signIn(username, password) {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  }).catch(() => {
    throw new Error("Cannot reach the server. Check that the backend is running.");
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(result?.detail || "Sign-in failed. Check your username and password.");
  }
  saveToken(result.access_token, result.expires_in);
  return request("/auth/me");
}

export const api = {
  currentUser: () => request("/auth/me"),
  changePassword: (data) => request("/auth/change-password", { method: "POST", body: data }),
  dashboard: () => request("/dashboard/summary"),
  students: () => request("/students"),
  createStudent: (data) => request("/students", { method: "POST", body: data }),
  classes: () => request("/classes"),
  createClass: (data) => request("/classes", { method: "POST", body: data }),
  scopes: () => request("/scopes"),
  createScope: (data) => request("/scopes", { method: "POST", body: data }),
  users: () => request("/users"),
  createUser: (data) => request("/users", { method: "POST", body: data }),
  setUserActive: (id, isActive) => request(`/users/${id}`, { method: "PATCH", body: { is_active: isActive } }),
  resetUserPassword: (id, newPassword) => request(`/users/${id}/reset-password`, { method: "POST", body: newPassword ? { new_password: newPassword } : undefined }),
  importAttendance: (data) =>
    request("/attendance-imports", { method: "POST", body: data, formData: true }),
  importStudents: (data) =>
    request("/student-imports", { method: "POST", body: data, formData: true }),
  createCampaign: (data) => request("/campaigns", { method: "POST", body: data }),
  campaigns: () => request("/campaigns"),
  campaignDetails: (id) => request(`/campaigns/${id}`),
  campaignTargets: (id) => request(`/campaigns/${id}/targets`),
  startCampaign: (id) => request(`/campaigns/${id}/start`, { method: "POST" }),
  pauseCampaign: (id) => request(`/campaigns/${id}/pause`, { method: "POST" }),
  stopCampaign: (id) => request(`/campaigns/${id}/stop`, { method: "POST" }),
  dispatchNextCampaignTarget: (id) => request(`/campaigns/${id}/dispatch-next`, { method: "POST" }),

  // Real Telephony & Calling Operations
  queueCampaignTarget: (id) => request(`/calls/targets/${id}/queue`, { method: "POST" }),
  dispatchTargetDirect: (id) => request(`/calls/dispatch-target/${id}`, { method: "POST" }),
  callAttempts: (params = {}) => {
    const q = new URLSearchParams();
    if (params.campaign_id) q.append("campaign_id", params.campaign_id);
    if (params.status) q.append("status", params.status);
    if (params.student_id) q.append("student_id", params.student_id);
    if (params.limit) q.append("limit", params.limit);
    const qs = q.toString();
    return request(`/calls/attempts${qs ? `?${qs}` : ""}`);
  },
  callAttemptDetail: (id) => request(`/calls/attempts/${id}`),
  voiceServiceStatus: () => request("/calls/service-status"),
  simulateDemoCall: (data) => request("/calls/simulate-demo", { method: "POST", body: data }),

  // Follow-ups
  followups: (params = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.append("status", params.status);
    if (params.priority) q.append("priority", params.priority);
    if (params.student_id) q.append("student_id", params.student_id);
    const qs = q.toString();
    return request(`/followups${qs ? `?${qs}` : ""}`);
  },
  updateFollowupStatus: (id, status) => request(`/followups/${id}/status`, { method: "PATCH", body: { status } }),

  // Parents / Guardians
  parents: (params = {}) => {
    const q = new URLSearchParams();
    if (params.search) q.append("search", params.search);
    const qs = q.toString();
    return request(`/parents${qs ? `?${qs}` : ""}`);
  },
  createParent: (data) => request("/parents", { method: "POST", body: data }),
  updateParent: (id, data) => request(`/parents/${id}`, { method: "PATCH", body: data }),
  linkStudentParent: (data) => request("/student-parents", { method: "POST", body: data }),

  // Reports
  reportsSummary: () => request("/reports/summary"),

  // 2026 Live Roll Call Terminal
  attendanceList: (classId, dateStr) => {
    const params = new URLSearchParams();
    if (classId) params.append("class_id", classId);
    if (dateStr) params.append("attendance_date", dateStr);
    return request(`/attendance?${params.toString()}`);
  },
  saveBulkAttendance: (data) => request("/attendance/bulk", { method: "POST", body: data }),
  quickToggleAttendance: (data) => request("/attendance/quick-toggle", { method: "POST", body: data }),

  // 2026 ML Risk & Predictive Analytics
  mlRiskAnalysis: (classId, riskTier, search) => {
    const params = new URLSearchParams();
    if (classId) params.append("class_id", classId);
    if (riskTier) params.append("risk_tier", riskTier);
    if (search) params.append("search", search);
    return request(`/ml/risk-analysis?${params.toString()}`);
  },

  // 2026 Voice Agent & Telephony Studio
  voiceCommand: (command, classId) => request("/voice/parse-command", { method: "POST", body: { command, class_id: classId } }),
  simulateVoiceCall: (studentId, reasonPreset) =>
    request("/voice/simulate-call", { method: "POST", body: { student_id: studentId, reason_preset: reasonPreset } }),
};
