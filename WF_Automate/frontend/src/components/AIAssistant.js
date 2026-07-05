import React, { useState } from 'react';

function AIAssistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  function sendMessage() {
    if (!input) return;
    const msg = input;
    setMessages(msgs => msgs.concat({ role: 'user', text: msg }));
    setInput('');
    // send to backend AI endpoint
    fetch('http://localhost:8000/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    })
      .then(r => r.json())
      .then(data => {
        setMessages(msgs => msgs.concat({ role: 'assistant', text: data.response }));
      })
      .catch(err => {
        setMessages(msgs => msgs.concat({ role: 'assistant', text: `(error: ${err})` }));
      });
  }

  return (
    <div style={{display:'flex', flexDirection:'column', height:'100%'}}>
      <div style={{flex:1, overflowY:'auto', fontSize:'12px'}}>
        {messages.map((m,i) => (
          <div key={i} style={{margin: '2px 0'}}><strong>{m.role}:</strong> {m.text}</div>
        ))}
      </div>
      <div style={{display:'flex'}}>
        <input
          style={{flex:1}} 
          value={input}
          onChange={e=>setInput(e.target.value)}
          onKeyDown={e=>e.key==='Enter' && sendMessage()}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default AIAssistant;
