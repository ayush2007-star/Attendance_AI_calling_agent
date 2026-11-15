# Attendwise: Project Learning Guide (Simple Hinglish)

Yeh guide college ke 3rd-year student ke liye hai. Aim hai ki tum project
khud chala sako, chhote changes kar sako, aur kisi ko simple language me
samjha sako. Ek saath sab yaad karne ki zaroorat nahi: pehle run karo, phir
ek feature ko browser se database tak trace karo.

> **Important sachchai:** app ke core screens API se data lete hain, lekin
> yeh complete production product abhi nahi hai. ML service abhi scaffold
> hai, aur campaign se real phone call nahi hota. Real student/parent data ya
> calls se pehle college ki permission aur privacy review zaroori hai.

## 1. Ek minute me project

Attendwise college ke students, classes aur attendance ko manage karne ka
web app hai:

```text
Browser (React)
  -> HTTP API request
FastAPI backend (rules + permission checks)
  -> SQL query
PostgreSQL database
```

Simple example: admin student form fill karta hai -> React form values bhejta
hai -> FastAPI request check karta hai -> service student save karti hai ->
PostgreSQL row save hoti hai -> API saved student response bhejti hai ->
browser list me student dikhata hai.

Backend **source of truth** hai: browser ko maan lena nahi chahiye ki user ko
permission hai. Har private action backend dobara authorize karta hai.

## 2. Project chalana aur check karna

Sabse aasan local demo: root [README](../README.md) me Docker instructions
follow karo. Docker Desktop chahiye. Pehli baar administrator banana:

```powershell
docker compose --env-file .\deploy\.env -f .\deploy\compose.yml exec backend python -m app.bootstrap_admin
```

Phir browser me `http://localhost:8080` kholo. **Compose file database
migrations startup par chalati hai.** Secrets ke liye `deploy/.env` banao;
example file me placeholders ko asli random values se badlo.

### Docker ke bina development

Python 3.13, Node.js 22, aur PostgreSQL install karo. `backend/.env.example`
ko `backend/.env` me copy karke database URL aur random JWT secret bharo.
Backend terminal:

```powershell
Set-Location .\backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.bootstrap_admin
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Front-end ke liye **doosra terminal** kholo:

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

Vite terminal jo URL de, use browser me kholo. Backend ka API explorer
`http://127.0.0.1:8000/docs` hai. API explorer development me endpoints ko
dekhne aur manually test karne ke kaam aata hai.

### Tests aur build

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m pytest tests -q

Set-Location ..\frontend
npm run lint
npm run build

Set-Location ..\voice-agent
.\.venv\Scripts\python.exe -m pytest tests -q
```

Test pass ka matlab tested code pass hua. Iska matlab yeh nahi ki Twilio,
Groq, database production setup, permissions, backup, ya har UI flow real
environment me verify ho gaya. CI har PR par main test/build commands chalata
hai.

## 3. Folders ka map

| Path | Kya rakha hai | Kab yahan jaana hai |
|---|---|---|
| `frontend/src/App.jsx` | App shell, navigation, login state | Naya menu/page jodna ho |
| `frontend/src/api/client.js` | API URL, token, HTTP errors, endpoint methods | Backend request badalni ho |
| `frontend/src/features/` | Dashboard, students, classes, import, campaign screens | Kisi ek UI feature ko badalna ho |
| `frontend/src/styles/workspace.css` | Main app ka responsive design | Colors/layout/mobile view badalna ho |
| `backend/app/api/v1/routes/` | HTTP endpoints; request kahan aata hai | Naya API route banana ho |
| `backend/app/schemas/` | Request/response fields aur validation | API data format badalna ho |
| `backend/app/services/` | Business logic aur database queries | Rule ya calculation badalni ho |
| `backend/app/models/` | PostgreSQL tables aur columns ka Python model | Naya database field/table ho |
| `backend/migrations/versions/` | Database schema ke numbered changes | Table/column add ya alter karna ho |
| `backend/app/core/` | Settings, password/JWT, common backend setup | Security/configuration badalni ho |
| `backend/tests/` | Backend ke automatic tests | Behavior change ke saath regression test |
| `deploy/` | Docker Compose, Nginx config aur local deployment example | Run/deploy setup badalna ho |
| `docs/` | Architecture, learning aur release guides | Project explain karna ho |
| `ml/` | Experimental feature/schema files; live service nahi | Future ML development |
| `voice-agent/` | Alag Twilio/AI voice app; campaign se disconnected | Approved voice-service development |

### Ek file me sab code kyun nahi?

Alag responsibility se change aasaan hota hai. UI badalna ho to database
service ko bina wajah nahi chhedte. DB column badalna ho to migration banate
hain. `frontend/src/features/StudentsPage.jsx` ka form ya list usi feature
ke paas hai; common HTTP behavior ek jagah `api/client.js` me hai.

## 4. Coding ke basic concepts

### Python function

Function ek naam wala kaam hai. Input parameters le sakta hai aur result
return kar sakta hai:

```python
def attendance_status(percent: float, threshold: float = 75) -> str:
    if percent >= threshold:
        return "ELIGIBLE"
    return "FOLLOW_UP"
