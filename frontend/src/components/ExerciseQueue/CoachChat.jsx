import { useState, useRef, useEffect } from 'react';
import { chatCoach } from '../../api/exqClient.js';

const SUGGESTIONS = [
  'How is my bench progressing?',
  'Am I neglecting any muscle group?',
  'Should I deload soon?',
  'What did I train last week?',
];

export default function CoachChat() {
  const [messages, setMessages] = useState([]); // { role, content }
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, busy]);

  async function send(text) {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    setErr(null);
    const next = [...messages, { role: 'user', content }];
    setMessages(next);
    setInput('');
    setBusy(true);
    try {
      const reply = await chatCoach(next);
      setMessages(m => [...m, { role: 'assistant', content: reply }]);
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
            <div className="exq-msg-bubble">{m.content}</div>
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
