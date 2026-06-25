import { useState, useRef, useCallback, useEffect } from 'react';
import * as audioAnalyser from '@/services/audioAnalyser';

/**
 * useVoice — Web Speech API recognition + TTS via backend
 *
 * States: idle | listening | thinking | speaking | error
 * POST /speak → { audio_url } → play Audio element
 * Wake word patterns: "mj", "hey mj", "jarvis", etc.
 */

const WAKE_PATTERNS = [
  'mj', 'm.j', 'em j', 'hey mj', 'ok mj', 'emj', 'm j',
  'heyy mj', 'hey m j', 'hame j',
  'aye mj', 'yo mj', 'hello mj', 'hi mj',
  'ey mj', 'oye mj', 'bolo mj',
  'jarvis', 'friday', 'hey jarvis',
];

function stripWakeWord(text) {
  let result = text;
  for (const w of WAKE_PATTERNS) {
    result = result.replace(new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), '').trim();
  }
  return result;
}

export function useVoice({ onTranscript, onWake } = {}) {
  const [orbState, setOrbState] = useState('idle');      // idle|listening|thinking|speaking|error
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [micStatus, setMicStatus] = useState('Mic off');
  const [waveState, setWaveState] = useState(null);      // null|active|wake-active|processing
  const [supported, setSupported] = useState(true);

  const recognitionRef = useRef(null);
  const audioRef = useRef(null);
  const listeningRef = useRef(false);
  const firstWakeRef = useRef(false);
  const wakeTimeoutRef = useRef(null);

  // ─── Init Speech Recognition ───
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      setMicStatus('Speech not supported');
      return;
    }

    const recognition = new SpeechRecognition();
    const savedLang = localStorage.getItem('mj-voice-lang') || navigator.language || 'en-US';
    recognition.lang = savedLang;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 3;

    recognition.onresult = (e) => {
      let text = '';
      for (let i = 0; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
      }
      setTranscript(text);
      setMicStatus('\u{1F3A4} ' + text);

      const isFinal = e.results[e.results.length - 1].isFinal;
      if (!isFinal) return;

      const lower = text.toLowerCase().trim();
      const hasWake = WAKE_PATTERNS.some(w => lower.includes(w));

      if (hasWake) {
        const command = stripWakeWord(text);
        if (!firstWakeRef.current) {
          firstWakeRef.current = true;
          onWake?.();
        }
        if (command.length > 1) {
          setWaveState('processing');
          onTranscript?.(command);
          setTimeout(() => setWaveState('active'), 2000);
        } else {
          setMicStatus('MJ active! Speak your command...');
          setWaveState('wake-active');
          if (wakeTimeoutRef.current) clearTimeout(wakeTimeoutRef.current);
          wakeTimeoutRef.current = setTimeout(() => {
            setMicStatus('Say "Hey MJ" to activate...');
            setWaveState('active');
          }, 30000);
        }
      } else {
        const trimmed = text.trim();
        if (trimmed.length > 1) {
          setWaveState('processing');
          onTranscript?.(trimmed);
          setTimeout(() => setWaveState('active'), 2000);
        }
      }
    };

    recognition.onend = () => {
      if (listeningRef.current) {
        setTimeout(() => {
          if (listeningRef.current) {
            try { recognition.start(); } catch (_) {}
          }
        }, 200);
      }
    };

    recognition.onerror = (e) => {
      if (e.error === 'no-speech') {
        setMicStatus('Listening...');
      } else if (e.error === 'network') {
        setMicStatus('Network error - retrying...');
      } else if (e.error !== 'aborted') {
        setMicStatus('Mic error: ' + e.error);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      try { recognition.stop(); } catch (_) {}
      if (wakeTimeoutRef.current) clearTimeout(wakeTimeoutRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Start / Stop Listening ───
  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    setListening(true);
    listeningRef.current = true;
    setOrbState('listening');
    setMicStatus('Listening...');
    setWaveState('active');
    try { recognitionRef.current.start(); } catch (_) {}
  }, []);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    setListening(false);
    listeningRef.current = false;
    setOrbState('idle');
    setMicStatus('Mic off');
    setWaveState(null);
    setTranscript('');
    if (wakeTimeoutRef.current) clearTimeout(wakeTimeoutRef.current);
    try { recognitionRef.current.stop(); } catch (_) {}
  }, []);

  const toggleListening = useCallback(() => {
    if (listeningRef.current) stopListening();
    else startListening();
  }, [startListening, stopListening]);

  // ─── Text-to-Speech via backend ───
  const speak = useCallback(async (text, emotion = 'neutral') => {
    // Stop any current audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (!text || text.length < 2) {
      setOrbState(listeningRef.current ? 'listening' : 'idle');
      return;
    }

    try {
      const ctrl = new AbortController();
      const timeout = setTimeout(() => ctrl.abort(), 10000);

      const res = await fetch('/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, emotion }),
        signal: ctrl.signal,
      });
      clearTimeout(timeout);

      if (!res.ok) {
        setOrbState(listeningRef.current ? 'listening' : 'idle');
        return;
      }

      const data = await res.json();
      const audio = new Audio(data.audio_url);
      audioRef.current = audio;
      // Route the real voice stream into the shared FFT analyser so the
      // AudioSpectrum visualizer reacts to MJ's actual speech.
      try { audioAnalyser.attach(audio); } catch (_) {}
      setOrbState('speaking');

      audio.onended = () => {
        setOrbState(listeningRef.current ? 'listening' : 'idle');
        audioRef.current = null;
      };
      audio.onerror = () => {
        setOrbState(listeningRef.current ? 'listening' : 'idle');
        audioRef.current = null;
      };
      audio.play().catch(() => {
        setOrbState(listeningRef.current ? 'listening' : 'idle');
      });
    } catch (e) {
      console.log('TTS error:', e.message || e);
      setOrbState(listeningRef.current ? 'listening' : 'idle');
    }
  }, []);

  // ─── Stop speaking (mute) ───
  const stopSpeaking = useCallback(() => {
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
      setOrbState(listeningRef.current ? 'listening' : 'idle');
      return true; // was speaking
    }
    if (window.speechSynthesis?.speaking) {
      window.speechSynthesis.cancel();
      setOrbState(listeningRef.current ? 'listening' : 'idle');
      return true;
    }
    return false;
  }, []);

  // ─── Orb click handler ───
  const handleOrbClick = useCallback(() => {
    // If speaking, stop (mute)
    if (stopSpeaking()) return;
    // Otherwise toggle mic
    toggleListening();
  }, [stopSpeaking, toggleListening]);

  return {
    orbState,
    setOrbState,
    listening,
    transcript,
    micStatus,
    waveState,
    supported,
    startListening,
    stopListening,
    toggleListening,
    speak,
    stopSpeaking,
    handleOrbClick,
  };
}
