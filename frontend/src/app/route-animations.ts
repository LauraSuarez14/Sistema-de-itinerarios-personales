import { animate, group, query, style, transition, trigger } from '@angular/animations';

/** Transición de fundido+deslizamiento entre vistas ruteadas (mapa <->
 * itinerarios), aplicada sobre el contenedor que envuelve <router-outlet>. */
export const routeAnimations = trigger('routeAnimations', [
  transition('* <=> *', [
    query(':enter, :leave', style({ position: 'absolute', width: '100%' }), { optional: true }),
    group([
      query(
        ':leave',
        [style({ opacity: 1, transform: 'translateY(0)' }), animate('150ms ease-in', style({ opacity: 0, transform: 'translateY(-6px)' }))],
        { optional: true }
      ),
      query(
        ':enter',
        [style({ opacity: 0, transform: 'translateY(6px)' }), animate('220ms 80ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))],
        { optional: true }
      ),
    ]),
  ]),
]);
