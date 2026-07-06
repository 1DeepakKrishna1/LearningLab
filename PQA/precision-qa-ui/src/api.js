import axios from 'axios';

// Read base URL from environment variable REACT_APP_API_BASE, else default to localhost
const BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:8000';

export async function generateQuestions(payload) {
  try {
    const r = await axios.post(`${BASE}/generate-questions`, payload);
    return r.data.questions || [];
  } catch (e) {
    console.error('generate-questions error', e);
    return [];
  }
}

export async function evaluateAnswers(payloadOrStatement, qa) {
  // Accept either:
  // - evaluateAnswers({ statement, qa: [...] })
  // - evaluateAnswers(statementString, qaArray)
  let payload;
  if (typeof payloadOrStatement === 'string') {
    payload = { statement: payloadOrStatement, qa: Array.isArray(qa) ? qa : [] };
  } else {
    payload = payloadOrStatement || {};
  }

  try {
    // console.log('Evaluating answers with payload:', payload);
    const r = await axios.post(`${BASE}/evaluate-answers`, payload);
    return r.data.evaluations || [];
  } catch (e) {
    console.error('evaluate-answers error', e);
    return { error: String(e) };
  }
}

export async function finalEvaluation(payload) {
  try {
    console.log('Final evaluation with payload:', payload);
    const r = await axios.post(`${BASE}/final-evaluation`, payload);
    console.log('Final evaluation response:', r.data);  
    return r.data || {};
  } catch (e) {
    console.error('final-evaluation error', e);
    return { error: String(e) };
  }
}

export async function createPlan(payload) {
  try {
    console.log('Create plan with payload:', payload);
    const r = await axios.post(`${BASE}/create-plan`, payload);
    return r.data || {};
  } catch (e) {
    console.error('create-plan error', e);
    return { error: String(e) };
  }
}

export async function getPromptResponse(prompt) {
  try {
    console.log('Getting prompt response for:', prompt);
    const r = await axios.post(`${BASE}/GetPromptResponse`, { prompt });
    return r.data.response || '';
  } catch (e) {
    console.error('GetPromptResponse error', e);
    return 'Error: Unable to get response from AI assistant.';
  }
}
