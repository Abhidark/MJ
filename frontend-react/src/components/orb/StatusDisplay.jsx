/**
 * StatusDisplay — orb state indicator + mic status + voice wave
 */
export default function StatusDisplay({ orbState, micStatus, waveState, listening, onMicToggle }) {
  const stateConfig = {
    idle:      { dot: 'idle',   text: 'IDLE' },
    listening: { dot: 'listen', text: 'LISTENING' },
    thinking:  { dot: 'think',  text: 'PROCESSING' },
    speaking:  { dot: 'speak',  text: 'SPEAKING' },
    error:     { dot: 'err',    text: 'ERROR' },
  };

  const cfg = stateConfig[orbState] || stateConfig.idle;

  return (
    <div className="orb-status-area">
      {/* State indicator */}
      <div className="orb-status">
        <span className={`state ${cfg.dot}`} />
        <span className="state-text">{cfg.text}</span>
      </div>

      {/* Mic status text */}
      <div className="orb-mic-status">{micStatus}</div>

      {/* Voice wave animation */}
      <div className={`voice-wave${waveState ? ` ${waveState}` : ''}`} />

      {/* Mic toggle button */}
      <button
        className={`orb-mic-btn${listening ? ' recording' : ''}`}
        onClick={onMicToggle}
        title={listening ? 'Stop listening' : 'Start listening'}
      >
        {listening ? '🎤 ON' : '🎤 OFF'}
      </button>
    </div>
  );
}
