import React, { useCallback } from 'react';
import ReactFlow, { addEdge, Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import { nodeTypes } from './WorkflowNode';

// elements and setElements must be passed from parent for persistence

function WorkflowCanvas({ elements, setElements, onElementSelected }) {
  // Separate nodes and edges from elements array
  const nodes = elements.filter(el => !el.source);
  const edges = elements.filter(el => el.source);

  const onConnect = useCallback(
    params => {
      console.log('onConnect', params);
      const edge = { ...params, id: `edge-${params.source}-${params.target}` };
      setElements(els => addEdge(edge, els));
    },
    [setElements]
  );

  const onNodesChange = useCallback(
    (changes) => {
      // Handle node changes (position, selection, etc)
      setElements(els => {
        return els.map(el => {
          const change = changes.find(c => c.id === el.id);
          if (!change) return el;
          if (change.type === 'remove') return null;
          if (change.type === 'position' && change.position) {
            return { ...el, position: change.position };
          }
          return el;
        }).filter(Boolean);
      });
    },
    [setElements]
  );

  const onEdgesChange = useCallback(
    (changes) => {
      // Handle edge changes
      setElements(els => {
        return els.map(el => {
          const change = changes.find(c => c.id === el.id);
          if (!change) return el;
          if (change.type === 'remove') return null;
          return el;
        }).filter(Boolean);
      });
    },
    [setElements]
  );

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const data = event.dataTransfer.getData('application/reactflow');
      if (!data) return;
      const nodeData = JSON.parse(data);
      const reactFlowBounds = event.target.getBoundingClientRect();
      const position = {
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      };
      const newNode = {
        id: `${nodeData.id}-${+new Date()}`,
        type: 'custom',
        position,
        data: { label: nodeData.name }
      };
      setElements((es) => es.concat(newNode));
    },
    [setElements]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  return (
    <div style={{ width: '100%', height: '100%' }} onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesConnectable={true}
        nodesDraggable={true}
        connectionLineStyle={{ stroke: '#888', strokeWidth: 2 }}
        connectionLineType="smoothstep"
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(e, node) => onElementSelected && onElementSelected(node)}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default WorkflowCanvas;
