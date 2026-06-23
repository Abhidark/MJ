/**
 * DashboardCard — reusable card wrapper with title, icon, expand/collapse, drag handle
 */
import { useState } from 'react';

export default function DashboardCard({
  id,
  title,
  icon,
  children,
  style,
  className = '',
  editing = false,
  dragging = false,
  onDragStart,
  onDragOver,
  onDragEnd,
  collapsible = true,
  defaultExpanded = true,
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div
      className={`dash-card${dragging ? ' dragging' : ''}${className ? ' ' + className : ''}`}
      style={style}
      data-card-id={id}
      onDragOver={(e) => { e.preventDefault(); onDragOver?.(id); }}
      onDrop={(e) => { e.preventDefault(); onDragEnd?.(); }}
    >
      {/* Drag handle (edit mode only) */}
      {editing && (
        <div
          className="card-drag-handle"
          draggable
          onDragStart={() => onDragStart?.(id)}
          onDragEnd={() => onDragEnd?.()}
        />
      )}

      {/* Title bar */}
      {title && (
        <div
          className={`dash-card-title${expanded ? ' expanded' : ''}`}
          onClick={() => collapsible && setExpanded(p => !p)}
        >
          {icon && <span className="dct-icon">{icon}</span>}
          <span>{title}</span>
          {collapsible && <span className="expand-arrow">&#9660;</span>}
        </div>
      )}

      {/* Content */}
      {expanded && <div className="dash-card-body">{children}</div>}
    </div>
  );
}
