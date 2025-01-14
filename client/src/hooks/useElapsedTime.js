import { useState, useEffect } from 'react';

export const useElapsedTime = (step, initialStartTime) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState(null);

  useEffect(() => {
    if ((step.status === "in_progress" || step.status === "completed") && !startTime) {
      // Convert ISO string to timestamp if needed
      const timestamp = typeof initialStartTime === 'string' 
        ? new Date(initialStartTime).getTime() 
        : initialStartTime || Date.now();
      setStartTime(timestamp);
    }
  }, [step.status, initialStartTime, startTime]);

  useEffect(() => {
    let interval;
    if (startTime && step.status === "in_progress") {
      interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
    } else if (step.status === "completed" && startTime && elapsedTime === 0) {
      // Update once on completion
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [step.status, startTime, elapsedTime]);

  return { elapsedTime, startTime };
};
