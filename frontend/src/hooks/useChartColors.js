import { useState, useEffect } from 'react';

function getCSSVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function readAll() {
  return {
    border:      getCSSVar('--border'),
    textMuted:   getCSSVar('--text-secondary'),
    accent:      getCSSVar('--accent'),
    readyGreen:  getCSSVar('--ready-green'),
    readyYellow: getCSSVar('--ready-yellow'),
    readyRed:    getCSSVar('--ready-red'),
    readyNone:   getCSSVar('--ready-none'),
    bgApp:       getCSSVar('--bg-app'),
    accentTint:  getCSSVar('--accent-tint-08'),
  };
}

export function useChartColors() {
  const [colors, setColors] = useState(readAll);

  useEffect(() => {
    const observer = new MutationObserver(() => setColors(readAll()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
    return () => observer.disconnect();
  }, []);

  return colors;
}
