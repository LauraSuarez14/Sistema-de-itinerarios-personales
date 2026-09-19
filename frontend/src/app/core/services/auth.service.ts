import { Injectable, computed, signal } from '@angular/core';

/** Estado de sesión: el JWT se guarda SOLO en memoria (una signal), nunca en
 * localStorage/sessionStorage. Decisión deliberada heredada del frontend
 * anterior: es un mock de autenticación académico sin usuarios reales, así
 * que no tiene sentido persistir el token entre recargas; además evita dejar
 * un JWT (aunque sea de demo) tirado en el almacenamiento del navegador. */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly _token = signal<string | null>(null);
  private readonly _username = signal<string | null>(null);

  readonly token = this._token.asReadonly();
  readonly username = this._username.asReadonly();
  readonly isLoggedIn = computed(() => this._token() !== null);

  setSession(username: string, token: string): void {
    this._username.set(username);
    this._token.set(token);
  }

  clearSession(): void {
    this._username.set(null);
    this._token.set(null);
  }
}
