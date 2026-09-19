import { Component, effect, inject, signal, untracked } from '@angular/core';
import { animate, query, stagger, style, transition, trigger } from '@angular/animations';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { parseApiError } from '../../core/utils/api-error.util';
import { Itinerary } from '../../core/models/itinerary.model';
import { StatusBoxComponent } from '../../shared/status-box/status-box.component';
import { CreateItineraryFormComponent } from './create-itinerary-form.component';

const PAGE_SIZE = 5;

@Component({
  selector: 'app-itineraries-page',
  standalone: true,
  imports: [TranslateModule, StatusBoxComponent, CreateItineraryFormComponent],
  templateUrl: './itineraries-page.component.html',
  styleUrl: './itineraries-page.component.css',
  animations: [
    // Solo opacidad (sin transform): las filas de una tabla no manejan bien
    // translate/transform por su layout interno (tr/td), así que se anima
    // exclusivamente el fundido para evitar saltos visuales.
    trigger('listStagger', [
      transition('* => *', [
        query(':enter', [style({ opacity: 0 }), stagger(50, animate('220ms ease-out', style({ opacity: 1 })))], { optional: true }),
      ]),
    ]),
  ],
})
export class ItinerariesPageComponent {
  private readonly api = inject(ApiService);
  private readonly translate = inject(TranslateService);
  readonly auth = inject(AuthService);

  readonly items = signal<Itinerary[]>([]);
  readonly total = signal(0);
  readonly currentPage = signal(1);
  readonly errorMessage = signal<string | null>(null);
  readonly pageSize = PAGE_SIZE;

  constructor() {
    // Recarga automáticamente al iniciar/cerrar sesión (no solo al construir
    // el componente), ya que el login vive en <app-session-bar>, fuera de
    // esta vista.
    effect(() => {
      const loggedIn = this.auth.isLoggedIn();
      // `load()` lee otras signals (currentPage); sin `untracked`, ese
      // acceso las convertiría también en dependencias de este efecto y
      // dispararía una recarga duplicada cada vez que cambia la página.
      untracked(() => {
        if (loggedIn) {
          this.currentPage.set(1);
          this.load();
        } else {
          this.items.set([]);
          this.total.set(0);
        }
      });
    });
  }

  load(): void {
    this.errorMessage.set(null);

    if (!this.auth.isLoggedIn()) {
      this.items.set([]);
      return;
    }

    this.api.listItineraries(this.currentPage(), this.pageSize).subscribe({
      next: (data) => {
        this.items.set(data.items);
        this.total.set(data.total);
      },
      error: (err) => {
        const info = parseApiError(err);
        this.errorMessage.set(
          info.isNetworkError
            ? this.translate.instant('errors.network', { base: this.api.apiBase, detail: info.detail })
            : this.translate.instant('errors.http', info)
        );
      },
    });
  }

  onCreated(): void {
    this.currentPage.set(1);
    this.load();
  }

  deleteItinerary(id: string): void {
    this.errorMessage.set(null);
    this.api.deleteItinerary(id).subscribe({
      next: () => this.load(),
      error: (err) => {
        const info = parseApiError(err);
        this.errorMessage.set(
          info.isNetworkError
            ? this.translate.instant('errors.network', { base: this.api.apiBase, detail: info.detail })
            : this.translate.instant('errors.http', info)
        );
      },
    });
  }

  prevPage(): void {
    if (this.currentPage() <= 1) return;
    this.currentPage.set(this.currentPage() - 1);
    this.load();
  }

  nextPage(): void {
    this.currentPage.set(this.currentPage() + 1);
    this.load();
  }
}
