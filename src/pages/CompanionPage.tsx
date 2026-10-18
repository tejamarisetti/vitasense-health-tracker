import React, { useState } from 'react';
import { Icon } from '../components/Icons';
import { Orb } from '../components/Orb';

interface Message {
  sender: 'ai' | 'user';
  text: string;
  context?: { icon: 'pulse' | 'drop' | 'shield'; text: string }[];
}

export function CompanionPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'ai',
      text: 'Good morning, Alex. Your latest demo readings are available. I can help you understand what changed, review the supporting data, or check signal quality.',
      context: [
        { icon: 'pulse', text: '72 BPM' },
        { icon: 'drop', text: '97% estimated SpO₂' },
        { icon: 'shield', text: '96% quality' }
      ]
    }
  ]);

  const quickPrompts = [
    'Explain my latest trend',
    'What changed this week?',
    'Review my measurement history',
    'Explain my data-quality report'
  ];

  const handleSend = (userText: string) => {
    if (!userText.trim()) return;

    const newMessages: Message[] = [
      ...messages,
      { sender: 'user', text: userText }
    ];
    setMessages(newMessages);
    setInput('');

    // Generate intelligent contextual response
    setTimeout(() => {
      let aiReply = '';
      let replyContext: { icon: 'pulse' | 'drop' | 'shield'; text: string }[] = [];

      if (userText.includes('trend') || userText.includes('week')) {
        aiReply =
          'Over the past 7 days, your resting heart rate maintained a stable average of 71 BPM (baseline 70–73 BPM). A brief elevation to 86 BPM occurred on Thursday at 2:40 PM, which coincided with physical activity. Signal quality was verified at 96% throughout.';
        replyContext = [
          { icon: 'pulse', text: '71 BPM 7-day avg' },
          { icon: 'shield', text: 'Verified baseline' }
        ];
      } else if (userText.includes('data-quality') || userText.includes('quality')) {
        aiReply =
          'Your overall signal integrity score is 96% (High integrity). Software validation flagged 2 minor motion artifacts on today’s 10:37 AM reading during brisk movement. Out-of-range sensor values were zero.';
        replyContext = [
          { icon: 'shield', text: '96% Integrity' },
          { icon: 'pulse', text: '2 motion flags' }
        ];
      } else if (userText.includes('history')) {
        aiReply =
          'Your measurement history spans 12,400 signal points across 7 days. Completeness is 98.4%, and SpO₂ saturation has remained optimal between 96% and 98%.';
        replyContext = [
          { icon: 'drop', text: '97% SpO₂ avg' },
          { icon: 'shield', text: '98.4% completeness' }
        ];
      } else {
        aiReply = `I've analyzed your bio-signals related to "${userText}". All recorded telemetry aligns with your established personal baseline. No anomalous sustained tachycardia or hypoxia detected.`;
        replyContext = [
          { icon: 'pulse', text: 'Stable vitals' },
          { icon: 'shield', text: 'Context aware' }
        ];
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: aiReply,
          context: replyContext
        }
      ]);
    }, 450);
  };

  return (
    <div className="companion-page">
      <div className="companion-intro">
        <Orb small />
        <span className="app-kicker">VITASENSE COMPANION</span>
        <h1>
          Let's understand <em>your health.</em>
        </h1>
        <p>
          Ask about your measurements, trends, and data quality. I’ll show my
          sources and limitations.
        </p>
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
              {m.context && (
                <div className="message-context">
                  {m.context.map((c, cIdx) => (
                    <span key={cIdx}>
                      <Icon name={c.icon} /> {c.text}
                    </span>
                  ))}
                </div>
              )}
              {m.sender === 'ai' && (
                <small>
                  <Icon name="shield" /> Demo measurements · Not medical advice
                </small>
              )}
            </div>

            {m.sender === 'user' && <span className="avatar">AM</span>}
          </div>
        ))}
      </div>

      {/* Quick Prompts */}
      <div className="prompt-row">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => handleSend(prompt)}
            type="button"
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
          placeholder="Ask VitaSense about your health data…"
        />
        <span>AI can make mistakes. Verify important information.</span>
        <button className="send" type="submit" aria-label="Send">
          <Icon name="send" />
        </button>
      </form>
    </div>
  );
}
