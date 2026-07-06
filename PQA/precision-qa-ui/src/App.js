import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, Link, useNavigate } from 'react-router-dom';
import { generateQuestions, evaluateAnswers, finalEvaluation, createPlan, getPromptResponse } from './api';
import axios from 'axios';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

// Backend URL from environment variable
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8100';

// Minimal Markdown -> HTML converter used for Create Plan rendering.
// Supports ATX headers (#, ##, ###), setext headers already normalized by caller,
// horizontal rules (--- or ***), unordered lists (- or *), ordered lists (1.),
// blockquotes (>), fenced code blocks (```lang), inline code (`code`), bold (**text**), and italic (*text*).
function mdToHtml(mdText) {
  let html = mdText;

  // Escape HTML
  html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // Handle code blocks ```lang ... ```
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || ""}">${code}</code></pre>`;
  });

  // Inline code `code`
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold **text**
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic *text*
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Horizontal rule ---
  html = html.replace(/^\s*---\s*$/gm, "<hr>");

  // Headings ###, ##, #
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Split into lines
  const lines = html.split("\n");
  let result = [];
  let listStack = [];

  function closeLists(level) {
    while (listStack.length > 0 && listStack.length >= level) {
      const type = listStack.pop();
      result.push(`</${type}>`);
    }
  }

  lines.forEach(line => {
    let trimmed = line.trim();

    if (trimmed === "") {
      result.push("");
      return;
    }

    // Ordered list
    let olMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (olMatch) {
      const [, , content] = olMatch;
      if (listStack[listStack.length - 1] !== "ol") {
        closeLists(1);
        listStack.push("ol");
        result.push("<ol>");
      }
      result.push(`<li>${content}</li>`);
      return;
    }

    // Unordered list
    let ulMatch = trimmed.match(/^- (.+)/);
    if (ulMatch) {
      const [, content] = ulMatch;
      if (listStack[listStack.length - 1] !== "ul") {
        closeLists(1);
        listStack.push("ul");
        result.push("<ul>");
      }
      result.push(`<li>${content}</li>`);
      return;
    }

    // If we reach here, close all open lists
    closeLists(0);

    // Already HTML tags from headings, hr, pre, etc.
    if (/^<(h\d|pre|hr|code|strong|em)>/.test(trimmed)) {
      result.push(trimmed);
    } else {
      // Strip any leftover ATX header markers like '#', '##', '###' at the start of a line
      const cleaned = trimmed.replace(/^#{1,6}\s+/, '');
      result.push(`<p>${cleaned}</p>`);
    }
  });

  // Close any remaining open lists
  closeLists(0);

  const bodyHtml = result.join("\n");

  // Scoped CSS for markdown output (applies only inside .md-rendered)
  const scopedCss = `
  .md-rendered { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; padding: 20px; background-color: #f9f9f9; }
  .md-rendered h1 { font-size: 1.6em; margin-bottom: 0.5em; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }
  .md-rendered h2 { font-size: 1.4em; margin-top: 1.5em; margin-bottom: 0.5em; color: #34495e; border-bottom: 1px solid #bdc3c7; padding-bottom: 0.2em; }
  .md-rendered h3 { font-size: 1.2em; margin-top: 1.2em; margin-bottom: 0.4em; color: #555; }
  .md-rendered p { margin: 0.8em 0; }
  .md-rendered ul, .md-rendered ol { margin: 0.8em 0 0.8em 2em; }
  .md-rendered li { margin: 0.4em 0; }
  .md-rendered hr { border: 0; border-top: 2px solid #ddd; margin: 2em 0; }
  .md-rendered strong { font-weight: 600; color: #2c3e50; }
  .md-rendered em { font-style: italic; color: #7f8c8d; }
  .md-rendered pre { background-color: #2d2d2d; color: #f8f8f2; padding: 1em; border-radius: 6px; overflow-x: auto; margin: 1em 0; }
  .md-rendered code { background-color: #e8e8e8; color: #c7254e; padding: 0.2em 0.4em; border-radius: 4px; font-family: 'Courier New', Courier, monospace; font-size: 0.95em; }
  .md-rendered a { color: #3498db; text-decoration: none; }
  .md-rendered a:hover { text-decoration: underline; }
  .md-rendered ul ul, .md-rendered ol ul { margin-left: 1.5em; }
  .md-rendered ol ol, .md-rendered ul ol { margin-left: 1.5em; }
  `;

  // Return scoped HTML: container div with inline style block + generated body
  return `<div class="md-rendered"><style>${scopedCss}</style>${bodyHtml}</div>`;
}

const CATEGORIES = [
  'Go/NoGo',
  'Clarification',
  'Assumption',
  'Critical',
  'Cause',
  'Effect',
  'Action',
];

