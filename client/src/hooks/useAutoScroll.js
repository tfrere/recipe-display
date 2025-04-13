import { useState, useCallback, useRef, useEffect } from 'react';

export const useAutoScroll = (content) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const elementRef = useRef(null);

  const handleScroll = useCallback((e) => {
    const el = e.target;
    const isAtBottom = Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) < 1;
    setAutoScroll(isAtBottom);
  }, []);

  useEffect(() => {
    const el = elementRef.current;
    if (el && autoScroll) {
      // Use requestAnimationFrame to ensure the scroll happens after the content is rendered
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [content, autoScroll]); // Re-run when content or autoScroll changes

  return { autoScroll, elementRef, handleScroll };
};
