export interface PlotlyPoint {
  id: number;
  lat: number;
  lon: number;
  /** Ya formateado por el dominio de Airport Service como "IATA — Nombre (Ciudad)". */
  label: string;
}

export interface AirportSummary {
  id: number;
  iata_code: string;
  name: string;
}
