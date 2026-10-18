import React from 'react';

interface OrbProps {
  small?: boolean;
}

export function Orb({ small = false }: OrbProps) {
  return (
    <div className={`orb-wrap ${small ? 'orb-small' : ''}`} aria-hidden="true">
      <div className="orbit orbit-a">
        <i />
        <i />
      </div>
      <div className="orbit orbit-b">
        <i />
      </div>
      <div className="orb">
        <div className="orb-mesh" />
        <div className="orb-core" />
      </div>
      <span className="node node-a" />
      <span className="node node-b" />
      <span className="node node-c" />
    </div>
  );
}
