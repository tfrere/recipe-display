import { useState, useEffect, useRef, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════════════
   Notification sound (Web Audio API – no external file needed)
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Play a short two-tone chime.
 * Accepts an existing AudioContext so we can reuse one created on
 * user-gesture (required by iOS Safari).
 */
const playNotificationSound = (existingCtx) => {
  try {
    const ctx =
      existingCtx || new (window.AudioContext || window.webkitAudioContext)();

    const tones = [
      { freq: 587.33, delay: 0, duration: 0.15 }, // D5
      { freq: 880, delay: 0.18, duration: 0.3 }, // A5
    ];

    tones.forEach(({ freq, delay, duration }) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = freq;
      osc.type = "sine";
      const t = ctx.currentTime + delay;
      gain.gain.setValueAtTime(0.2, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
      osc.start(t);
      osc.stop(t + duration);
    });
  } catch {
    // Web Audio API not available
  }
};

/* ═══════════════════════════════════════════════════════════════════
   useTimer hook
   ═══════════════════════════════════════════════════════════════════ */

export const useTimer = (durationMinutes) => {
  const [totalSeconds, setTotalSeconds] = useState(
    Math.ceil(durationMinutes * 60)
  );
  const [remainingSeconds, setRemainingSeconds] = useState(
    Math.ceil(durationMinutes * 60)
  );
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef(null);
  const hasNotified = useRef(false);
  const audioCtxRef = useRef(null);

  // Reset when duration changes (step navigation)
  useEffect(() => {
    const next = Math.ceil(durationMinutes * 60);
    setTotalSeconds(next);
    setRemainingSeconds(next);
    setIsRunning(false);
    hasNotified.current = false;
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, [durationMinutes]);

  // Countdown tick
  useEffect(() => {
    if (isRunning && remainingSeconds > 0) {
      intervalRef.current = setInterval(() => {
        setRemainingSeconds((prev) => {
          if (prev <= 1) {
            clearInterval(intervalRef.current);
            setIsRunning(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isRunning, remainingSeconds]);

  // Sound notification on finish
  useEffect(() => {
    if (remainingSeconds === 0 && totalSeconds > 0 && !hasNotified.current) {
      hasNotified.current = true;
      playNotificationSound(audioCtxRef.current);
    }
  }, [remainingSeconds, totalSeconds]);

  // Create AudioContext on first user gesture (iOS Safari compat)
  const toggle = useCallback(() => {
    if (!audioCtxRef.current) {
      try {
        audioCtxRef.current = new (window.AudioContext ||
          window.webkitAudioContext)();
      } catch {
        // not available
      }
    }
    setIsRunning((p) => !p);
  }, []);

  const reset = useCallback(() => {
    setRemainingSeconds(totalSeconds);
    setIsRunning(false);
    hasNotified.current = false;
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, [totalSeconds]);

  const progress =
    totalSeconds > 0
      ? ((totalSeconds - remainingSeconds) / totalSeconds) * 100
      : 0;
  const isFinished = remainingSeconds === 0 && totalSeconds > 0;

  return {
    remainingSeconds,
    isRunning,
    toggle,
    reset,
    progress,
    isFinished,
    totalSeconds,
  };
};
