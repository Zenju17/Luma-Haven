export interface Room {
  id: number
  number: string
  type: string
  description?: string
  amenities?: string[]
  capacity: number
  rate_minor?: number
  currency?: string
  cleaning?: string
  in_service?: boolean
  occupied?: boolean
}

export interface Quote {
  id: string
  room_amount_minor: number
  tax_minor: number
  total_minor: number
  currency: string
  expires_at: string
}

export interface Booking {
  payment_provider?: 'development' | 'bakong'
  id: number
  reference: string
  status: string
  arrival: string
  departure: string
  hotel_today: string
  hotel_timezone: string
  room: string
  room_type: string
  guest_name: string
  verified: boolean
  currency: string
  balance_minor: number
  folio_version: number
  entries: { category: string; description: string; amount_minor: number; service_date: string }[]
  requests: { id: number; type: string; description: string; status: string }[]
  checked_in_at: string | null
  checked_out_at: string | null
}

export interface StaffUser { username: string; role: string }
export interface Task { id: number; room__number: string; status: string; notes: string; assignee__username?: string }
export interface GuestRequest { id: number; type: string; description: string; status: string }

export interface DecisionAlert {
  id: string
  severity: 'URGENT' | 'WARNING' | 'INFO'
  category: string
  title: string
  what_happened: string
  records_involved: string
  why_it_matters: string
  recommended_action: string
}

export interface RoomTypePerformance {
  id: number
  name: string
  capacity: number
  total_rooms: number
  nightly_rate_minor: number
  sellable_room_nights: number
  sold_room_nights: number
  occupancy_rate_percent: number | null
  net_room_revenue_minor: number
  adr_minor: number | null
}

export interface DailyTrendPoint {
  date: string
  sellable: number
  sold: number
  revenue_minor: number
}

export interface ManagerKPIs {
  hotel: string
  timezone: string
  currency: string
  start: string
  end_exclusive: string
  days: number
  generated_at: string
  total_rooms: number
  sellable_room_nights: number
  sold_room_nights: number
  occupancy_rate_percent: number | null
  average_daily_rate_minor: number | null
  revpar_minor: number | null
  net_room_revenue_minor: number
  settled_cash_minor: number
  gross_cash_minor: number
  refunded_cash_minor: number
  outstanding_balances_minor: number
  cancellations_count: number
  no_shows_count: number
  cancellation_rate_percent: number | null
  avg_housekeeping_turnaround_minutes: number | null
  daily_breakdown: DailyTrendPoint[]
}

export interface ManagerOperations {
  arrivals: { total: number; checked_in: number; pending: number }
  departures: { total: number; checked_out: number; pending: number }
  unready_arrivals_today: { id: number; number: string; cleaning: string; in_service: boolean; type__name: string }[]
  open_maintenance: { id: number; room__number: string; description: string; priority: string; status: string; created_at: string }[]
  open_requests: { id: number; stay__reservation__reference: string; stay__reservation__room__number: string; type: string; description: string; status: string; submitted_at: string }[]
  pending_refunds: { id: number; payment__attempt__reservation__reference: string; amount_minor: number; reason: string; status: string; requested_by__username: string; created_at: string }[]
  payment_exceptions_count: number
}

export interface ManagerDashboardData {
  kpis: ManagerKPIs
  trends: DailyTrendPoint[]
  room_types: RoomTypePerformance[]
  readiness: { total: number; ready: number; cleaning: number; inspection: number; dirty: number; out_of_service: number }
  operations: ManagerOperations
  alerts: DecisionAlert[]
  metadata: { hotel: string; timezone: string; currency: string; start: string; end: string; generated_at: string }
}

export interface RefundRecord {
  id: number
  payment_id: number
  reservation_reference: string
  guest_name: string
  amount_minor: number
  reason: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'SETTLED'
  requested_by: string | null
  reviewed_by: string | null
  created_at: string
  settled_at: string | null
}

export interface RoomTypeRate {
  id: number
  name: string
  description: string
  capacity: number
  nightly_rate_minor: number
  total_rooms: number
}

export interface ReconciliationItem {
  reservation_id: number
  reference: string
  guest_name: string
  arrival: string
  departure: string
  status: string
  currency: string
  charges_minor: number
  settled_minor: number
  refunds_minor: number
  balance_minor: number
  is_balanced: boolean
  has_exception: boolean
  folio_closed: boolean
}

export interface AccountantPayment {
  id: number
  reservation_id: number
  reference: string
  guest_name: string
  amount_minor: number
  currency: string
  status: string
  created_at: string
  settled_at: string | null
  gateway_reference: string
  has_exception: boolean
  exception_resolved: boolean
}

export interface DiagnosticItem {
  code: string
  message: string
  blocking: boolean
  severity: 'ERROR' | 'WARNING' | 'INFO'
}

export interface ReservationDiagnostics {
  reservation_id: number
  reference: string
  guest_name: string
  status: string
  room_number: string
  room_cleaning: string
  room_in_service: boolean
  balance_minor: number
  verified: boolean
  eligible_check_in: boolean
  eligible_check_out: boolean
  check_in_diagnostics: DiagnosticItem[]
  check_out_diagnostics: DiagnosticItem[]
}

export interface AdminHealthDiagnostics {
  timestamp: string
  services: {
    database: { status: 'ONLINE' | 'ERROR'; latency_ms?: number; error?: string }
    redis: { status: 'ONLINE' | 'ERROR'; latency_ms?: number; error?: string }
  }
  unresolved_payment_exceptions: number
  failed_payment_attempts_24h: number
  outbox_backlog: number
  all_healthy: boolean
}

export const money = (minor: number) => `$${(minor / 100).toFixed(2)}`

export interface VisualAsset {
  id: number
  category: 'BRANDING' | 'HERO' | 'GALLERY' | 'ROOM_TYPE' | 'EXPERIENCE' | 'OTHER'
  room_type_id: number | null
  room_type_name: string | null
  image_url: string
  title: string
  caption: string
  alt_text: string
  display_order: number
  is_active: boolean
  source_type: 'CONCEPT' | 'VERIFIED' | 'PLACEHOLDER'
  facility_claim: string
  original_filename: string
  file_size_bytes: number
  width: number
  height: number
  created_at: string
  updated_at: string
}

export interface PublicVisualAssetsResponse {
  items: VisualAsset[]
  hero: VisualAsset | null
  logo: VisualAsset | null
  gallery: VisualAsset[]
  features: VisualAsset[]
  room_types: Record<string, VisualAsset[]>
}


export interface LegalDocSummary { id: number; kind: string; language: 'en' | 'km'; version: number; title: string; effective_at: string | null }
export interface LegalDoc extends LegalDocSummary { body_markdown: string }
export interface DataRequestResult { id: number; type: string; status: string; due_at: string }