function HomePage({ onGenerate, initialPayload }) {
  const [statement, setStatement] = useState('');
  const [selected, setSelected] = useState([]);
  const [count, setCount] = useState(3);
  const [preset, setPreset] = useState('');
  const [preStatement, setPreStatement] = useState('');
  const [showContextFlyout, setShowContextFlyout] = useState(false);
  const [showContextPreview, setShowContextPreview] = useState(false);
  const [context, setContext] = useState({
    starting_point: '',
    intent: '',
    supporting_data: '',
    constraints: '',
    persona: ''
  });
  const [isExpanded, setIsExpanded] = useState(true);

  // Function to get icon for each category
  function getCategoryIcon(category) {
    switch (category) {
      case 'Go/NoGo':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'Clarification':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'Assumption':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        );
      case 'Critical':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'Cause':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        );
      case 'Effect':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
          </svg>
        );
      case 'Action':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 9l3 3m0 0l-3 3m3-3H8m13 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
        );
    }
  }

  const PRESET_MAP = {
    'complex': ['Cause', 'Effect', 'Action'],
    'deep': ['Clarification', 'Assumption', 'Critical'],
    'decision': ['Go/NoGo', 'Critical', 'Action'],
  };

  const PRESTATEMENT_MAP = {
    'complex': 'Solve complex problem for the statement: {statement}',
    'deep': 'Conduct deep analysis for the statement: {statement}',
    'decision': 'Make wise decisions for the statement: {statement}',
  };

  useEffect(() => {
    if (initialPayload) {
      setStatement(initialPayload.statement || '');
      setSelected(initialPayload.categories || []);
      setCount(initialPayload.n || initialPayload.count || 3);
      setPreStatement(initialPayload.preStatement || '')
    }
  }, [initialPayload]);

  function toggleCategory(cat) {
    setSelected(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]);
  }

  function applyPreset(key) {
    setPreset(key);
    setPreStatement(PRESTATEMENT_MAP[key] || '');
    const cats = PRESET_MAP[key] || [];
    setSelected(cats);
  }

  async function handleGenerate(e) {
    e.preventDefault();
    var applied = preStatement.replace('{statement}', statement);
    
    var contextString = " " + formatContextStringFiltered();
    console.log('Context string:', contextString);
    if (contextString.length > 5) {
      applied = "Set the context with below Json: " +  contextString + "\n" + applied;
    }

    const payload = { statement: applied, preStatement: preStatement, preStatementApplied: applied, categories: effectiveSelected, n: Number(effectiveCount) };
    const questions = await generateQuestions(payload);
    onGenerate(questions, payload);
  }

  // In minimized mode, use default values for categories and count
  const effectiveSelected = isExpanded ? selected : (selected.length > 0 ? selected : ['General']);
  const effectiveCount = isExpanded ? count : (count > 0 ? count : 3);

  const isGenerateEnabled = (statement || '').toString().trim().length > 0 && preset !== '' && Array.isArray(effectiveSelected) && effectiveSelected.length > 0 && Number(effectiveCount) > 0;

  // Context management functions
  const updateContext = (field, value) => {
    setContext(prev => ({ ...prev, [field]: value }));
  };

  const clearContext = async () => {
    try {
      // Store empty context to backend
      const emptyContext = {
        starting_point: '',
        intent: '',
        supporting_data: '',
        constraints: '',
        persona: ''
      };

      await axios.post(`${BACKEND_URL}/store-context`, emptyContext);

      setContext(emptyContext);
      setShowContextPreview(false);
    } catch (error) {
      console.error('Error clearing context:', error);
      // Still proceed with UI updates even if backend fails
      setContext({
        starting_point: '',
        intent: '',
        supporting_data: '',
        constraints: '',
        persona: ''
      });
      setShowContextPreview(false);
    }
  };

  const hasContextContent = () => {
    return (context.starting_point && context.starting_point.trim()) ||
           (context.intent && context.intent.trim()) ||
           (context.supporting_data && context.supporting_data.trim()) ||
           (context.constraints && context.constraints.trim()) ||
           (context.persona && context.persona.trim());
  };

  const loadContextFromBackend = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/load-context`);
      if (response.data) {
        setContext({
          starting_point: response.data.starting_point || '',
          intent: response.data.intent || '',
          supporting_data: response.data.supporting_data || '',
          constraints: response.data.constraints || '',
          persona: response.data.persona || ''
        });

        // Set preview state based on whether loaded context has content
        const hasContent = (response.data.starting_point && response.data.starting_point.trim()) ||
                          (response.data.intent && response.data.intent.trim()) ||
                          (response.data.supporting_data && response.data.supporting_data.trim()) ||
                          (response.data.constraints && response.data.constraints.trim()) ||
                          (response.data.persona && response.data.persona.trim());
        setShowContextPreview(hasContent);
      }
    } catch (error) {
      console.error('Error loading context:', error);
      // If loading fails, keep current context state
    }
  };

  // Load context on component mount
  useEffect(() => {
    loadContextFromBackend();
  }, []);

  const formatContextString = () => {
    return JSON.stringify(context, null, 2);
  };

  const formatContextStringFiltered = () => {
    // Create a filtered context object with only non-empty values
    const filteredContext = {};

    if (context.starting_point && context.starting_point.trim()) {
      filteredContext.starting_point = context.starting_point;
    }
    if (context.intent && context.intent.trim()) {
      filteredContext.intent = context.intent;
    }
    if (context.supporting_data && context.supporting_data.trim()) {
      filteredContext.supporting_data = context.supporting_data;
    }
    if (context.constraints && context.constraints.trim()) {
      filteredContext.constraints = context.constraints;
    }
    if (context.persona && context.persona.trim()) {
      filteredContext.persona = context.persona;
    }

    return JSON.stringify(filteredContext, null, 2);
  };

  const applyContextToStatement = async () => {
    try {
      const contextData = {
        starting_point: context.starting_point || '',
        intent: context.intent || '',
        supporting_data: context.supporting_data || '',
        constraints: context.constraints || '',
        persona: context.persona || ''
      };

      // Store context to backend
      await axios.post(`${BACKEND_URL}/store-context`, contextData);

      setShowContextPreview(true);
      setShowContextFlyout(false);
    } catch (error) {
      console.error('Error storing context:', error);
      // Still proceed with UI updates even if backend fails
      setShowContextPreview(true);
      setShowContextFlyout(false);
    }
  };

  return (<>
    <div className="container mx-auto p-6 max-w-3xl">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          {/* ClariQ Icon with Toggle */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 rounded-lg hover:bg-blue-50 transition-colors"
            title={isExpanded ? "Minimize view" : "Expand view"}
          >
            <svg
              className="w-10 h-10 text-blue-700"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {/* ClariQ Logo - Letter C with Q inside */}
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10c1.19 0 2.34-.21 3.41-.6"
              />
              <circle
                cx="12"
                cy="12"
                r="4"
                strokeWidth={1.5}
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="m15 15 2 2"
              />
              {/* Expand/Collapse indicator */}
              {isExpanded ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1}
                  d="M8 12h8M12 8v8"
                  opacity="0.5"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1}
                  d="M8 12h8"
                  opacity="0.5"
                />
              )}
            </svg>
          </button>
          <div>
            <h1 className="text-4xl font-bold text-blue-700">ClariQ</h1>
          </div>
        </div>
        <p className="text-lg text-gray-600 italic">Precision that leads to clarity</p>
      </div>
      <form onSubmit={handleGenerate} className="space-y-4">
        <div>
          <div className="font-medium flex items-center gap-2">
            Statement
            <button
              type="button"
              onClick={() => {
                setShowContextFlyout(true);
                loadContextFromBackend();
              }}
              className={`p-1 rounded transition-colors ${
                showContextPreview && hasContextContent()
                  ? 'text-green-600 hover:text-green-800 hover:bg-green-50'
                  : 'text-blue-600 hover:text-blue-800 hover:bg-blue-50'
              }`}
              title={showContextPreview && hasContextContent() ? formatContextStringFiltered() : "Set Context for Better Questions"}
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
          <input value={statement} onChange={e => setStatement(e.target.value)} className="w-full mt-1 p-2 border rounded" placeholder="Enter the statement to analyze" />
          <div className="flex gap-3 mt-3 mb-4">
            <label className="flex items-center gap-2"><input type="radio" name="preset" checked={preset==='complex'} onChange={() => applyPreset('complex')} /> <span className="text-base">Complex Problems</span></label>
            <label className="flex items-center gap-2"><input type="radio" name="preset" checked={preset==='deep'} onChange={() => applyPreset('deep')} /> <span className="text-base">Deep Analysis</span></label>
            <label className="flex items-center gap-2"><input type="radio" name="preset" checked={preset==='decision'} onChange={() => applyPreset('decision')} /> <span className="text-base">Decision Making</span></label>
          </div>
          <hr className="border-gray-300 mb-4" />
        </div>

        {isExpanded && (
          <div>
            <div className="font-medium">Categories (multi-select)</div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {CATEGORIES.map(cat => (
                <button key={cat} type="button" onClick={() => toggleCategory(cat)} className={`p-2 border rounded text-left flex items-center gap-2 ${selected.includes(cat) ? 'bg-blue-100 border-blue-400' : ''}`}>
                  {getCategoryIcon(cat)}
                  <span>{cat}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {isExpanded && (
          <label className="block">
            <div className="font-medium">Number of questions</div>
            <input type="number" min={1} max={20} value={count} onChange={e => setCount(e.target.value)} className="w-24 mt-1 p-2 border rounded" />
          </label>
        )}

        {/* Generate button moved to sticky footer */}
      </form>
  </div>

  {/* Sticky footer for HomePage: Generate button on the right */}
  <div className="fixed left-0 right-0 bottom-0 bg-white border-t p-4">
      <div className="container mx-auto max-w-3xl flex items-center justify-end">
        <button onClick={handleGenerate} disabled={!isGenerateEnabled} className={`px-4 py-2 text-white rounded ${isGenerateEnabled ? 'bg-blue-600' : 'bg-gray-300 cursor-not-allowed'}`}>Generate Questions</button>
      </div>
    </div>

    {/* Context Setting Flyout */}
    {showContextFlyout && (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-end">
        <div className="bg-white w-96 h-full shadow-xl flex flex-col">
          <div className="flex-1 overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Set Context</h2>
                <p className="text-sm text-gray-500 mt-1">All fields are optional - fill what's relevant</p>
              </div>
              <button
                onClick={() => setShowContextFlyout(false)}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              {/* Starting Point */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  Starting Point
                  <span
                    className="text-gray-400 cursor-help"
                    title="A clear statement or hypothesis to explore&#10;Example: We plan to launch our product in Q2."
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </span>
                </label>
                <textarea
                  value={context.starting_point}
                  onChange={(e) => updateContext('starting_point', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md text-sm"
                  rows={2}
                  placeholder="A clear statement or hypothesis to explore"
                />
              </div>

              {/* Intent */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  Intent
                  <span
                    className="text-gray-400 cursor-help"
                    title="What you want to achieve (e.g., evaluate, challenge, clarify)&#10;Example: Evaluate readiness for launch"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </span>
                </label>
                <input
                  type="text"
                  value={context.intent}
                  onChange={(e) => updateContext('intent', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md text-sm"
                  placeholder="What you want to achieve (e.g., evaluate, challenge, clarify)"
                />
              </div>



              {/* Supporting Data */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  Supporting Data
                  <span
                    className="text-gray-400 cursor-help"
                    title="Relevant facts, metrics, or observations&#10;Example: Customer churn dropped by 12% after onboarding changes."
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </span>
                </label>
                <textarea
                  value={context.supporting_data}
                  onChange={(e) => updateContext('supporting_data', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md text-sm"
                  rows={3}
                  placeholder="Relevant facts, metrics, or observations"
                />
              </div>

              {/* Constraints */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  Constraints
                  <span
                    className="text-gray-400 cursor-help"
                    title="Any boundaries like budget, timeline, compliance&#10;Example: Must stay within budget and launch before June."
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </span>
                </label>
                <textarea
                  value={context.constraints}
                  onChange={(e) => updateContext('constraints', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md text-sm"
                  rows={2}
                  placeholder="Any boundaries like budget, timeline, compliance"
                />
              </div>

              {/* Persona */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  Persona
                  <span
                    className="text-gray-400 cursor-help"
                    title="Who is answering (e.g., Product Manager, CTO)&#10;Example: Product Manager"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </span>
                </label>
                <input
                  type="text"
                  value={context.persona}
                  onChange={(e) => updateContext('persona', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md text-sm"
                  placeholder="Who is answering (e.g., Product Manager, CTO)"
                />
              </div>
            </div>
          </div>

          {/* Sticky Action Buttons */}
          <div className="border-t bg-white p-4">
            <div className="flex gap-3">
              <button
                onClick={applyContextToStatement}
                disabled={!hasContextContent()}
                className={`flex-1 px-4 py-2 rounded-md text-sm font-medium ${
                  hasContextContent()
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                Apply to Statement
              </button>
              <button
                onClick={clearContext}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      </div>
    )}
  </>);
}

