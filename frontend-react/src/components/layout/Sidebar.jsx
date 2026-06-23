export default function Sidebar() {
  return (
    <aside className="w-64 h-full bg-[var(--bg-panel)] border-r border-[var(--border)] flex flex-col">
      <div className="p-4 border-b border-[var(--border)]">
        <h2 className="text-sm font-semibold text-[var(--cyan)]">MJ Assistant</h2>
      </div>
      <nav className="flex-1 p-3 space-y-1">
      </nav>
    </aside>
  );
}
