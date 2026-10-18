import React from 'react';

interface WaveformProps {
  large?: boolean;
}

export function Waveform({ large = false }: WaveformProps) {
  return (
    <svg
      className={`waveform ${large ? 'waveform-large' : ''}`}
      viewBox="0 0 820 220"
      preserveAspectRatio="none"
      role="img"
      aria-label="Illustrative heart rate waveform"
    >
      <defs>
        <linearGradient id="wave" x1="0" x2="1">
          <stop stopColor="#35e6d3" />
          <stop offset="0.5" stopColor="#8bffd1" />
          <stop offset="1" stopColor="#7dd3fc" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        className="wave-shadow"
        d="M0 126 C45 125 67 124 98 126 L126 127 142 116 154 132 172 124 196 126 216 125 235 76 251 172 267 28 290 154 307 111 325 125 C370 127 397 124 432 125 L457 126 470 112 486 133 503 124 532 126 551 124 566 79 584 169 601 36 621 155 638 109 657 125 C706 126 752 123 820 126"
      />
      <path
        className="wave-line"
        d="M0 126 C45 125 67 124 98 126 L126 127 142 116 154 132 172 124 196 126 216 125 235 76 251 172 267 28 290 154 307 111 325 125 C370 127 397 124 432 125 L457 126 470 112 486 133 503 124 532 126 551 124 566 79 584 169 601 36 621 155 638 109 657 125 C706 126 752 123 820 126"
      />
      <circle className="wave-dot" cx="601" cy="36" r="5" />
    </svg>
  );
}