function QuestionsPage({ initialPayload, initialQuestions, initialSummary, onFinalize, onBack }) {
  const [questions, setQuestions] = useState(initialQuestions || []);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('first'); // first -> next -> final
  const [summary, setSummary] = useState(initialSummary || null);
  const [evaluations, setEvaluations] = useState([]);
  const [pendingNextQuestions, setPendingNextQuestions] = useState([]);
  const navigate = useNavigate();
  const [showRaw, setShowRaw] = useState(false);
  const [expandedItems, setExpandedItems] = useState({});
  // Selection state for plan creation (must be top-level hooks)
  const [selectedRecs, setSelectedRecs] = useState([]);
  const [selectedNext, setSelectedNext] = useState([]);
  const [planResult, setPlanResult] = useState(null);
  const [allRecs, setAllRecs] = useState([]);
  const [allNextSteps, setAllNextSteps] = useState([]);
  const [newRecText, setNewRecText] = useState('');
  const [newNextText, setNewNextText] = useState('');
  const [promptLoading, setPromptLoading] = useState({});
  const contentRef = useRef(null);

  function toggleRec(i) {
    setSelectedRecs(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i]);
  }
  function toggleNext(i) {
    setSelectedNext(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i]);
  }

  async function handleCreatePlan() {
    const selRecs = selectedRecs.map(i => allRecs[i]).filter(Boolean);
    const selNext = selectedNext.map(i => allNextSteps[i]).filter(Boolean);
    // Prefer the applied PreStatement shown at the top UI, then summary-derived statement, then initial payload
    const statementText = (initialPayload && initialPayload.preStatementApplied) || (initialPayload && initialPayload.statement) || '';

    const qaList = (questions || []).map((q, i) => {
      const questionText = typeof q === 'string' ? q : (q && q.question ? q.question : String(q));
      return { question: questionText, answer: answers[i] || '' };
    });
    // Ensure the payload explicitly contains the Input User Statement shown at the top of the UI
    const inputStatement = (summary && summary.FinalResult && summary.FinalResult[0].statement) || '';
    console.log('Creating plan with statement:', inputStatement);
    console.log(summary);
    const payload = {
      statement: inputStatement,
      recommendations: selRecs,
      next_steps: selNext,
      qa: qaList,
    };
    const res = await createPlan(payload);
    setPlanResult(res);
  }

  async function exportToPDF() {
    if (!planResult) {
      alert('Please generate a response first before exporting to PDF.');
      return;
    }

    try {
      // Create a temporary container for PDF content with proper margins
      const pdfContent = document.createElement('div');
      pdfContent.style.padding = '40px 30px'; // Top/bottom: 40px, Left/right: 30px
      pdfContent.style.backgroundColor = 'white';
      pdfContent.style.fontFamily = 'Arial, sans-serif';
      pdfContent.style.lineHeight = '1.6';
      pdfContent.style.maxWidth = '800px';
      pdfContent.style.margin = '0 auto';

      // Get the statement header
      const statementHeader = (summary && summary.FinalResult && summary.FinalResult[0] && summary.FinalResult[0].statement) || 'Precision QA Results';

      // Build PDF content with proper spacing
      let htmlContent = `
        <div style="margin-bottom: 50px;">
          <h1 style="
            color: #1d4ed8;
            border-bottom: 2px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 10px;
            font-size: 32px;
            font-weight: bold;
          ">ClariQ</h1>
          <p style="
            color: #6b7280;
            font-style: italic;
            font-size: 16px;
            margin-bottom: 40px;
          ">Precision that leads to clarity</p>

          <h2 style="
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 20px;
            font-size: 20px;
            font-weight: 600;
          ">User Input Statement</h2>

          <div style="
            background-color: #f8f9fa;
            padding: 25px;
            border-left: 4px solid #3498db;
            margin-bottom: 50px;
            border-radius: 4px;
            font-size: 16px;
            line-height: 1.7;
          ">${statementHeader}</div>
        </div>
      `;

      // Add generated response section with proper spacing
      htmlContent += `
        <div style="margin-bottom: 40px;">
          <h2 style="
            color: #34495e;
            margin-bottom: 25px;
            font-size: 20px;
            font-weight: 600;
          ">Generated Response</h2>

          <div style="
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
            padding: 25px;
            background-color: #ffffff;
          ">
      `;

      // Extract the plan content
      let planContent = '';
      if (typeof planResult === 'string') {
        planContent = planResult;
      } else if (planResult && planResult.plan) {
        planContent = typeof planResult.plan === 'string' ? planResult.plan : JSON.stringify(planResult.plan, null, 2);
      } else {
        planContent = JSON.stringify(planResult, null, 2);
      }

      // Use the existing mdToHtml function for proper markdown conversion
      const convertedHtml = mdToHtml(planContent);

      // Add custom CSS for better spacing in the markdown content
      const styledHtml = convertedHtml.replace(
        '<div class="md-rendered">',
        `<div class="md-rendered" style="
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          line-height: 1.8;
          color: #333;
        ">`
      ).replace(
        /<style>[\s\S]*?<\/style>/,
        `<style>
          .md-rendered {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.8;
            color: #333;
          }
          .md-rendered h1 {
            font-size: 1.8em;
            margin: 30px 0 20px 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
          }
          .md-rendered h2 {
            font-size: 1.5em;
            margin: 25px 0 15px 0;
            color: #34495e;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 8px;
          }
          .md-rendered h3 {
            font-size: 1.3em;
            margin: 20px 0 12px 0;
            color: #555;
          }
          .md-rendered p {
            margin: 15px 0;
            font-size: 16px;
          }
          .md-rendered ul, .md-rendered ol {
            margin: 15px 0 15px 25px;
            padding-left: 20px;
          }
          .md-rendered li {
            margin: 8px 0;
            line-height: 1.7;
          }
          .md-rendered hr {
            border: 0;
            border-top: 2px solid #ddd;
            margin: 30px 0;
          }
          .md-rendered strong {
            font-weight: 600;
            color: #2c3e50;
          }
          .md-rendered em {
            font-style: italic;
            color: #7f8c8d;
          }
          .md-rendered pre {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 20px 0;
            font-size: 14px;
          }
          .md-rendered code {
            background-color: #e8e8e8;
            color: #c7254e;
            padding: 3px 6px;
            border-radius: 4px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
          }
          .md-rendered blockquote {
            border-left: 4px solid #3498db;
            margin: 20px 0;
            padding: 15px 20px;
            background-color: #f8f9fa;
            font-style: italic;
          }
        </style>`
      );

      htmlContent += styledHtml;
      htmlContent += `</div></div>`;

      pdfContent.innerHTML = htmlContent;
      document.body.appendChild(pdfContent);

      // Generate PDF as single continuous page without page breaks
      const canvas = await html2canvas(pdfContent, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff'
      });

      const imgData = canvas.toDataURL('image/png');

      // Calculate dimensions for single page
      const margin = 15; // 15mm margins on all sides
      const contentWidth = 180; // 210mm - 30mm margins = 180mm content width
      const imgWidth = contentWidth;
      const imgHeight = (canvas.height * contentWidth) / canvas.width;

      // Create PDF with custom page size to fit all content
      const pageWidth = 210; // A4 width
      const pageHeight = imgHeight + (margin * 2); // Height to fit all content + margins

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: [pageWidth, pageHeight]
      });

      // Add the entire content as a single image with margins
      pdf.addImage(imgData, 'PNG', margin, margin, imgWidth, imgHeight);

      // Clean up
      document.body.removeChild(pdfContent);

      // Save the PDF
      const fileName = `ClariQ-response-${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);

    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Error generating PDF. Please try again.');
    }
  }

  // initialize allRecs/allNextSteps from summary when it becomes available
  useEffect(() => {
    if (!summary) return;
    const raw = (summary.summary && summary.summary.FinalResult) ? summary.summary.FinalResult : (summary.FinalResult || summary.summary || summary);
    const finalObj = Array.isArray(raw) ? (raw.length > 0 ? raw[0] : {}) : (raw || {});
    const recommendations = Array.isArray(finalObj.recommendations) ? finalObj.recommendations : (finalObj.recommendations ? [finalObj.recommendations] : (Array.isArray(finalObj.recs) ? finalObj.recs : (finalObj.recs ? [finalObj.recs] : [])));
    const nextSteps = Array.isArray(finalObj.next_steps) ? finalObj.next_steps : (Array.isArray(finalObj.nextSteps) ? finalObj.nextSteps : (finalObj.next_steps ? [finalObj.next_steps] : (finalObj.next ? (Array.isArray(finalObj.next) ? finalObj.next : [finalObj.next]) : [])));
    setAllRecs(recommendations || []);
    setAllNextSteps(nextSteps || []);
    // reset selections
    setSelectedRecs([]);
    setSelectedNext([]);
    setPlanResult(null);
  }, [summary]);

  function addManualRec() {
    if (!newRecText || !newRecText.trim()) return;
    const text = newRecText.trim();
    setAllRecs(prev => {
      const next = [...prev, text];
      // select the new index
      setSelectedRecs(prevSel => [...prevSel, next.length - 1]);
      return next;
    });
    setNewRecText('');
  }

  function addManualNext() {
    if (!newNextText || !newNextText.trim()) return;
    const text = newNextText.trim();
    setAllNextSteps(prev => {
      const next = [...prev, text];
      setSelectedNext(prevSel => [...prevSel, next.length - 1]);
      return next;
    });
    setNewNextText('');
  }

  useEffect(() => {
    if (initialSummary) {
      setSummary(initialSummary);
      setStage('final');
    }
  }, [initialSummary]);

  function updateAnswer(idx, value) {
    setAnswers(prev => ({ ...prev, [idx]: value }));
  }

  async function fillWithPrompt(idx) {
    const question = questions[idx];
    const questionText = typeof question === 'string' ? question : (question && question.question ? question.question : JSON.stringify(question));
    const preStatement = initialPayload && initialPayload.preStatementApplied ? initialPayload.preStatementApplied : '';

    const prompt = `In Precise Question and Answering, with the Context: "${preStatement}"

