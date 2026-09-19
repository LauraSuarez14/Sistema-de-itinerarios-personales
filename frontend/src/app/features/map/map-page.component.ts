import { AfterViewInit, Component, ElementRef, ViewChild, inject, signal } from '@angular/core';
import { trigger, transition, style, animate } from '@angular/animations';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ApiService } from '../../core/services/api.service';
import { parseApiError } from '../../core/utils/api-error.util';
import { PlotlyPoint } from '../../core/models/airport.model';
import { parseAirportLabel } from '../../core/utils/airport-label.util';
import { StatusBoxComponent } from '../../shared/status-box/status-box.component';

declare const Plotly: any;

@Component({
  selector: 'app-map-page',
  standalone: true,
  imports: [TranslateModule, StatusBoxComponent],
  templateUrl: './map-page.component.html',
  styleUrl: './map-page.component.css',
  animations: [
    trigger('panelUpdate', [
      transition('* => *', [
        style({ opacity: 0, transform: 'translateY(6px)' }),
        animate('200ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
      ]),
    ]),
  ],
})
export class MapPageComponent implements AfterViewInit {
  private readonly api = inject(ApiService);
  private readonly translate = inject(TranslateService);

  @ViewChild('mapDiv') private readonly mapDivRef!: ElementRef<HTMLDivElement>;

  readonly errorMessage = signal<string | null>(null);
  readonly loading = signal(false);
  readonly selected = signal<PlotlyPoint | null>(null);

  ngAfterViewInit(): void {
    this.load();
  }

  load(): void {
    this.errorMessage.set(null);
    this.loading.set(true);

    this.api.getAirportsPlotly(300).subscribe({
      next: (points) => {
        this.loading.set(false);
        this.renderChart(points);
      },
      error: (err) => {
        this.loading.set(false);
        const info = parseApiError(err);
        this.errorMessage.set(
          info.isNetworkError
            ? this.translate.instant('errors.network', { base: this.api.apiBase, detail: info.detail })
            : this.translate.instant('errors.http', info)
        );
      },
    });
  }

  parsedSelected() {
    const point = this.selected();
    return point ? { ...parseAirportLabel(point.label), lat: point.lat, lon: point.lon } : null;
  }

  private renderChart(points: PlotlyPoint[]): void {
    const trace = {
      type: 'scattergeo',
      mode: 'markers',
      lat: points.map((p) => p.lat),
      lon: points.map((p) => p.lon),
      // El tooltip flotante nativo de Plotly se apaga; el detalle se
      // muestra en el recuadro lateral vía los eventos de abajo.
      hoverinfo: 'none',
      customdata: points,
      marker: {
        size: 9,
        color: '#10b981',
        line: { color: '#7c3aed', width: 1.5 },
        opacity: 0.9,
      },
    };

    const layout = {
      geo: {
        scope: 'south america',
        center: { lat: 4.5709, lon: -74.2973 },
        projection: { type: 'mercator' },
        lataxis: { range: [-5, 14] },
        lonaxis: { range: [-82, -66] },
        showland: true,
        landcolor: this.cssVar('--geo-land'),
        showcountries: true,
        countrycolor: this.cssVar('--geo-country'),
        showocean: true,
        oceancolor: this.cssVar('--geo-ocean'),
        bgcolor: 'rgba(0,0,0,0)',
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      margin: { l: 0, r: 0, t: 10, b: 0 },
    };

    Plotly.newPlot(this.mapDivRef.nativeElement, [trace], layout, { responsive: true }).then((gd: any) => {
      const onSignal = (event: any) => {
        const point = event.points?.[0]?.customdata;
        if (point) this.selected.set(point);
      };
      gd.on('plotly_hover', onSignal);
      gd.on('plotly_click', onSignal);
    });
  }

  private cssVar(name: string): string {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#000000';
  }
}
