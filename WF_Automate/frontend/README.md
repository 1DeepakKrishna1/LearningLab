# Frontend - Workflow Management UI

This is a React application using `reactflow` for visual workflow orchestration.

## Setup

```bash
cd frontend
npm install
npm start
```

The app expects the backend to be running at `http://localhost:8000` and will fetch agents and workflows.

## Core Features

### Building Workflows

1. **Drag agents onto the canvas**: Drag an agent from the left "Agent Library" panel and drop it onto the canvas to create a node.

2. **Connect agents with edges**: 
   - Each node has several connection points:
     - **Green dots**: Inputs (top and left sides) — where edges come *into* this agent
     - **Red dots**: Outputs (bottom and right sides) — where edges go *out* to downstream agents
   - To connect: **start the drag from any red dot on the source node, and release on a green dot of the target node**. The green/ red circles expand when hovered so you know you can attach there.
   - If you're having trouble, try using the left/right handles; they give you more area to drop onto.
   - Successfully dropping on a handle creates a workflow edge showing execution flow

3. **Edit node labels**: Click any node on the canvas to select it; a panel appears on the right where you can edit the label.

4. **Delete nodes/edges**: Select a node or edge and press the **Delete** key.

### Managing Workflows

- **Workflow library**: Use the dropdown on the left to select and load previously saved workflows.
- **New** button: Start building a fresh workflow.
- **Save** button: Create or update workflows; all nodes and edges are persisted to the backend.
- **Clone** button: Duplicate the current workflow (backend endpoint creates a copy).
- **Run** button: Simulate execution; results appear as step-by-step animations on the canvas with node highlighting.

### AI Assistant

- **Chat window** (bottom right): Connects to backend `/ai/chat` endpoint.
- To enable real AI responses, start the backend with `OPENAI_API_KEY` or `GROQ_API_KEY` environment variable set.

---

**Tip**: When you run a workflow, nodes execute in order following the edges you've drawn. The UI highlights each node as it completes.