Provide a precise response in less than 30 words to the following Question: ${questionText}
`;

    // Set loading state for this specific question
    setPromptLoading(prev => ({ ...prev, [idx]: true }));

    try {
      // Call the backend API to get LLM response
      const response = await getPromptResponse(prompt);
      updateAnswer(idx, response);
    } catch (error) {
      console.error('Error getting prompt response:', error);
      updateAnswer(idx, 'Error: Unable to get AI response. Please try again.');
    } finally {
      // Clear loading state
      setPromptLoading(prev => ({ ...prev, [idx]: false }));
    }
  }

  async function handleSubmit() {
    setLoading(true);
    // Build structured payload: keep 'qa' as list of {question, answer, category?}
    // and also include a simple 'questions' array of strings for backward compatibility.
    const qaList = questions.map((q, i) => {
      const questionText = typeof q === 'string' ? q : (q && q.question ? q.question : String(q));
      const category = (q && q.category) ? q.category : undefined;
      return { question: questionText, answer: answers[i] || '', ...(category ? { category } : {}) };
    });

    const payload = {
      statement: initialPayload.statement,
      qa: qaList,
    };

    console.log('Submitting answers payload:', payload);
    // First, evaluate answers (this returns evaluations with rating/explanation/next_questions)
    const evals = await evaluateAnswers(payload);
    setLoading(false);

    // Expect evals to be an array of {question, answer, rating, explanation, next_questions}
    if (Array.isArray(evals)) {
      setEvaluations(evals);
      // collect any next-level questions
      const nextQs = [];
      evals.forEach(e => {
        if (e.next_questions && e.next_questions.length > 0) {
          nextQs.push(...e.next_questions);
        }
      });

      if (nextQs.length > 0) {
        // show a review screen with evaluations and the next-level questions listed
        setPendingNextQuestions(nextQs);
        setStage('review');
        return;
      }
    }

    // If no next questions returned, call final evaluation directly
    const finalPayload = {
      statement: initialPayload.statement,
      qa: qaList,
    };
    const finalRes = await finalEvaluation(finalPayload);
    setSummary(finalRes);
    setStage('final');
    onFinalize && onFinalize(finalRes);
  }

  function proceedToNext() {
    if (pendingNextQuestions && pendingNextQuestions.length > 0) {
      setQuestions(pendingNextQuestions);
      setAnswers({});
      setPendingNextQuestions([]);
      setStage('next');
    }
  }

  async function skipToFinal() {
    setLoading(true);
    const finalPayload = {
      statement: initialPayload.statement,
      qa: questions.map((q, i) => ({ question: typeof q === 'string' ? q : (q && q.question ? q.question : String(q)), answer: answers[i] || '' })),
    };
    const finalRes = await finalEvaluation(finalPayload);
    setLoading(false);
    setSummary(finalRes);
    setStage('final');
    onFinalize && onFinalize(finalRes);
  }

  async function exportEvaluationToPDF() {
    if (!evaluations || evaluations.length === 0) {
      alert('No evaluations available to export.');
      return;
    }

    try {
      // Create a temporary container for PDF content
      const pdfContent = document.createElement('div');
      pdfContent.style.padding = '40px 30px';
      pdfContent.style.backgroundColor = 'white';
      pdfContent.style.fontFamily = 'Arial, sans-serif';
      pdfContent.style.lineHeight = '1.6';
      pdfContent.style.maxWidth = '800px';
      pdfContent.style.margin = '0 auto';

      // Get the statement
      const statementText = (initialPayload && initialPayload.preStatementApplied) || (initialPayload && initialPayload.statement) || 'Evaluation Review';

      // Helper function to extract question text
      const extractQuestionInfo = (questionObj) => {
        if (typeof questionObj === 'string') {
          return { text: questionObj, category: null };
        }
        if (questionObj && typeof questionObj === 'object') {
          const text = questionObj.question || questionObj.text || JSON.stringify(questionObj);
          const category = questionObj.category || null;
          return { text, category };
        }
        return { text: String(questionObj || 'Unknown question'), category: null };
      };

      // Build PDF content
      let htmlContent = `
        <div style="margin-bottom: 40px;">
          <h1 style="
            color: #1d4ed8;
            border-bottom: 2px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 10px;
            font-size: 32px;
            font-weight: bold;
          ">ClariQ</h1>
          <p style="
            color: #6b7280;
            font-style: italic;
            font-size: 16px;
            margin-bottom: 20px;
          ">Precision that leads to clarity</p>
          <h2 style="
            color: #2c3e50;
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 30px;
          ">Evaluation Review Report</h2>

          <h2 style="
            color: #34495e;
            margin-bottom: 15px;
            font-size: 18px;
            font-weight: 600;
          ">Statement</h2>

          <div style="
            background-color: #f8f9fa;
            padding: 20px;
            border-left: 4px solid #3498db;
            margin-bottom: 40px;
            border-radius: 4px;
            font-size: 15px;
            line-height: 1.6;
          ">${statementText}</div>
        </div>
      `;

      // Add evaluations
      htmlContent += `
        <div style="margin-bottom: 30px;">
          <h2 style="
            color: #34495e;
            margin-bottom: 25px;
            font-size: 20px;
            font-weight: 600;
          ">Question Evaluations</h2>
      `;

      evaluations.forEach((ev, i) => {
        const mainQuestion = extractQuestionInfo(ev.question);

        htmlContent += `
          <div style="
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            background-color: #ffffff;
          ">
            <div style="
              font-weight: 600;
              font-size: 16px;
              margin-bottom: 12px;
              color: #2c3e50;
            ">
              Question ${i + 1}: ${mainQuestion.text}
              ${mainQuestion.category ? `<span style="color: #6c757d; font-size: 14px; font-weight: normal;"> (${mainQuestion.category})</span>` : ''}
            </div>

            <div style="margin-bottom: 10px;">
              <strong>Your Answer:</strong> ${ev.answer || 'No answer provided'}
            </div>

            <div style="margin-bottom: 10px;">
              <strong>Rating:</strong> <span style="color: #27ae60; font-weight: bold; font-size: 18px;">${ev.rating}/10</span>
            </div>

            <div style="margin-bottom: 15px;">
              <strong>Explanation:</strong> ${ev.explanation || 'No explanation provided'}
            </div>
        `;

        // Add next-level questions if available
        if (ev.next_questions && ev.next_questions.length > 0) {
          htmlContent += `
            <div style="
              background-color: #f8f9fa;
              padding: 15px;
              border-radius: 4px;
              margin-top: 15px;
            ">
              <div style="font-weight: 600; margin-bottom: 10px;">Next-level Questions:</div>
              <ol style="margin: 0; padding-left: 20px;">
          `;

          ev.next_questions.forEach((nq) => {
            const nextQuestion = extractQuestionInfo(nq);
            htmlContent += `
              <li style="margin-bottom: 8px; line-height: 1.5;">
                ${nextQuestion.text}
                ${nextQuestion.category ? `<span style="color: #6c757d; font-size: 12px;"> (${nextQuestion.category})</span>` : ''}
              </li>
            `;
          });

          htmlContent += `
              </ol>
            </div>
          `;
        }

        htmlContent += `</div>`;
      });

      htmlContent += `</div>`;

      pdfContent.innerHTML = htmlContent;
      document.body.appendChild(pdfContent);

      // Generate PDF as single continuous page
      const canvas = await html2canvas(pdfContent, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff'
      });

      const imgData = canvas.toDataURL('image/png');

      // Calculate dimensions for single page
      const margin = 15;
      const contentWidth = 180;
      const imgWidth = contentWidth;
      const imgHeight = (canvas.height * contentWidth) / canvas.width;

      // Create PDF with custom page size
      const pageWidth = 210;
      const pageHeight = imgHeight + (margin * 2);

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: [pageWidth, pageHeight]
      });

      pdf.addImage(imgData, 'PNG', margin, margin, imgWidth, imgHeight);

      // Clean up
      document.body.removeChild(pdfContent);

      // Save the PDF
      const fileName = `ClariQ-evaluation-${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);

    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Error generating PDF. Please try again.');
    }
  }

  if (stage === 'final' && summary) {
    // Normalize different backend shapes: { summary: { items,... } } or { answers: [...] }
  const raw = (summary.summary && summary.summary.FinalResult) ? summary.summary.FinalResult : (summary.FinalResult || summary.summary || summary);
  // If provider returned an array (e.g. [ { statement, readiness_score, ... } ]) normalize to first object
  const finalObj = Array.isArray(raw) ? (raw.length > 0 ? raw[0] : {}) : (raw || {});
  const items = finalObj.items || finalObj.answers || [];
  const readinessRaw = finalObj.readiness_score ?? finalObj.overall_readiness ?? finalObj.readiness ?? null;
  // normalize recommendations and next steps to arrays
  const recommendations = Array.isArray(finalObj.recommendations) ? finalObj.recommendations : (finalObj.recommendations ? [finalObj.recommendations] : (Array.isArray(finalObj.recs) ? finalObj.recs : (finalObj.recs ? [finalObj.recs] : [])));
  const nextSteps = Array.isArray(finalObj.next_steps) ? finalObj.next_steps : (Array.isArray(finalObj.nextSteps) ? finalObj.nextSteps : (finalObj.next_steps ? [finalObj.next_steps] : (finalObj.next ? (Array.isArray(finalObj.next) ? finalObj.next : [finalObj.next]) : [])));

    function renderValue(v) {
      if (v === null || v === undefined) return <span className="text-gray-600">(none)</span>;
      if (Array.isArray(v)) {
        if (v.length === 0) return <span className="text-gray-600">(empty list)</span>;
        // array of primitives
        if (typeof v[0] !== 'object') {
          return (
            <ul className="list-disc list-inside mt-2">
              {v.map((x, i) => <li key={i}>{String(x)}</li>)}
            </ul>
          );
        }
        // array of objects
        return (
          <div className="space-y-2 mt-2">
            {v.map((obj, i) => (
              <div key={i} className="p-2 border rounded bg-white">
                <pre className="text-xs m-0 overflow-auto">{JSON.stringify(obj, null, 2)}</pre>
              </div>
            ))}
          </div>
        );
      }
      if (typeof v === 'object') {
        return <pre className="text-xs mt-2 overflow-auto">{JSON.stringify(v, null, 2)}</pre>;
      }
      return <div className="mt-1">{String(v)}</div>;
    }

  // Simple final-only UI: Statement header, readiness pie chart, Recommendations and NextSteps lists
    const statementHeader = finalObj.statement || finalObj.summary || finalObj.title || 'Final Result';
    // parse readiness into 0-100 integer
    let readinessPct = null;
    if (typeof readinessRaw === 'number') {
      readinessPct = Math.max(0, Math.min(100, Math.round(readinessRaw)));
    } else if (typeof readinessRaw === 'string') {
      const parsed = Number(readinessRaw.replace('%', '').trim());
      readinessPct = Number.isFinite(parsed) ? Math.max(0, Math.min(100, Math.round(parsed))) : null;
    }

    function Pie({ pct = 0, size = 120, stroke = 12 }) {
      const r = (size - stroke) / 2;
      const c = 2 * Math.PI * r;
      const dash = (pct / 100) * c;
      return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <g transform={`translate(${size/2}, ${size/2})`}>
            <circle r={r} cx={0} cy={0} fill="transparent" stroke="#e5e7eb" strokeWidth={stroke} />
            <circle r={r} cx={0} cy={0} fill="transparent" stroke="#10b981" strokeWidth={stroke} strokeDasharray={`${dash} ${c - dash}`} strokeLinecap="round" transform="rotate(-90)" />
            <text x={0} y={4} textAnchor="middle" fontSize={18} fontWeight={600}>{pct}%</text>
          </g>
        </svg>
      );
    }

    return (
      <div className="container mx-auto p-6 max-w-3xl pb-24" ref={contentRef}>
        <div className="mb-2 text-sm text-gray-500">Input User Statement</div>
        <h1 className="text-2xl font-bold mb-4">{statementHeader}</h1>

        <div className="flex items-center gap-6 mb-6">
          <div>
            <Pie pct={isNaN(readinessPct) ? 0 : readinessPct} />
          </div>
          <div>
            <div className="font-medium">Readiness</div>
            <div className="text-lg mt-2">{isNaN(readinessPct) ? 'n/a' : `${readinessPct}%`}</div>
            {finalObj.explanation && <div className="mt-2 text-gray-700">{finalObj.explanation}</div>}
          </div>
        </div>

        <div className="space-y-6">
          <div className="p-4 border rounded bg-white">
            <div className="font-medium mb-3">Recommendations</div>
            {Array.isArray(allRecs) && allRecs.length > 0 ? (
              <div className="space-y-3">
                {allRecs.map((r, i) => (
                  <label key={i} className="flex items-center gap-3">
                    <input type="checkbox" checked={selectedRecs.includes(i)} onChange={() => toggleRec(i)} />
                    <div className="text-sm text-gray-800">{r}</div>
                  </label>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">No recommendations provided.</div>
            )}

            <div className="mt-3 flex gap-2">
              <input value={newRecText} onChange={e => setNewRecText(e.target.value)} placeholder="Add manual recommendation" className="flex-1 p-2 border rounded" />
              <button onClick={addManualRec} className="px-3 py-2 bg-blue-600 text-white rounded">Add</button>
            </div>
          </div>

          <div className="p-4 border rounded bg-white">
            <div className="font-medium mb-3">Next Steps</div>
            {Array.isArray(allNextSteps) && allNextSteps.length > 0 ? (
              <div className="space-y-3">
                {allNextSteps.map((n, i) => (
                  <label key={i} className="flex items-center gap-3">
                    <input type="checkbox" checked={selectedNext.includes(i)} onChange={() => toggleNext(i)} />
                    <div className="text-sm text-gray-800">{n}</div>
                  </label>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">No next steps provided.</div>
            )}

            <div className="mt-3 flex gap-2">
              <input value={newNextText} onChange={e => setNewNextText(e.target.value)} placeholder="Add manual next step" className="flex-1 p-2 border rounded" />
              <button onClick={addManualNext} className="px-3 py-2 bg-blue-600 text-white rounded">Add</button>
            </div>
          </div>

          {/* Buttons moved to sticky footer to keep them visible at the bottom */}

          {planResult ? (() => {
            // Reuse deep parser from PlanMarkdownViewer area to find markdown string
            function deepParseCandidateLocal(x) {
              if (x === null || x === undefined) return x;
              if (typeof x === 'string') {
                const s = x.trim();
                if (s.startsWith('{') || s.startsWith('[')) {
                  try { return deepParseCandidateLocal(JSON.parse(s)); } catch (e) { return x; }
                }
                return x;
              }
              if (Array.isArray(x)) return x.map(deepParseCandidateLocal);
              if (typeof x === 'object') {
                const out = {};
                let changed = false;
                for (const k of Object.keys(x)) {
                  const v = x[k];
                  const parsed = deepParseCandidateLocal(v);
                  out[k] = parsed;
                  if (parsed !== v) changed = true;
                }
                const keys = Object.keys(x);
                if (!changed && keys.length === 1 && typeof x[keys[0]] === 'string') {
                  const only = x[keys[0]].trim();
                  if (only.startsWith('{') || only.startsWith('[')) {
                    try { return deepParseCandidateLocal(JSON.parse(only)); } catch (e) {}
                  }
                }
                return out;
              }
              return x;
            }

            let p = deepParseCandidateLocal(planResult);
            if (p && typeof p === 'object' && p.plan) p = deepParseCandidateLocal(p.plan);

            // If plan is a markdown string, normalize setext headers and render HTML
            if (typeof p === 'string') {
              function normalizeSetextHeaders(s) {
                const lines = String(s).split(/\r?\n/);
                const out = [];
                for (let i = 0; i < lines.length; i++) {
                  const cur = lines[i];
                  const nxt = lines[i + 1] || '';
                  if (/^[=]{3,}\s*$/.test(nxt)) { out.push('# ' + cur); i++; continue; }
                  if (/^[-]{3,}\s*$/.test(nxt)) { out.push('## ' + cur); i++; continue; }
                  out.push(cur);
                }
                return out.join('\n');
              }
              const mdSource = normalizeSetextHeaders(p);
                const renderedHtml = mdToHtml(mdSource);
              return (
                <div className="mt-4 p-4 border rounded bg-white">
                  <div dangerouslySetInnerHTML={{ __html: renderedHtml }} />
                </div>
              );
            }

            // otherwise show nothing (structured render remains available elsewhere)
            return null;
          })() : null}
        </div>

        {/* Sticky footer with action buttons */}
        <div className="fixed left-0 right-0 bottom-0 bg-white border-t p-4">
          <div className="container mx-auto max-w-3xl flex items-center justify-between">
            <div>
              <button onClick={() => setStage('review')} className="px-4 py-2 bg-gray-100 rounded">Back</button>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={handleCreatePlan} className="px-4 py-2 bg-indigo-600 text-white rounded flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Generate Response
              </button>
              <button
                onClick={exportToPDF}
                disabled={!planResult}
                className={`px-4 py-2 rounded flex items-center gap-2 ${
                  planResult
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
                title={planResult ? "Export PDF" : "Generate a response first to export PDF"}
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export PDF
              </button>
              <button onClick={() => navigate('/')} className="px-4 py-2 bg-red-600 text-white rounded">Restart</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (stage === 'review') {
    return (
      <div className="container mx-auto p-6 max-w-3xl">
        <h2 className="text-2xl font-semibold mb-4">Evaluation Review</h2>
        {initialPayload && initialPayload.preStatementApplied && (
          <div className="mt-2 text-sm text-gray-600">PreStatement: {initialPayload.preStatementApplied}</div>
        )}
        <p className="mb-4">Below are the evaluations for your answers. Review ratings, explanations and the generated next-level questions. You can proceed to answer the next-level questions or skip to final evaluation.</p>

        <div className="space-y-4">
          {evaluations.map((ev, i) => {
            // Helper function to extract question text and category from question object
            const extractQuestionInfo = (questionObj) => {
              if (typeof questionObj === 'string') {
                return { text: questionObj, category: null };
              }
              if (questionObj && typeof questionObj === 'object') {
                const text = questionObj.question || questionObj.text || JSON.stringify(questionObj);
                const category = questionObj.category || null;
                return { text, category };
              }
              return { text: String(questionObj || 'Unknown question'), category: null };
            };

            // Extract main question info
            const mainQuestion = extractQuestionInfo(ev.question);

            return (
              <div key={i} className="p-4 border rounded">
                <div className="font-medium">
                  Q: {mainQuestion.text}
                  {mainQuestion.category && <span className="text-sm text-gray-500 ml-2">({mainQuestion.category})</span>}
                </div>
                <div className="mt-1">Your answer: <span className="font-semibold">{ev.answer}</span></div>
                <div className="mt-2">Rating: <span className="font-bold">{ev.rating}/10</span></div>
                <div className="mt-2 text-gray-700">Explanation: {ev.explanation}</div>
                {ev.next_questions && ev.next_questions.length > 0 && (
                  <div className="mt-3">
                    <div className="font-medium">Next-level Questions:</div>
                    <ol className="list-decimal list-inside mt-1 space-y-1">
                      {ev.next_questions.map((nq, j) => {
                        const nextQuestion = extractQuestionInfo(nq);
                        return (
                          <li key={j} className="text-sm text-gray-800">
                            {nextQuestion.text}
                            {nextQuestion.category && <span className="text-xs text-gray-400 ml-1">({nextQuestion.category})</span>}
                          </li>
                        );
                      })}
                    </ol>
                  </div>
                )}
              </div>
            );
          })}
        

        <div className="mt-6 flex items-center justify-between">
          <div className="flex gap-3">
            <button onClick={() => setStage('first')} className="px-4 py-2 bg-gray-100 rounded">Back</button>
            <button
              onClick={exportEvaluationToPDF}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded flex items-center gap-2"
              title="Export Evaluation Review as PDF"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export PDF
            </button>
          </div>
          <div className="flex gap-3">
            <button onClick={proceedToNext} className="px-4 py-2 bg-blue-600 text-white rounded">Proceed to Next-level Questions</button>
            <button onClick={skipToFinal} className="px-4 py-2 bg-gray-200 rounded">Skip to Final Evaluation</button>
          </div>
        </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-3xl">
      <div className="mb-4">
        <h2 className="text-2xl font-semibold">{stage === 'first' ? 'Questions' : 'Next-level Questions'}</h2>
        {initialPayload && initialPayload.preStatementApplied && (
          <div className="mt-2 text-sm text-gray-600">PreStatement: {initialPayload.preStatementApplied}</div>
        )}
      </div>
      <div className="space-y-4">
        {questions.map((q, i) => {
          const text = typeof q === 'string' ? q : (q && q.question ? q.question : JSON.stringify(q));
          const category = (q && q.category) ? q.category : null;
          return (
            <div key={i} className="p-3 border rounded">
              <div className="font-medium">{i + 1}. {text} {category ? <span className="text-sm text-gray-500">({category})</span> : null}</div>
              <div className="mt-2 flex gap-2">
                <textarea value={answers[i] || ''} onChange={e => updateAnswer(i, e.target.value)} className="flex-1 p-2 border rounded" rows={3} />
                <button
                  onClick={() => fillWithPrompt(i)}
                  disabled={promptLoading[i]}
                  className={`px-3 py-2 border border-blue-300 rounded text-sm whitespace-nowrap self-start flex items-center gap-1 ${
                    promptLoading[i]
                      ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-100 hover:bg-blue-200 text-blue-700'
                  }`}
                  title="Fill with AI response"
                >
                  {promptLoading[i] ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Loading...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      AI
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <div>
          <button onClick={() => { onBack && onBack(); navigate('/'); }} className="px-3 py-1 bg-gray-100 rounded">Back</button>
        </div>
        <div>
          <button onClick={handleSubmit} disabled={loading} className="px-4 py-2 bg-green-600 text-white rounded">{loading ? 'Submitting...' : 'Submit Answers'}</button>
        </div>
      </div>
    </div>
  );
}

function About() {
  return (
    <div className="container mx-auto p-6">
      <h2 className="text-2xl font-semibold">About</h2>
      <p className="mt-2">This is a minimal FastAPI + React starter app with a simple QA flow.</p>
    </div>
  );
}

export default function App() {
  const [flow, setFlow] = useState({ page: 'home' });

  const navigate = useNavigate();
  function handleGenerate(questions, payload) {
    setFlow({ page: 'questions', questions, payload });
    // navigate to flow route
    navigate('/flow');
  }

  function handleFinalize(res) {
    setFlow({ page: 'final', summary: res.summary || res });
  }

  return (
    <Routes>
      <Route path="/" element={<HomePage onGenerate={handleGenerate} initialPayload={flow.page === 'questions' ? flow.payload : (flow.page === 'final' ? flow.payload : undefined)} />} />
      <Route path="/about" element={<About />} />
      <Route path="/flow" element={
        flow.page === 'questions'
          ? <QuestionsPage initialQuestions={flow.questions} initialPayload={flow.payload} onFinalize={handleFinalize} onBack={() => setFlow({ page: 'home', payload: flow.payload })} />
          : flow.page === 'final'
            ? <QuestionsPage initialQuestions={flow.questions} initialPayload={flow.payload} initialSummary={flow.summary} onFinalize={handleFinalize} onBack={() => setFlow({ page: 'home', payload: flow.payload })} />
            : <div className="container mx-auto p-6">No active flow. <Link to="/">Go Home</Link></div>
      } />
    </Routes>
  );
}
