import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { routeAnimations } from './route-animations';
import { ThemeService } from './core/services/theme.service';
import { ApiService } from './core/services/api.service';
import { SessionBarComponent } from './features/session/session-bar.component';

const SUPPORTED_LANGS = ['es', 'en', 'fr'] as const;
type Lang = (typeof SUPPORTED_LANGS)[number];
const LANG_STORAGE_KEY = 'itinerarios-lang';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, TranslateModule, SessionBarComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
  animations: [routeAnimations],
})
export class AppComponent {
  readonly theme = inject(ThemeService);
  readonly translate = inject(TranslateService);
  readonly api = inject(ApiService);
  readonly languages = SUPPORTED_LANGS;

  constructor() {
    this.translate.addLangs([...SUPPORTED_LANGS]);
    this.translate.setDefaultLang('es');
    this.translate.onLangChange.subscribe(({ lang }) => {
      document.documentElement.lang = lang;
    });
    this.translate.use(this.loadInitialLang());
  }

  get currentLang(): string {
    return this.translate.currentLang || this.translate.defaultLang;
  }

  useLang(lang: string): void {
    this.translate.use(lang);
    try {
      localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch {
      // Sin localStorage disponible: el idioma simplemente no persiste.
    }
  }

  private loadInitialLang(): Lang {
    try {
      const stored = localStorage.getItem(LANG_STORAGE_KEY);
      if (stored && (SUPPORTED_LANGS as readonly string[]).includes(stored)) {
        return stored as Lang;
      }
    } catch {
      // Ignorado.
    }
    const browserLang = this.translate.getBrowserLang();
    return browserLang && (SUPPORTED_LANGS as readonly string[]).includes(browserLang) ? (browserLang as Lang) : 'es';
  }
}
