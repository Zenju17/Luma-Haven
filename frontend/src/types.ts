export type Room = {
  id: number
  number: string
  type: string
  capacity: number
  rate_minor: number
  currency: string
  cleaning: string
  in_service: boolean
  occupied: boolean
}

export type Booking = {
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
  entries: {
    category: string
    description: string
    amount_minor: number
    service_date: string
  }[]
  requests: {
    id: number
    type: string
    description: string
    status: string
  }[]
  checked_in_at: string | null
  checked_out_at: string | null
}

export type Quote = {
  id: string
  total_minor: number
  tax_minor: number
  room_amount_minor: number
}

export type StaffUser = {
  username: string
  role: string
}

export type ServiceRequest = {
  id: number
  type: string
  description: string
  status: string
}

export type HousekeepingTask = {
  id: number
  room__number: string
  status: string
}

export type CheckoutSession = {
  amount_minor: number
  currency: string
  status: string
  reservation_id: number
}
