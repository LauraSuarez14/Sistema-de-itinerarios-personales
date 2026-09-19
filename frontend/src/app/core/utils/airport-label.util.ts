export interface ParsedAirportLabel {
  iata: string;
  name: string;
  city: string;
}

/** Reconstruye el desglose (código IATA, nombre, ciudad) a partir del
 * `label` que ya viene formateado desde el dominio de Airport Service
 * (`"IATA — Nombre (Ciudad)"`, ver Airport.to_plotly_point()). */
export function parseAirportLabel(label: string | undefined): ParsedAirportLabel {
  const match = /^(.*?)\s—\s(.*?)\s\(([^)]*)\)$/.exec(label ?? '');
  if (!match) {
    return { iata: '—', name: label ?? '', city: '' };
  }
  const [, iata, name, city] = match;
  return { iata, name, city };
}
