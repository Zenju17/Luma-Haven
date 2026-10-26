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
export interface Task { id: number; room__number: string; status: string; notes: string }
export interface GuestRequest { id: number; type: string; description: string; status: string }

export const money = (minor: number) => `$${(minor / 100).toFixed(2)}`
