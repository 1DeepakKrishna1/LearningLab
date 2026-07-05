# Workflow Automation System

This workspace contains a simple prototype of a workflow management system with a React frontend and a FastAPI backend.

## Architecture

- **backend/**: FastAPI application serving dummy data for workflows, agents, and tools.
- **frontend/**: React application using React Flow for visual workflow orchestration.

## Getting Started

### Backend

1. Open a terminal and navigate to `backend`.
2. Create a virtual environment:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install requirements:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the server:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
5. Test endpoints via browser or curl:
   - `GET http://localhost:8000/agents/`
   - `GET http://localhost:8000/workflows/`
   - `POST http://localhost:8000/workflows/1/run`

### Frontend

1. Open another terminal and go to `frontend`.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm start
   ```
4. The UI will load on `http://localhost:3000` and will fetch data from the backend.

## Features

- Left panel shows agents fetched from the backend.
- Agents can be dragged onto the React Flow canvas to create nodes.
- **Workflow library** with load/save/clone functionality via API.
- **Workflow persistence**: create, update, clone workflows using FastAPI endpoints.
- Node selection opens a properties pane for editing labels (configuration stub).
- Execution simulation endpoint with results displayed in the UI, including step‑by‑step animation and node highlighting.
- AI assistant pane backed by `/ai/chat`; can be wired to OpenAI with an API key.

## Next Steps

- Implement more detailed agent/tool configuration in the right‑hand flyout.
- Persist workflows in a real database.
- Add user authentication and role‑based steps (HumanInTheLoop, etc.).
- Integrate a real AI model by setting `OPENAI_API_KEY` and enhancing `/ai/chat`.
- Improve execution simulation with delays, error handling, and visual feedback.

This skeleton provides a starting point for further development of the workflow management system described in `req.txt`.
