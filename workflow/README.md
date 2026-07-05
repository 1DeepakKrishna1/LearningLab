# Workflow Management Platform

An enterprise-grade workflow orchestration platform with role-based access control, management portal, visual workflow studio, and AI assistant.

The organization name and logo are configurable — see [Organization Branding](#organization-branding).

## Stack

| Layer    | Tech                                                        |
|----------|-------------------------------------------------------------|
| Frontend | React 18, Vite, ReactFlow v11, Zustand v4, Tailwind CSS v3  |
| Backend  | Python 3.11+, FastAPI, Pydantic v2, Uvicorn                 |
| AI       | Groq API (Llama 3.3-70B)                                    |

---

## Quick Start

### 1 – Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment (.env already has defaults)
# Ensure GROQ_API_KEY is set for the AI assistant

# Start API server
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2 – Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

---

## Organization Branding

The org name, login email domain, and logo are configured in `backend/.env`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `ORG_NAME`   | Display name shown across the UI/API | `Incepta` |
| `ORG_DOMAIN` | Login email domain | derived from `ORG_NAME` (e.g. `incepta.com`) |
| `ORG_LOGO`   | Path to a logo image (png/jpg/svg/gif/webp); relative paths resolve from `backend/`. If unset or invalid, **no logo is shown**. | `../frontend/public/incepta_logo.png` |

Changing `ORG_NAME` (or `ORG_DOMAIN`) updates the login email domain for all default
accounts — e.g. `admin@incepta.com` becomes `admin@<org-domain>`.

## Default Login Credentials

Emails use the configured org domain (defaults to `incepta.com`).

| Role | Email | Password |
|------|-------|----------|
| **Product Admin** | admin@\<org-domain> | Admin@123 |
| **Org Admin** | orgadmin@\<org-domain> | Admin@123 |
| **Org User** | alice@\<org-domain> | User@123 |
| **Org User** | bob@\<org-domain> | User@123 |
| **Org User** | carol@\<org-domain> | User@123 |
| **Customer Admin** | custadmin@\<org-domain> | Admin@123 |
| **Customer User** | custuser@\<org-domain> | User@123 |

---

## Application Flow

```
Login Screen
    ↓
Landing Portal  ──────────────────────────────────────
    │                                                 │
    ├── Insights                                      │
    │   ├── Dashboard (default)                       │
    │   ├── Reports                                   │
    │   └── Audit Logs                                │
    │                                                 │
    ├── Process                                       │
    │   └── My Workflows → [Open in Studio] ──────►  │
    │                                                 │
    └── Manage (Admin only)                   Workflow Studio
        ├── Library: Tools, Agents, Templates         │
        ├── Reviews: Approve / Reject queue    ◄──────┘
        ├── Data Models                        (Back to Portal)
        └── Identity: Users, Groups, Projects
```

---

## Features

### Portal

| Feature | Description |
|---------|-------------|
| **Role-Based Login** | Product Admin, Org Admin, Org User with scoped access |
| **Insights Dashboard** | KPI metrics: workflows, executions, SLA, token consumption, 7-day trends |
| **Reports** | Workflow usage, agent performance, user activity, token consumption — CSV export |
| **Audit Logs** | Full activity trail with search, filtering by action/resource type, pagination |
| **Process** | Browse assigned workflows; launch directly into the Studio |
| **Tools Manager** | CRUD for tool library; new tools require review before publishing |
| **Agents Manager** | CRUD for agent library; new agents go through review queue |
| **Templates Manager** | Browse, clone, and manage workflow templates |
| **Review Queue** | Admin approval workflow — Approve or Reject pending library items |
| **Data Models** | Manage data model library; full editing available in Studio |
| **Users** | Create/edit/deactivate users; assign to projects |
| **Groups** | Manage user groups; add/remove members |
| **Projects** | Associate workflows and users to projects; Org Users see assigned projects only |

### Studio (Visual Workflow Editor)

| Feature | Description |
|---------|-------------|
| **Drag & Drop Canvas** | Drag agents from the left panel onto the ReactFlow canvas |
| **Agent Configuration** | Click any agent to configure properties in the right panel |
| **Tool Assignment** | Toggle tools on/off per agent |
| **Workflow Persistence** | Save/load workflows; persisted to `myworkflow.json` |
| **Library Templates** | Pre-built template workflows; clone to customize |
| **Execution Simulation** | Step-by-step animated execution with per-node status |
| **Human-in-the-Loop** | Pauses execution for human judgment / input |
| **AI Assistant** | Floating chat powered by Groq (Llama 3.3-70B), context-aware |
| **Data Model Designer** | Visual entity-relationship designer with binding to workflow nodes |
| **Theme Switcher** | 6 color themes: slate, carbon, ocean, aurora, midnight, light |

---

## Agent Types

| Type | Color | Description |
|------|-------|-------------|
| `automatic` | Indigo | Fully automated processing |
| `role_based` | Emerald | Routed to specific team roles |
| `human_in_the_loop` | Amber | Pauses for human approval |
| `conditional` | Orange | Branches based on data conditions |
| `parallel` | Purple | Runs sub-tasks concurrently |
| `prompt_agent` | Indigo | LLM prompt-driven agent |
| `react_agent` | Indigo | ReAct pattern with tool use |
| `guardrails` | Red | PII / toxicity / compliance checks |
| `orchestrator` | Indigo | Multi-agent coordination |
| `supervisor` | Indigo | Supervisory control flow |

---

## Project Structure

```
workflow/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, startup
│   ├── models.py                  # Pydantic v2 models (all entities)
│   ├── db.py                      # In-memory stores
│   ├── dummy_data.py              # Seed: tools, agents, templates, IAM defaults
│   ├── dummy_data.json            # Library seed data (tools, agents, templates)
│   ├── myworkflow.json            # User-created workflows (persisted)
│   ├── data_models.json           # Data model definitions (persisted)
│   ├── users.json                 # Users (persisted after first run)
│   ├── groups.json                # Groups (persisted)
│   ├── projects.json              # Projects (persisted)
│   ├── reviews.json               # Review queue (persisted)
│   ├── persistence.py             # Workflow persistence
│   ├── data_models_persistence.py # Data model persistence
│   ├── portal_persistence.py      # IAM + review persistence
│   ├── library_persistence.py     # Library (tools/agents/templates) persistence
│   └── routes/
│       ├── auth.py                # Login, logout, /me
│       ├── users.py               # User CRUD
│       ├── groups.py              # Group CRUD
│       ├── projects.py            # Project CRUD
│       ├── metrics.py             # Dashboard + reports
│       ├── audit.py               # Audit log queries
│       ├── reviews.py             # Review / publish workflow
│       ├── workflows.py           # Workflow CRUD
│       ├── agents.py              # Agent CRUD
│       ├── tools.py               # Tool CRUD
│       ├── library.py             # Template listing + clone
│       ├── execution.py           # Execution simulation
│       ├── ai_assistant.py        # Groq chat
│       ├── data_models.py         # Data model CRUD
│       └── associations.py        # Workflow ↔ data model bindings
│
└── frontend/
    ├── public/
    │   └── incepta_logo.png
    ├── index.html
    └── src/
        ├── App.jsx                        # Top-level router (login/landing/studio)
        ├── main.jsx
        ├── api/api.js                     # Axios client (all endpoints)
        ├── store/
        │   ├── workflowStore.js           # Studio state (Zustand)
        │   ├── authStore.js               # Auth state
        │   └── portalStore.js             # Portal navigation state
        ├── pages/
        │   ├── LoginPage.jsx
        │   ├── LandingPage.jsx
        │   ├── insights/
        │   │   ├── Dashboard.jsx
        │   │   ├── Reports.jsx
        │   │   └── AuditLogs.jsx
        │   ├── process/
        │   │   └── ProcessList.jsx
        │   └── manage/
        │       ├── ToolsManager.jsx
        │       ├── AgentsManager.jsx
        │       ├── TemplatesManager.jsx
        │       ├── DataModelsManager.jsx
        │       ├── UsersManager.jsx
        │       ├── GroupsManager.jsx
        │       ├── ProjectsManager.jsx
        │       └── ReviewsManager.jsx
        └── components/
            ├── portal/
            │   ├── TopBar.jsx
            │   ├── Sidebar.jsx
            │   └── Notification.jsx
            ├── Toolbar.jsx
            ├── WorkflowCanvas.jsx
            ├── LibraryPanel.jsx
            ├── PropertiesPanel.jsx
            ├── AIAssistant.jsx
            ├── ExecutionPanel.jsx
            ├── HumanInputModal.jsx
            ├── SaveWorkflowModal.jsx
            ├── DataModelDesigner.jsx
            ├── ThemeSwitcher.jsx
            └── nodes/
                ├── AgentNode.jsx
                └── ToolNode.jsx
```

---

## API Reference

### Auth
```
POST   /auth/login              Login → {token, user}
POST   /auth/logout             Invalidate session token
GET    /auth/me                 Current user profile
```

### Users / Groups / Projects
```
GET    /users                   List users (admin)
POST   /users                   Create user (admin)
PUT    /users/{id}              Update user (admin)
DELETE /users/{id}              Delete user (admin)
PATCH  /users/{id}/status       Toggle active/inactive

GET    /groups                  List groups
POST   /groups                  Create group
POST   /groups/{id}/members/{uid}   Add member
DELETE /groups/{id}/members/{uid}   Remove member

GET    /projects                List projects
POST   /projects                Create project
POST   /projects/{id}/workflows/{wid}   Link workflow
POST   /projects/{id}/users/{uid}       Link user
```

### Metrics & Governance
```
GET    /metrics/dashboard       KPI metrics (executions, SLA, tokens)
GET    /metrics/reports         Report data (workflow_usage|agent_performance|user_activity|token_consumption)

GET    /audit-logs              Activity log (filterable)
GET    /audit-logs/summary      Action + resource type counts

GET    /reviews                 Review queue
POST   /reviews                 Submit item for review
PUT    /reviews/{id}/approve    Approve item
PUT    /reviews/{id}/reject     Reject item
```

### Studio
```
GET    /workflows               List user workflows
POST   /workflows               Create workflow
PUT    /workflows/{id}          Update workflow
DELETE /workflows/{id}          Delete workflow

GET    /library/workflows       Template workflows
POST   /library/workflows/{id}/clone   Clone template

GET    /agents                  List agents
POST   /agents                  Create agent
PUT    /agents/{id}             Update agent
DELETE /agents/{id}             Delete agent

GET    /tools                   List tools
POST   /tools                   Create tool
PUT    /tools/{id}              Update tool
DELETE /tools/{id}              Delete tool

POST   /execution/{id}/run      Simulate execution
POST   /ai/chat                 AI assistant chat

GET    /data-models             List data models
POST   /data-models             Create data model
PUT    /data-models/{id}        Update data model
DELETE /data-models/{id}        Delete data model
```

---

## Environment Variables (`backend/.env`)

```env
GROQ_API_KEY=gsk_...          # Required for AI assistant
ISMOCK=True                    # Load seed data on startup
MOCKDATA=dummy_data.json       # Seed data filename
MYWORKFLOW=myworkflow.json     # User workflow persistence file
```
