import { lazy } from 'react';
import type { ComponentType } from 'react';

/**
 * Custom lazy loader with artificial timeout simulation if needed
 * to avoid flashing layout states and split Vite chunks beautifully.
 */
export function lazyLoad<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>
) {
  return lazy(importFn);
}

/**
 * GPU-friendly high-frequency function debouncer utilizing requestAnimationFrame.
 * Essential for rendering canvas molecules and virtual list scrolls smoothly at 60fps.
 */
export function rafThrottle<T extends (...args: any[]) => any>(fn: T): (...args: Parameters<T>) => void {
  let active = false;
  let savedArgs: Parameters<T> | null = null;

  return function throttled(...args: Parameters<T>) {
    if (active) {
      savedArgs = args;
      return;
    }

    active = true;
    fn(...args);

    requestAnimationFrame(() => {
      active = false;
      if (savedArgs) {
        throttled(...savedArgs);
        savedArgs = null;
      }
    });
  };
}

/**
 * Dynamic search input debouncer to avoid triggering component rerenders on every keystroke.
 */
export function debounce<T extends (...args: any[]) => void>(fn: T, delay: number = 300) {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  
  return function(...args: Parameters<T>) {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      fn(...args);
    }, delay);
  };
}
