import { Injectable, effect, signal } from '@angular/core';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'itinerarios-theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly theme = signal<Theme>(this.loadInitial());

  constructor() {
    // Refleja la signal en el DOM (atributo leído por las variables CSS de
    // tema en styles.css) y la persiste, cada vez que cambia.
    effect(() => {
      const value = this.theme();
      document.documentElement.setAttribute('data-theme', value);
      try {
        localStorage.setItem(STORAGE_KEY, value);
      } catch {
        // Almacenamiento no disponible (modo privado, etc.): no es crítico.
      }
    });
  }

  toggle(): void {
    this.theme.set(this.theme() === 'dark' ? 'light' : 'dark');
  }

  private loadInitial(): Theme {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') return stored;
    } catch {
      // Ignorado: sin localStorage, se cae al valor de prefers-color-scheme.
    }
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
}
