import { HttpErrorResponse } from '@angular/common/http';

export interface ApiErrorInfo {
  isNetworkError: boolean;
  status: number;
  title: string;
  detail: string;
}

/** Interpreta cualquier error HTTP, priorizando el formato
 * application/problem+json (RFC 7807) que usan todos los servicios backend. */
export function parseApiError(err: HttpErrorResponse): ApiErrorInfo {
  if (err.status === 0) {
    return { isNetworkError: true, status: 0, title: 'Network', detail: err.message };
  }

  const body = err.error;
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    return { isNetworkError: false, status: err.status, title: body.title || 'Error', detail };
  }

  return { isNetworkError: false, status: err.status, title: 'Error', detail: err.message };
}
