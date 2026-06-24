/**
 * DashboardCard — reusable card wrapper with title, icon, expand/collapse,
 * and full edit-mode controls: drag handle, resize handle, resize buttons,
 * color picker, position badge.
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
  dragHidden = false,
  pos,
  editActions,
  collapsible = true,
  defaultExpanded = true,
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const cardStyle = {
    ...style,
    ...(dragHidden ? { opacity: 0, pointerEvents: 'none' } : {}),
  };

  return (
    <div
      className={`dash-card${className ? ' ' + className : ''}`}
      style={cardStyle}
      data-card-id={id}
    >
      {/* Drag handle — edit mode only */}
      {editing && (
        <div
          className="card-drag-handle"
          onMouseDown={(e) => editActions?.onDragStart?.(id, e)}
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

      {/* Edit mode controls */}
      {editing && (
        <>
          {/* Per-card toolbar: color + resize buttons + reset */}
          <div className="card-edit-toolbar">
            <input
              type="color"
              defaultValue="#020c19"
              className="card-color-pick"
              title="Card BG Color"
              onInput={(e) => editActions?.onColorChange?.(id, e.target.value)}
            />
            <button title="Wider (+1 col)" className="card-wider"
              onClick={() => editActions?.onWider?.(id)}>→</button>
            <button title="Narrower (-1 col)" className="card-narrower"
              onClick={() => editActions?.onNarrower?.(id)}>←</button>
            <button title="Taller (+1 row)" className="card-taller"
              onClick={() => editActions?.onTaller?.(id)}>↓</button>
            <button title="Shorter (-1 row)" className="card-shorter"
              onClick={() => editActions?.onShorter?.(id)}>↑</button>
            <button title="Reset to default" className="card-reset-size"
              onClick={() => editActions?.onResetCard?.(id)}>↺</button>
          </div>

          {/* Corner resize handle (drag to resize) */}
          <div
            className="card-resize-handle"
            onMouseDown={(e) => editActions?.onResizeStart?.(id, e)}
          >⤡</div>

          {/* Grid position badge */}
          {pos && (
            <div className="grid-pos-badge">
              C{pos.col} R{pos.row} {pos.w}×{pos.h}
            </div>
          )}
        </>
      )}
    </div>
  );
}
