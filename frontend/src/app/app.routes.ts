import { Routes } from '@angular/router';
import { MapPageComponent } from './features/map/map-page.component';
import { ItinerariesPageComponent } from './features/itineraries/itineraries-page.component';

export const routes: Routes = [
  { path: '', redirectTo: 'map', pathMatch: 'full' },
  { path: 'map', component: MapPageComponent, data: { animation: 'map' } },
  { path: 'itineraries', component: ItinerariesPageComponent, data: { animation: 'itineraries' } },
  { path: '**', redirectTo: 'map' },
];
