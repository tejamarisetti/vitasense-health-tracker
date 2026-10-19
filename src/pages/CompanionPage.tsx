import React, { useState, useEffect } from 'react';
import { Icon } from '../components/Icons';
import { Orb } from '../components/Orb';

interface DataCard {
  title: string;
  value: string;
  badge?: string;
  description?: string;
}

interface Message {
  sender: 'ai' | 'user';
  text: string;
  intent?: string;
  show_cards?: boolean;
  cards?: DataCard[];
  engine?: 'llm' | 'rule_fallback';
  fallback_reason?: string;
}

export function CompanionPage() {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [engineInfo, setEngineInfo] = useState<{
    engine: 'llm' | 'rule_fallback';
    reason?: string;
  }>({ engine: 'rule_fallback', reason: 'checking...' });

  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'ai',
      text: "Hi! How can I help you? I can answer questions about your heart rate readings, trust scores, or signal validation from PPG-DaLiA replay recordings.",
      intent: 'greeting',
      show_cards: false,
      cards: [],
      engine: 'rule_fallback',
    },
  ]);

  useEffect(() => {
    fetch('/api/assistant/health')
      .then((r) => r.json())
      .then((data) => {
        if (data.status === 'ok') {
          setEngineInfo({ engine: 'llm' });
        } else {
          setEngineInfo({
            engine: 'rule_fallback',
            reason: data.category || 'fallback',
          });
        }
      })
      .catch(() => {
        setEngineInfo({ engine: 'rule_fallback', reason: 'offline' });
      });
  }, []);

  // Current session context passed to POST /api/assistant
  const activeContext = {
    latest_reading: { hr: 74.2, unit: 'bpm' },
    timestamp: '2026-10-19T10:30:00Z',
    source: 'PPG-DaLiA S1 (REPLAY: public dataset, not live)',
    trust_score: 0.94,
    flags: ['motion_detected'],
    alerts: [],
  };

  const quickPrompts = [
    'Hi',
    'What is my latest heart rate?',
    'What is my trust score?',
    'Show me my data cards',
    'Do I have tachycardia?',
    'What is the capital of France?',
  ];

  const handleSend = async (userText: string) => {
    if (!userText.trim() || isLoading) return;

    const newMessages: Message[] = [
      ...messages,
      { sender: 'user', text: userText },
    ];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          context: activeContext,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      if (data.engine) {
        setEngineInfo({
          engine: data.engine,
          reason: data.fallback_reason,
        });
      }
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: data.reply,
          intent: data.intent,
          show_cards: Boolean(data.show_cards),
          cards: data.cards || [],
          engine: data.engine,
          fallback_reason: data.fallback_reason,
        },
      ]);
    } catch (err) {
      console.error('Assistant API request failed:', err);
      // Fallback response with strict anti-card compliance
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: "I'm having trouble connecting to the backend right now. Please verify that the API server is running on port 8000.",
          intent: 'error',
          show_cards: false,
          cards: [],
          engine: 'rule_fallback',
          fallback_reason: 'connection error',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="companion-page">
      <div className="companion-intro">
        <Orb small />
        <span className="app-kicker">VITASENSE AI COMPANION</span>
        <h1>
          Let's understand <em>your health data.</em>
        </h1>
        <p>
          Ask about your measurements, trust scores, and data quality.
          Telemetry is strictly educational replay; clinical diagnoses are never provided.
        </p>
      </div>

      {/* Replay Notice with unobtrusive Engine Indicator */}
      <div className="assistant-context-banner">
        <div className="banner-left-info">
          <Icon name="shield" />
          <span>
            Active Context: <strong>PPG-DaLiA S1</strong> · Replay Mode (public dataset, not live) · Heart Rate: 74.2 bpm · Trust: 94%
          </span>
        </div>
        <div
          className={`assistant-engine-pill ${engineInfo.engine === 'llm' ? 'is-llm' : 'is-fallback'}`}
          title={engineInfo.reason ? `Fallback reason: ${engineInfo.reason}` : 'Active Engine: LLM'}
        >
          <span className="engine-pulse-dot" />
          <span className="engine-label">
            {engineInfo.engine === 'llm'
              ? 'LLM'
              : `Rule Fallback${engineInfo.reason ? ` (${engineInfo.reason})` : ''}`}
          </span>
        </div>
      </div>

      <div className="chat-space">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`chat-message ${
              m.sender === 'ai' ? 'ai-message' : 'user-message'
            }`}
          >
            {m.sender === 'ai' && (
              <span className="chat-avatar">
                <Icon name="sparkles" />
              </span>
            )}

            <div>
              <p>{m.text}</p>

              {/* Cards render ONLY when explicitly requested by user */}
              {m.show_cards && m.cards && m.cards.length > 0 && (
                <div className="assistant-cards-grid">
                  {m.cards.map((c, cIdx) => (
                    <div key={cIdx} className="assistant-metric-card">
                      <div className="card-top">
                        <small>{c.title}</small>
                        {c.badge && <span className="card-badge">{c.badge}</span>}
                      </div>
                      <strong>{c.value}</strong>
                      {c.description && <small className="card-desc">{c.description}</small>}
                    </div>
                  ))}
                </div>
              )}

              {m.sender === 'ai' && (
                <small className="ai-disclaimer">
                  <Icon name="shield" />
                  <span>
                    {m.intent === 'diagnosis_refusal'
                      ? 'Clinical refusal · VitaSense does not provide medical diagnoses'
                      : 'Replay data · Educational & research tool · Not medical advice'}
                  </span>
                  {m.engine && (
                    <span className="message-engine-tag">
                      · {m.engine === 'llm' ? 'llm' : `rule_fallback${m.fallback_reason ? ` (${m.fallback_reason})` : ''}`}
                    </span>
                  )}
                </small>
              )}
            </div>

            {m.sender === 'user' && <span className="avatar">AM</span>}
          </div>
        ))}

        {isLoading && (
          <div className="chat-message ai-message">
            <span className="chat-avatar">
              <Icon name="sparkles" />
            </span>
            <div className="loading-dots">
              <span>Thinking…</span>
            </div>
          </div>
        )}
      </div>

      {/* Quick Prompts */}
      <div className="prompt-row">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => handleSend(prompt)}
            type="button"
            disabled={isLoading}
          >
            {prompt}
            <Icon name="arrow" />
          </button>
        ))}
      </div>

      {/* Message Composer */}
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
      >
        <button type="button" aria-label="Add attachment">
          ＋
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your heart rate, trust score, or signal quality…"
          disabled={isLoading}
        />
        <span>AI companion for research telemetry. Verify important data.</span>
        <button className="send" type="submit" aria-label="Send" disabled={isLoading || !input.trim()}>
          <Icon name="send" />
        </button>
      </form>
    </div>
  );
}
