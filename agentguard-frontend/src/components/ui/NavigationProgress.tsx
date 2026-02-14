'use client';

import { useEffect, useState, useRef } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Thin progress bar at the top of the viewport during page navigation.
 * Mimics the nprogress / YouTube loading bar pattern.
 */
export function NavigationProgress() {
  const pathname = usePathname();
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevPathRef = useRef(pathname);

  useEffect(() => {
    // Only show on actual navigation (path change)
    if (pathname === prevPathRef.current) return;
    prevPathRef.current = pathname;

    // Start progress
    setProgress(0);
    setVisible(true);

    // Animate progress
    let current = 0;
    timerRef.current = setInterval(() => {
      current += Math.random() * 15 + 5;
      if (current >= 90) {
        current = 90;
        if (timerRef.current) clearInterval(timerRef.current);
      }
      setProgress(current);
    }, 100);

    // Complete after a short delay (simulates load completion)
    const completeTimer = setTimeout(() => {
      if (timerRef.current) clearInterval(timerRef.current);
      setProgress(100);
      setTimeout(() => setVisible(false), 200);
    }, 300);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      clearTimeout(completeTimer);
    };
  }, [pathname]);

  if (!visible) return null;

  return (
    <div className="fixed left-0 right-0 top-0 z-[100] h-0.5">
      <div
        className="h-full bg-primary transition-all duration-200 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
