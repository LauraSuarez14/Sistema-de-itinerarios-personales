import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { parseApiError } from '../../core/utils/api-error.util';
import { StatusBoxComponent } from '../../shared/status-box/status-box.component';

@Component({
  selector: 'app-session-bar',
  standalone: true,
  imports: [ReactiveFormsModule, TranslateModule, StatusBoxComponent],
  templateUrl: './session-bar.component.html',
  styleUrl: './session-bar.component.css',
})
export class SessionBarComponent {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiService);
  private readonly translate = inject(TranslateService);
  readonly auth = inject(AuthService);

  readonly form = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  readonly errorMessage = signal<string | null>(null);
  readonly submitting = signal(false);

  submit(): void {
    if (this.form.invalid) return;
    this.submitting.set(true);
    this.errorMessage.set(null);

    const { username, password } = this.form.getRawValue();
    this.api.login(username, password).subscribe({
      next: (res) => {
        this.auth.setSession(username, res.access_token);
        this.submitting.set(false);
        this.form.reset();
      },
      error: (err) => {
        const info = parseApiError(err);
        this.errorMessage.set(
          info.isNetworkError
            ? this.translate.instant('errors.network', { base: this.api.apiBase, detail: info.detail })
            : this.translate.instant('errors.http', info)
        );
        this.submitting.set(false);
      },
    });
  }

  logout(): void {
    this.auth.clearSession();
  }
}
