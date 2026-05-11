import { useEffect, useRef, useState } from 'react';

export function useIsTouchDevice() {
  const [isTouch, setIsTouch] = useState(
    () => !window.matchMedia('(hover: hover) and (pointer: fine)').matches
  );
  useEffect(() => {
    const mq = window.matchMedia('(hover: hover) and (pointer: fine)');
    const handler = (e) => setIsTouch(!e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return isTouch;
}

const registry = new Set();

function closeOthers(excludeId) {
  registry.forEach(entry => { if (entry.id !== excludeId) entry.close(); });
}

export function useExpandable(id, containerRef) {
  const [isOpen, setIsOpen] = useState(false);
  const ownRef = useRef(null);

  useEffect(() => {
    const entry = { id, close: () => setIsOpen(false) };
    registry.add(entry);
    return () => registry.delete(entry);
  }, [id]);

  useEffect(() => {
    if (!isOpen) return;
    const checkRef = containerRef ?? ownRef;
    function onMouseDown(e) {
      if (checkRef.current && !checkRef.current.contains(e.target)) setIsOpen(false);
    }
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [isOpen, containerRef]);

  function toggle() {
    setIsOpen(prev => {
      if (!prev) closeOthers(id);
      return !prev;
    });
  }

  return [isOpen, toggle, ownRef];
}

export function useTooltip(id) {
  const [tooltip, setTooltip] = useState(null);
  const ref = useRef(null);

  useEffect(() => {
    const entry = { id, close: () => setTooltip(null) };
    registry.add(entry);
    return () => registry.delete(entry);
  }, [id]);

  useEffect(() => {
    if (!tooltip) return;
    function onMouseDown(e) {
      if (ref.current && !ref.current.contains(e.target)) setTooltip(null);
    }
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [tooltip]);

  function open(value) {
    if (value != null) closeOthers(id);
    setTooltip(value);
  }

  return [tooltip, open, ref];
}
