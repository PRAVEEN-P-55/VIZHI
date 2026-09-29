import { useEffect, useState } from "react";
import client from "../api/client";

export default function AIChatPanel({ context, onClose }) {
  const [messages, setMessages] = useState([{ role: "agent", text: "VIZHI Intelligence Agent online. Ask about risk zones, complaints, or request a district brief." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const closeOnEscape = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  const send = async (suggestion) => {
    const query = suggestion ?? input;
    if (!query.trim() || busy) return;
    setMessages((items) => [...items, { role: "user", text: query }]);
    setInput("");
    setBusy(true);
    try {
      const { data } = await client.post("/agent/query", {
        query,
        district: context?.district || null,
        complaint_id: context?.complaint_id || null,
      });
      setMessages((items) => [...items, { role: "agent", text: data.answer, mode: data.mode, brief: data.brief, district: data.focus_district }]);
    } catch (error) {
      setMessages((items) => [...items, { role: "agent", text: `Request failed: ${error.response?.data?.detail || error.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  const exportPDF = async (brief, district) => {
    const { jsPDF } = await import("jspdf");
    const document = new jsPDF();
    document.setFontSize(16);
    document.text("VIZHI Intelligence Brief", 14, 18);
    document.setFontSize(10);
    document.text(`I4C / CIS Division — generated ${new Date().toLocaleString()}`, 14, 25);
    document.setDrawColor(21, 94, 239);
    document.line(14, 28, 196, 28);
    let y = 38;
    document.setFontSize(11);
    (brief.brief_text || "").split("\n").forEach((line) => {
      document.text(line, 14, y);
      y += 7;
    });
    document.setFontSize(8);
    document.setTextColor(93, 107, 130);
    document.text("Generated from VIZHI predictive output; traceable to district-level sources.", 14, y + 4);
    document.save(`vizhi_brief_${district || "district"}.pdf`);
  };

  return (
    <div className="fixed right-0 top-0 z-50 flex h-full w-full flex-col border-l border-slate-200 bg-white shadow-2xl sm:w-[440px]" role="dialog" aria-label="VIZHI intelligence assistant">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div><div className="font-semibold text-accent">VIZHI Intelligence Agent</div>{context?.district && <div className="text-xs text-muted">Context: {context.district}</div>}</div>
        <button onClick={onClose} className="grid h-11 w-11 place-items-center rounded-xl text-2xl text-muted hover:bg-slate-100 hover:text-text" aria-label="Close intelligence agent">×</button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-3" aria-live="polite">
        {messages.map((message, index) => (
          <div key={index} className={`rounded-xl border p-3 text-sm ${message.role === "user" ? "ml-8 border-blue-200 bg-blue-50" : "mr-4 border-slate-200 bg-slate-50"}`}>
            <pre className="whitespace-pre-wrap font-sans text-text">{message.text}</pre>
            {message.brief?.brief_text && <button onClick={() => exportPDF(message.brief, message.district)} className="mt-3 min-h-11 rounded-lg bg-accent px-3 text-xs font-semibold text-white">Export PDF brief</button>}
            {message.mode && <div className="mt-1 text-[11px] text-muted">Source mode: {message.mode}</div>}
          </div>
        ))}
        {busy && <div className="text-sm text-muted">Analyzing current evidence…</div>}
      </div>

      <div className="border-t border-slate-200 p-3">
        <div className="mb-2 flex flex-wrap gap-2">
          {["Top risk zones now", `Brief for ${context?.district || "Coimbatore"}`].map((suggestion) => <button key={suggestion} onClick={() => send(suggestion)} className="min-h-11 rounded-lg border border-slate-200 bg-white px-2 text-xs text-muted hover:bg-slate-50">{suggestion}</button>)}
        </div>
        <div className="flex gap-2">
          <input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => event.key === "Enter" && send()} placeholder="Ask the intelligence agent…" aria-label="Message VIZHI intelligence agent" className="min-h-11 flex-1 rounded-xl border border-slate-300 bg-white px-3 text-sm focus:border-accent" />
          <button onClick={() => send()} disabled={busy} className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold text-white disabled:opacity-50">Send</button>
        </div>
      </div>
    </div>
  );
}
