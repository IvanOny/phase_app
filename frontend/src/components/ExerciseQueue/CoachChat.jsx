import { useState, useRef, useEffect } from 'react';
import { chatCoach } from '../../api/exqClient.js';

const SUGGESTIONS = [
  'How is my bench progressing?',
  'Am I neglecting any muscle group?',
  'Should I deload soon?',
  'What did I train last week?',
];

function Trace({ steps }) {
  return (
    <details className="exq-trace">
      <summary>🐛 Debug trace — {steps.length} steps</summary>
      {steps.map((s, i) => {
        if (s.step === 'system_prompt') return (
          <details key={i} className="exq-trace-step">
            <summary>📋 system prompt (the snapshot Claude starts with)</summary>
            <pre className="exq-trace-pre">{s.content}</pre>
          </details>
        );
        if (s.step === 'reasoning') return (
          <div key={i} className="exq-trace-step">
            <span className="exq-trace-tag exq-trace-tag--think">💭 reasoning</span>
            <div className="exq-trace-text">{s.content}</div>
          </div>
        );
        if (s.step === 'tool_call') return (
          <div key={i} className="exq-trace-step">
            <span className="exq-trace-tag exq-trace-tag--call">🔧 calls {s.name}</span>
            <code className="exq-trace-code">{JSON.stringify(s.input)}</code>
          </div>
        );
        if (s.step === 'tool_result') return (
          <details key={i} className="exq-trace-step">
            <summary>📤 {s.name} → result</summary>
            <pre className="exq-trace-pre">{s.content}</pre>
          </details>
        );
        return null;
      })}
    </details>
  );
}

export default function CoachChat() {
  const [messages, setMessages] = useState([]); // { role, content, trace? }
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [debug, setDebug] = useState(() => localStorage.getItem('exq-coach-debug') === '1');
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, busy]);

  function toggleDebug() {
    setDebug(d => { const n = !d; localStorage.setItem('exq-coach-debug', n ? '1' : '0'); return n; });
  }

  async function send(text) {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    setErr(null);
    const next = [...messages, { role: 'user', content }];
    setMessages(next);
    setInput('');
    setBusy(true);
    try {
      const res = await chatCoach(next.map(m => ({ role: m.role, content: m.content })), debug);
      setMessages(m => [...m, { role: 'assistant', content: res.reply, trace: res.trace }]);
    } catch (e) {
      setErr(e.message);
      setMessages(m => m.slice(0, -1)); // drop the user msg so they can retry
      setInput(content);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="exq-chat">
      <div className="exq-chat-bar">
        <button
          className={`exq-btn${debug ? ' active' : ''}`}
          onClick={toggleDebug}
          title="Show the system prompt, tool calls, results and reasoning behind each answer"
        >🐛 Debug {debug ? 'on' : 'off'}</button>
      </div>

      <div className="exq-chat-log">
        {messages.length === 0 && (
          <div className="exq-chat-empty">
            <p>Ask your coach anything — it can see your training logs.</p>
            <div className="exq-chat-chips">
              {SUGGESTIONS.map(s => (
                <button key={s} className="exq-chat-chip" onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`exq-msg exq-msg--${m.role}`}>
            <div className="exq-msg-col">
              <div className="exq-msg-bubble">{m.content}</div>
              {m.trace && <Trace steps={m.trace} />}
            </div>
          </div>
        ))}
        {busy && <div className="exq-msg exq-msg--assistant"><div className="exq-msg-bubble exq-msg-typing">…</div></div>}
        {err && <div className="exq-error">{err}</div>}
        <div ref={endRef} />
      </div>

      <div className="exq-chat-input">
        <textarea
          rows={1}
          value={input}
          placeholder="Ask about your training…"
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
        />
        <button className="exq-btn active" onClick={() => send()} disabled={busy || !input.trim()}>Send</button>
      </div>
    </div>
  );
}
