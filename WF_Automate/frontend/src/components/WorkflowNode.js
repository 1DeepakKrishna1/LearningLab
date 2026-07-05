import React from 'react';
import { Handle, Position } from 'reactflow';

export function WorkflowNode({ data }) {
  return (
    <div style={{
      padding: '10px 15px',
      borderRadius: '8px',
      border: '2px solid #222',
      background: '#fff',
      color: '#222',
      fontSize: '12px',
      textAlign: 'center',
      minWidth: '100px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    }}>
      <Handle 
        type="target" 
        position={Position.Top}
        isConnectable={true}
        style={{ background: '#00ff00', width: '14px', height: '14px', borderRadius: '50%' }}
      />
      {/* additional side handles make it easier to connect */}
      <Handle type="target" position={Position.Left} isConnectable={true} style={{ background: '#00ff00', width: '14px', height: '14px', borderRadius: '50%' }} />
      <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{data.label}</div>
      <div style={{ fontSize: '10px', color: '#666' }}>Agent/Tool</div>
      <Handle 
        type="source" 
        position={Position.Bottom}
        isConnectable={true}
        style={{ background: '#ff0000', width: '14px', height: '14px', borderRadius: '50%' }}
      />
      <Handle type="source" position={Position.Right} isConnectable={true} style={{ background: '#ff0000', width: '14px', height: '14px', borderRadius: '50%' }} />
    </div>
  );
}

export const nodeTypes = {
  custom: WorkflowNode,
};
