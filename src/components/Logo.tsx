import React from 'react';

interface LogoProps {
  compact?: boolean;
}

export function Logo({ compact = false }: LogoProps) {
  return (
    <div className="logo">
      <span className="logo-mark">
        <i />
        <i />
        <i />
      </span>
      {!compact && (
        <span>
          VitaSense <b>AI</b>
        </span>
      )}
    </div>
  );
}
