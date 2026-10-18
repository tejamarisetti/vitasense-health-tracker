import React from 'react';
import { Icon, IconName } from './Icons';

interface MetricCardProps {
  icon: IconName;
  label: string;
  value: string;
  unit: string;
  change: string;
  children?: React.ReactNode;
}

export function MetricCard({
  icon,
  label,
  value,
  unit,
  change,
  children
}: MetricCardProps) {
  return (
    <article className="mini-metric">
      <div className="metric-label">
        <span>
          <Icon name={icon} />
        </span>
        {label}
        <Icon name="more" />
      </div>
      <div className="mini-value">
        {value}
        <small>{unit}</small>
      </div>
      {children}
      <div className="metric-change">
        <b>↗ {change}</b> vs previous week
      </div>
    </article>
  );
}
