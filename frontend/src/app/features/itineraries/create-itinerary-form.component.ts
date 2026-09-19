import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { parseApiError } from '../../core/utils/api-error.util';
import { Itinerary } from '../../core/models/itinerary.model';
import { StatusBoxComponent } from '../../shared/status-box/status-box.component';

@Component({
  selector: 'app-create-itinerary-form',
  standalone: true,
  imports: [ReactiveFormsModule, TranslateModule, StatusBoxComponent],
  templateUrl: './create-itinerary-form.component.html',
  styleUrl: './create-itinerary-form.component.css',
})
export class CreateItineraryFormComponent {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiService);
  private readonly translate = inject(TranslateService);
  readonly auth = inject(AuthService);

  @Output() readonly created = new EventEmitter<Itinerary>();

  readonly form = this.fb.nonNullable.group({
    userName: ['', Validators.required],
    originId: [null as number | null, [Validators.required, Validators.min(1)]],
    destinationId: [null as number | null, [Validators.required, Validators.min(1)]],
    travelDate: ['', Validators.required],
    durationMinutes: [null as number | null, [Validators.required, Validators.min(1)]],
  });

  readonly submitting = signal(false);
  readonly resultMessage = signal<string | null>(null);
  readonly resultKind = signal<'success' | 'error'>('success');

  submit(): void {
    this.resultMessage.set(null);

    if (!this.auth.isLoggedIn()) {
      this.resultKind.set('error');
      this.resultMessage.set(this.translate.instant('itineraries.create.loginRequired'));
      return;
    }
    if (this.form.invalid) return;

    this.submitting.set(true);
    const value = this.form.getRawValue();
    this.api
      .createItinerary({
        user_name: value.userName,
        origin_airport_id: value.originId!,
        destination_airport_id: value.destinationId!,
        travel_date: value.travelDate,
        duration_minutes: value.durationMinutes!,
      })
      .subscribe({
        next: (itinerary) => {
          this.submitting.set(false);
          this.resultKind.set('success');
          this.resultMessage.set(
            this.translate.instant('itineraries.create.success', {
              id: itinerary.id,
              origin: itinerary.origin_airport.iata_code,
              destination: itinerary.destination_airport.iata_code,
              date: itinerary.travel_date,
            })
          );
          this.form.reset();
          this.created.emit(itinerary);
        },
        error: (err) => {
          this.submitting.set(false);
          this.resultKind.set('error');
          const info = parseApiError(err);
          this.resultMessage.set(
            info.isNetworkError
              ? this.translate.instant('errors.network', { base: this.api.apiBase, detail: info.detail })
              : this.translate.instant('errors.http', info)
          );
        },
      });
  }
}
