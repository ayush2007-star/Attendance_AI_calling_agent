# Attendance dashboard

This React/Vite application provides the college attendance dashboard. Sign-in,
classes, students, attendance imports, dashboard summary, and campaign
eligibility snapshots use the FastAPI backend. Campaign creation does not
place calls.

## Development

From this directory:

```powershell
npm ci
npm run dev
```

Vite prints the local development URL. Build and inspect the production bundle
with:

```powershell
npm run lint
npm run build
npm run preview
```

`npm run build` writes to `dist/`. There is currently no automated
browser/component test script; the repository CI runs backend tests and
frontend lint/build checks.

## Integration boundary

The backend is the source of truth for users, permissions, academic scope,
students, attendance, campaigns, and calls. Do not treat frontend role
checks or local state as authorization or persistence. See
[`../docs/PROJECT_GUIDE.md`](../docs/PROJECT_GUIDE.md) and
[`../docs/BACKEND_ARCHITECTURE_GUIDE.md`](../docs/BACKEND_ARCHITECTURE_GUIDE.md)
before adding API calls or changing permission-sensitive screens.
