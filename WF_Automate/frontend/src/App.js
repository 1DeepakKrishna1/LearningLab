import React, { useEffect, useState } from 'react';
import axios from 'axios';
import WorkflowCanvas from './components/WorkflowCanvas';
import AIAssistant from './components/AIAssistant';

function App() {
  const [agents, setAgents] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [currentWorkflowId, setCurrentWorkflowId] = useState(null);
  const [workflowName, setWorkflowName] = useState('');
  const [elements, setElements] = useState([]);
  const [selectedElement, setSelectedElement] = useState(null);
  const [runResult, setRunResult] = useState(null);

  useEffect(() => {
    axios.get('http://localhost:8000/agents/').then(res => setAgents(res.data));
    refreshWorkflowList();
  }, []);

  function refreshWorkflowList() {
    axios.get('http://localhost:8000/workflows/').then(res => setWorkflows(res.data));
  }

  function loadWorkflow(id) {
    if (!id) {
      setCurrentWorkflowId(null);
      setElements([]);
      return;
    }
    axios.get(`http://localhost:8000/workflows/${id}`).then(res => {
      const wf = res.data;
      setCurrentWorkflowId(wf.id);
      setWorkflowName(wf.name || '');
      // convert workflow data to elements (simple mapping)
      const nodes = (wf.steps || []).map((step, idx) => ({
        id: `${step.agent}-${idx}`,
        type: 'custom',
        position: step.position || { x: 50 * idx, y: 50 * idx },
        data: { label: step.name || `Step ${idx}` }
      }));
      const edges = (wf.edges || []).map((edge, idx) => ({
        id: `e${idx}-${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep'
      }));
      setElements(nodes.concat(edges));
    });
  }

  function saveWorkflow() {
    const wf = {
      name: workflowName || (currentWorkflowId ? `Workflow ${currentWorkflowId}` : `New Workflow`),
      agents: [],
      steps: elements
        .filter(el => !el.source)
        .map((el) => ({
          id: el.id,
          name: el.data.label,
          position: el.position
        })),
      edges: elements
        .filter(el => el.source)
        .map((el) => ({ source: el.source, target: el.target }))
    };
    if (currentWorkflowId) {
      axios.put(`http://localhost:8000/workflows/${currentWorkflowId}`, wf).then(() => refreshWorkflowList());
    } else {
      axios.post('http://localhost:8000/workflows/', wf).then((res) => {
        setCurrentWorkflowId(res.data.id);
        refreshWorkflowList();
      });
    }
  }

  function cloneWorkflow() {
    if (!currentWorkflowId) return;
    axios.post(`http://localhost:8000/workflows/${currentWorkflowId}/clone`).then(res => {
      refreshWorkflowList();
      setCurrentWorkflowId(res.data.id);
      loadWorkflow(res.data.id);
    });
  }

  function runWorkflow() {
    if (!currentWorkflowId) return;
    axios.post(`http://localhost:8000/workflows/${currentWorkflowId}/run`).then(res => {
      const data = res.data;
      // initialize result state and clear any highlights
      setRunResult({status: data.status, steps: []});
      setElements(elts => elts.map(e => ({...e, style: {...(e.style||{}), background: 'white'}})));
      if (data.steps && data.steps.length) {
        data.steps.forEach((s, i) => {
          setTimeout(() => {
            // append this step to runResult
            setRunResult(prev => ({...prev, steps: prev.steps.concat(s)}));
            // highlight associated node
            const nodeId = `${s.agent}-${s.step}`;
            setElements(elts => elts.map(el => {
              if (el.id === nodeId) {
                return {...el, style: {...(el.style||{}), background: '#aef'}};
              }
              return el;
            }));
          }, i * 1000);
        });
      }
    });
  }

  return (
    <div className="App" style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '250px', borderRight: '1px solid #ccc', padding: 10 }}>
        <h3>Agent Library</h3>
        {agents.map(a => (
          <div
            key={a.id}
            draggable
            onDragStart={(event) => {
              event.dataTransfer.setData(
                'application/reactflow',
                JSON.stringify(a)
              );
              event.dataTransfer.effectAllowed = 'move';
            }}
            style={{ padding: '4px', border: '1px solid #ddd', marginBottom: '4px', cursor: 'grab' }}
          >
            {a.name}
          </div>
        ))}
        <hr />
        <h4>Workflows</h4>
        <div>
          <input
            type="text"
            placeholder="workflow name"
            value={workflowName}
            onChange={e => setWorkflowName(e.target.value)}
            style={{ width: '100%', marginBottom: '4px' }}
          />
        </div>
        <select
          value={currentWorkflowId || ''}
          onChange={(e) => loadWorkflow(parseInt(e.target.value))}
          style={{ width: '100%' }}
        >
          <option value="">-- select --</option>
          {workflows.map(wf => (
            <option key={wf.id} value={wf.id}>{wf.name || `Workflow ${wf.id}`}</option>
          ))}
        </select>
        <button onClick={() => { setCurrentWorkflowId(null); setElements([]); setSelectedElement(null); setWorkflowName(''); }} style={{ marginTop: '8px' }}>New</button>
        <button onClick={saveWorkflow} style={{ marginTop: '8px' }}>Save</button>
        <button onClick={cloneWorkflow} style={{ marginTop: '8px' }}>Clone</button>
        <button onClick={runWorkflow} style={{ marginTop: '8px' }}>Run</button>
      </div>
      <div style={{ flex: 1, position: 'relative' }}>
        <WorkflowCanvas
          elements={elements}
          setElements={setElements}
          onElementSelected={setSelectedElement}
        />
        {runResult && (
          <div style={{position:'absolute', top:0, left:'50%', background:'#ffffee', padding: '8px', border:'1px solid #ccc', transform:'translateX(-50%)', maxWidth:'400px'}}>
            <strong>Run Result:</strong> {runResult.status}
            {runResult.steps && runResult.steps.length > 0 && (
              <ul style={{margin:'4px 0', paddingLeft:'16px'}}>
                {runResult.steps.map((s,i) => (
                  <li key={i}>{s.message}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {selectedElement && (
          <div
            style={{
              position: 'absolute',
              right: 0,
              top: 0,
              width: '200px',
              background: '#f9f9f9',
              borderLeft: '1px solid #ccc',
              padding: '10px'
            }}
          >
            <h4>Properties</h4>
            <div>ID: {selectedElement.id}</div>
            <div>
              Label: <input
                value={selectedElement.data.label}
                onChange={e => {
                  const newLabel = e.target.value;
                  setElements(els => els.map(el => el.id === selectedElement.id ? {...el, data:{...el.data,label:newLabel}} : el));
                  setSelectedElement(el => ({...el, data:{...el.data,label:newLabel}}));
                }}
              />
            </div>
          </div>
        )}
        {/* AI assistant component */}
        <div style={{position:'absolute', bottom:0, right:0, width:'250px', height:'200px', background:'#fff', border:'1px solid #ccc', padding:'8px'}}>
          <AIAssistant />
        </div>
      </div>
    </div>
  );
}

export default App;
