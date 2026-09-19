import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { AuthService } from '../services/auth.service';

/** Adjunta el JWT (si hay sesión) a toda petición al API Gateway. Los
 * endpoints públicos (p.ej. GET /api/v1/airports/plotly/points) simplemente
 * ignoran el header de más. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(AuthService).token();
  if (!token) return next(req);
  return next(req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }));
};
