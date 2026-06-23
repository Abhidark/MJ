/**
 * ProviderBadge — shows "GROQ" or "OLLAMA" badge on chat messages
 * Uses provider info already stored in message.modelBadge from SSE summary event
 */
export default function ProviderBadge({ provider }) {
  if (!provider) return null;

  const p = provider.toLowerCase();
  const isGroq = p.includes('groq');
  const label = isGroq ? 'GROQ' : 'OLLAMA';

  return (
    <span className={`provider-badge ${isGroq ? 'groq' : 'ollama'}`}>
      <span className="pb-dot" />
      {label}
    </span>
  );
}
