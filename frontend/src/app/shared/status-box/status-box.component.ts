import { Component, Input } from '@angular/core';

export type StatusKind = 'info' | 'success' | 'error';

@Component({
  selector: 'app-status-box',
  standalone: true,
  templateUrl: './status-box.component.html',
  styleUrl: './status-box.component.css',
})
export class StatusBoxComponent {
  @Input() message: string | null = null;
  @Input() kind: StatusKind = 'info';
}
