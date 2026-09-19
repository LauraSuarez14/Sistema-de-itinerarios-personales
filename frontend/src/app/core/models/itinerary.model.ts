import { AirportSummary } from './airport.model';

export interface Itinerary {
  id: string;
  user_name: string;
  origin_airport: AirportSummary;
  destination_airport: AirportSummary;
  travel_date: string;
  duration_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface PageOut<T = Itinerary> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface CreateItineraryPayload {
  user_name: string;
  origin_airport_id: number;
  destination_airport_id: number;
  travel_date: string;
  duration_minutes: number;
}