```

`def` function banata hai; `percent` input hai; `-> str` batata hai output
string expected hai. Is project me route aur service bhi Python functions
hain. Pehle function ka input, output, aur side effect (DB write?) samjho.

### Python modules aur imports

Har `.py` file ek module hai. `from app.models.student import Student`
ka matlab doosri file me bana `Student` model use karna. Import path
`backend/app/` se package structure follow karta hai.

### Type hints

`student_id: UUID`, `db: Session`, `-> list[Student]` developer aur tools ko
expected type batate hain. Type hint khud runtime validation nahi hota;
request validation ke liye Pydantic schema use hoti hai.

### FastAPI route

Route HTTP URL ko Python function se jodta hai. Example dekhne ke liye
`backend/app/api/v1/routes/students.py` kholo:

- `@router.get("")`: student list URL par GET request.
- `@router.post("")`: naya student banane ke liye POST.
- `Depends(...)`: common cheez (database session ya current user) mangta
  hai.
- `response_model=StudentResponse`: browser ko bhejne wala data format.

Route ko patla rakho. Validation schema me, actual rule service me, database
table model me rakho.

### Pydantic schema

Schema API ke parcel ka label/form jaisa hai. `StudentCreate` batata hai
kaunse fields incoming request me hone chahiye. Pydantic invalid type ya
missing required field ko route chalne se pehle reject karta hai.

### Database, table, row, primary key

- **Database:** project ka organized permanent data store.
- **Table:** ek type ki cheezon ki list, jaise `students`.
- **Row:** ek student ka stored record.
- **Column:** record ki field, jaise `student_code`.
- **Primary key (`id`):** har record ka unique internal ID.
- **Foreign key:** ek table ka doosri table ke record se link; student ka
  `class_id` use karta hai.
- **Transaction:** multiple DB changes ko ek logical operation me commit ya
  rollback karna.

Passwords plain text me nahi rakhte: `password_hash` me one-way hash save
hota hai. API/database secrets kisi source file me nahi rakhte.

### SQLAlchemy model aur service

`backend/app/models/student.py` Python class ke zariye table batata hai.
Service me `db.execute(...)`, `db.add(...)`, `db.commit()` database padhne,
nayi row add karne aur save karne ke liye hain. Service business logic ki
jagah hai: scope check, eligibility rule, duplicate handling, etc.

### Migration: purane data ko bachate hue schema update

Python model badalne se pehle se bani database table khud nahi badalti.
Alembic migration database ko version-by-version update karti hai:

1. `backend/app/models/` me schema change samjho/likho.
2. Nayi migration file `backend/migrations/versions/` me banao.
3. Migration `upgrade()` aur rollback (`downgrade()`) check karo.
4. Disposable local DB par `alembic upgrade head` chalao aur tests run karo.
5. Existing migration ko edit/delete mat karo; already deployed DB us par
   depend kar sakta hai.

### HTTP, JSON, status code

Frontend request method + URL + data bhejta hai. API status code aur JSON
reply deti hai. `200` ka matlab request successful, `201` naya record bana,
`401` sign-in chahiye, `403` permission nahi, `404` record nahi mila,
`422` input validate nahi hua, `500` server error. Error ko chupane ke bajay
screen par samajhne layak message dikhao.

### React component, state, props, effect

- **Component:** reusable UI function, jaise `LoginPage` ya `StudentsPage`.
- **Props:** parent se child component ko diya data/function.
- **State:** screen ka badalne wala data; `useState` se banta hai.
- **Effect:** `useEffect` se screen aane par API jaise external system se
  baat karna. UI ko render karna ho to effect ki jagah normal JSX/state rakho.
- **Event:** form submit/button click par function chalna.

Har feature component `frontend/src/features/` me hai. Common request
`api/client.js` me add karo; page me `fetch` copy/paste mat karo.

### Authentication aur authorization

- **Authentication:** “tum kaun ho?” — username/password par token milta hai.
- **Authorization:** “tum yeh kar sakte ho?” — API permission/scope check
  karti hai.
- **JWT access token:** signed temporary login proof; token session storage
  me expiry ke saath rakha jaata hai.
- **Scope:** kis department/class ke data tak pahunch hai.

React me menu chhupana security nahi. Backend ki `require_permission(...)`
aur service scope checks asli barrier hain. Private action ke liye naye API
route me un checks ko zaroor samjho.

### File upload aur validation

File extension, content parser, class scope, student ID, duplicates aur
10 MB maximum ko backend validate karta hai. Browser ka `accept=` sirf
convenience hai; attacker usse bypass kar sakta hai. Server-side check
mandatory hai.

## 5. Data request ko code me trace karna

Browser me **Students** kholne se shuru karo:

1. UI: `frontend/src/features/StudentsPage.jsx` API ka `api.students()` call
   karta hai.
2. API client: `frontend/src/api/client.js` `/students` GET aur bearer token
   bhejta hai.
3. Router: `backend/app/api/v1/routes/students.py` URL sambhalta hai.
4. Permission: `require_permission("student.read")` access check karta hai.
5. Service: `backend/app/services/student_service.py` user ke allowed scope
   ke students query karta hai.
6. Model: `backend/app/models/student.py` student table ko represent karta
   hai.
7. Schema: `backend/app/schemas/student_schema.py` safe API response fields
   define karta hai.
8. Result JSON browser me aata hai aur React state table update karti hai.

`Classes`, `Imports`, aur `Campaigns` ko isi tarah trace karo. Ye tumhara
project samjhane ka sabse achha practical tareeqa hai.

## 6. Chhota change safely kaise karein

Har change ke liye yeh short loop follow karo:

1. Ek sentence me expected behavior likho: “Search box student code se bhi
   match kare.”
2. `frontend/src/features/StudentsPage.jsx` me search filter kholo.
3. Zaroorat par API/route/schema/service/model check karo; sirf correct layer
   ko edit karo.
4. Agar API input/output badla, backend test ya UI error/loading state update
   karo. DB badli to nayi Alembic migration bhi banao.
5. `npm run lint`, `npm run build`, backend `pytest` chalao.
6. Browser me signed-in role se feature manually check karo.
7. `git diff` dekho: unrelated ya secret file change nahi honi chahiye.

### Misal: student form me phone number add karna

Pehle guardian/student phone ka business rule aur privacy approval confirm
karo. Phir model me column, Pydantic create/response schema, Alembic
migration, frontend form/input, aur tests update karo. Phone number personal
data hai: use CSV export, logs, screenshots aur public test data me bina
approval mat dalo. Sirf React input add karne se phone database me persist
nahi hota.

### Feature hataana

Sirf menu button chhupana feature removal nahi. Check karo: UI route,
frontend API call, backend endpoint/service, DB table/data, tests, migration,
docs aur deployment config. Purane production data wali table ko bina
retention/backup discussion destructive migration se delete mat karo.

## 7. Padhai ka ordered roadmap

### Phase A — Basics

1. Python variables, strings, numbers, list/dict, `if`, `for`.
2. Python functions, parameters/default values, return, exceptions.
3. Python modules, imports, virtual environment, `pip`, requirements file.
4. HTTP basics: request/response, JSON, GET/POST, status codes.
5. SQL: SELECT/INSERT/UPDATE, table, primary key, foreign key.

### Phase B — Is project ka backend

6. FastAPI route, `APIRouter`, path/query/form/file parameters.
7. Pydantic model aur input validation.
8. SQLAlchemy model/query/session/commit.
9. Service layer aur business rules; route/service boundary.
10. Authentication: password hash, bearer token, JWT expiry.
11. Authorization: role, permission, scope; har request ka DB check.
12. Alembic migration, `upgrade head`, backup/rollback.
13. Pytest: arrange/act/assert, fixture, mock, regression test.

### Phase C — Frontend

14. HTML forms, labels, buttons, tables, semantic page structure.
15. CSS box model, flexbox, grid, media queries, focus state.
16. JavaScript promises, `async/await`, `fetch`, try/catch, modules.
17. React component, props, `useState`, `useEffect`, event handler.
18. Loading/error/empty states, form validation, keyboard/accessibility.
19. Vite dev server, environment variables, npm scripts, production build.

### Phase D — Release

20. Git: status, diff, branch, commit, pull request.
21. Docker image/container/volume/network and Compose.
22. Environment variables, secrets, TLS/HTTPS, reverse proxy, firewall.
23. Health check, logs, automated CI, backup and restore.
24. Student/parent data minimization, consent, retention, access reviews.
25. ML basics only when there is approved labeled data: features, labels,
    train/test split, baseline, accuracy/recall, bias, uncertainty.

**Suggested approach:** roz 30–60 minute. Ek topic padhkar upar wale
request-flow ke matching project file ko kholo. Pehle read-only change,
phir ek chhota safe UI change karo. Auth, scopes, DB migrations aur real
calling ko supervisor ke bina experiment mat karo.

## 8. Common errors aur unka pehla check

| Problem | Pehle kya check karein |
|---|---|
| Browser “Cannot reach the server” dikhaye | Backend chal raha hai? local Vite proxy `/api` port 8000 par bhej raha hai? |
| Sign-in `401` | Admin bootstrap hua? Username/password? Account active? |
| `403` permission error | User ka role/permission/scope? UI me hidden control se access nahi milta. |
| Database connection error | PostgreSQL running? `DATABASE_URL` host, port, DB name aur password? |
| `relation does not exist` | Sahi database par `alembic upgrade head` chala? |
| `422` | API `/docs` me expected field names/types check karo. |
| File `413` | File 10 MB se chhoti hai? Allowed format? |
| `npm ci` error | Node.js 22? `frontend/package-lock.json` maujood? |
| Docker healthy nahi | `docker compose ... ps` aur `logs -f backend db` dekho. `/ready` DB tak pahunchna chahiye. |
| Frontend build sahi par live data nahi | API URL, token expiry, backend permission aur browser Network tab check karo. |

Logs share karne se pehle personal data, access tokens, phone numbers aur
database URL/password hatao.

## 9. Jo abhi nahi bana hai

- **Real phone calls:** disabled/disconnected. Provider credentials se pehle
  consent, guardian verification, opt-out, calling hours, privacy review,
  live callback testing aur institution approval chahiye.
- **ML predictions:** `ml/` me kuch settings/schema/features hain; running
  model API, trained model, accepted metrics ya validated training data nahi.
- **Full production operations:** domain/TLS reverse proxy, managed secrets,
  backups/restore test, monitoring/alerts, school-specific privacy approval
  aur public deployment sign-off operator ko set karne honge.
- **Frontend me sab backend workflows:** UI se basic sign-in, classes,
  students, attendance import, dashboard aur campaign creation covered hain.
  Follow-ups, reports, user admin aur all API actions ke liye backend API
  explorer use karo; future UI screens `features/` me add ki ja sakti hain.

## 10. Kisi ko project kaise samjhaun

Is 60-second explanation ko apne words me bolo:

> “Yeh college attendance manage karne ka React aur FastAPI web app hai.
> React browser me forms aur tables dikhata hai. FastAPI API request ko
> validate karti hai, signed-in user ke permissions aur data scope check
> karti hai, aur SQLAlchemy se PostgreSQL me data save/read karti hai.
> Alembic database schema changes ko versions me rakhta hai. Abhi app
> classes, students, attendance import aur campaign eligibility me help
> karta hai. Campaign banana call karna nahi hai. ML aur live voice-calling
> production features tabhi honge jab unhe alag se validate, integrate,
> approve aur test kiya jaaye.”

Padhate waqt pehle browser flow dikhana, phir usi flow ki React file, phir
API route/schema/service/model tak trace karna. Isse concept aur code ka link
clear hota hai.
