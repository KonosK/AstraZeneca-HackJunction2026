import { useEffect, useRef } from "react";

export type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

export function CheckupChat({
  messages,
  draft,
  busy,
  started,
  onDraftChange,
  onSend,
  onStart,
}: {
  messages: ChatMessage[];
  draft: string;
  busy: boolean;
  started: boolean;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onStart: () => void;
}) {
  const thread = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = thread.current;
    if (!el) return;
    // Scroll only inside the thread — never jump the page.
    el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  if (!started) {
    return (
      <div className="checkup-chat start">
        <p>
          Start a Thriver Care checkup with SILTA. Talk about how you feel
          first; when the checkup is ready to share with your care team, SILTA
          will tell you.
        </p>
        <button className="primary" onClick={onStart}>
          Start cancer checkup
        </button>
      </div>
    );
  }

  return (
    <div className="checkup-chat">
      <div className="checkup-chat-meta">
        <span className="small">Synthetic demo · not a clinical visit</span>
      </div>
      <div
        ref={thread}
        className="checkup-thread"
        role="log"
        aria-live="polite"
      >
        {messages.map((m) => (
          <div key={m.id} className={`checkup-bubble ${m.role}`}>
            <strong>{m.role === "assistant" ? "SILTA" : "You"}</strong>
            <p>{m.content}</p>
          </div>
        ))}
        {busy && (
          <div className="checkup-bubble assistant">
            <strong>SILTA</strong>
            <p>Thinking…</p>
          </div>
        )}
      </div>
      <form
        className="checkup-compose"
        onSubmit={(e) => {
          e.preventDefault();
          if (!busy && draft.trim()) onSend();
        }}
      >
        <label className="sr-only" htmlFor="checkup-draft">
          Message to SILTA
        </label>
        <textarea
          id="checkup-draft"
          rows={2}
          value={draft}
          disabled={busy}
          placeholder="Type your answer…"
          onChange={(e) => onDraftChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (!busy && draft.trim()) onSend();
            }
          }}
        />
        <button className="primary" type="submit" disabled={busy || !draft.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
