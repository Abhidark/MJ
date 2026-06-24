/**
 * GestureControlCard — Webcam gesture control widget with toggle.
 */
import { useState, useRef, useEffect } from 'react';

export default function GestureControlCard() {
  const [active, setActive] = useState(false);
  const [gesture, setGesture] = useState('IDLE');
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const toggleGesture = async () => {
    if (active) {
      // Stop
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      }
      setActive(false);
      setGesture('IDLE');
    } else {
      // Start webcam
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 160, height: 120 } });
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setActive(true);
        setGesture('DETECTING...');
      } catch {
        setGesture('CAM ERROR');
      }
    }
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    };
  }, []);

  return (
    <div className="gesture-card">
      <div className="gesture-header">
        <span>Gesture Control</span>
        <button
          className={`gesture-toggle-btn${active ? ' active' : ''}`}
          onClick={toggleGesture}
          title="Toggle gesture control"
        >
          ✋
        </button>
      </div>
      {active && (
        <div className="gesture-preview">
          <video ref={videoRef} autoPlay playsInline muted className="gesture-video" />
          <div className="gesture-label">GESTURE: {gesture}</div>
          <div className={`gesture-dot${active ? ' active' : ''}`} />
        </div>
      )}
      {!active && (
        <div className="gesture-inactive">
          <span className="gesture-inactive-icon">✋</span>
          <span>Click to enable gesture control</span>
        </div>
      )}
    </div>
  );
}
