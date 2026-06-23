/**
 * MainContent — wrapper that holds <Header /> + <content-row>
 * Receives isResizing to disable transitions during sidebar drag.
 */
export default function MainContent({ isResizing, children }) {
  return (
    <div className={`main-content${isResizing ? ' resizing' : ''}`}>
      {children}
    </div>
  );
}

/**
 * ContentRow — flex row for dashboard + right panels side by side.
 */
export function ContentRow({ children }) {
  return (
    <div className="content-row">
      {children}
    </div>
  );
}
