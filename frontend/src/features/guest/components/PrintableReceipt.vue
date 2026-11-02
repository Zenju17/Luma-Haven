<script setup lang="ts">
import { computed } from 'vue'
import { money, type Booking } from '../../../types'

const props = defineProps<{
  booking: Booking
}>()

const nights = computed(() => {
  if (!props.booking.arrival || !props.booking.departure) return 1
  const start = new Date(props.booking.arrival).getTime()
  const end = new Date(props.booking.departure).getTime()
  const diff = Math.round((end - start) / (1000 * 60 * 60 * 24))
  return diff > 0 ? diff : 1
})

const totalCharges = computed(() => {
  const sum = props.booking.entries
    ?.filter((e) => e.amount_minor > 0)
    .reduce((acc, e) => acc + e.amount_minor, 0) || 0
  return sum > 0 ? sum : props.booking.balance_minor
})

const totalPayments = computed(() => {
  if (props.booking.balance_minor === 0) {
    return totalCharges.value
  }
  return Math.max(0, totalCharges.value - props.booking.balance_minor)
})

const isFullyPaid = computed(() => props.booking.balance_minor === 0)

const printedDate = computed(() => {
  return props.booking.hotel_today || new Date().toISOString().slice(0, 10)
})
</script>

<template>
  <div class="printable-receipt hidden print:block bg-white text-slate-900 font-sans p-0 m-0 w-full">
    <!-- Header -->
    <div class="flex items-start justify-between pb-6 border-b-2 border-slate-900">
      <div class="flex items-center gap-4">
        <img
          src="/images/luma-haven/branding/logo.png"
          alt="Luma Haven Logo"
          class="w-14 h-14 object-contain"
        />
        <div>
          <h1 class="text-2xl font-serif font-bold text-slate-900 tracking-wide uppercase">Luma Haven</h1>
          <p class="text-xs text-slate-600 font-medium tracking-wider uppercase">Boutique Hotel & Sanctuary</p>
          <p class="text-xs text-slate-500 mt-1">Daun Penh, Phnom Penh, Cambodia</p>
          <p class="text-[11px] text-slate-500">Tel: +855 23 987 654 · contact@lumahaven.com</p>
        </div>
      </div>
      <div class="text-right">
        <h2 class="text-xl font-serif font-bold text-slate-900 tracking-wider">OFFICIAL RECEIPT</h2>
        <p class="text-xs font-semibold text-slate-600 uppercase tracking-widest mt-0.5">Guest Folio & Invoice</p>
        <div class="mt-3 space-y-0.5 text-xs text-slate-600">
          <p><span class="text-slate-400">Folio Ref:</span> <span class="font-mono font-bold text-slate-900">{{ booking.reference }}</span></p>
          <p><span class="text-slate-400">Date Issued:</span> <span class="font-medium text-slate-800">{{ printedDate }}</span></p>
          <p><span class="text-slate-400">Status:</span> 
            <span :class="isFullyPaid ? 'text-emerald-700 font-bold' : 'text-amber-700 font-bold'">
              {{ isFullyPaid ? 'PAID IN FULL' : 'BALANCE OUTSTANDING' }}
            </span>
          </p>
        </div>
      </div>
    </div>

    <!-- Guest & Stay Metadata Box -->
    <div class="grid grid-cols-2 gap-6 my-6 p-4 bg-slate-50 rounded-lg border border-slate-200 text-xs">
      <div>
        <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">Guest Information</span>
        <p class="text-sm font-bold text-slate-900">{{ booking.guest_name }}</p>
        <p class="text-slate-600 mt-0.5">Verification: <span class="text-emerald-700 font-semibold">{{ booking.verified ? 'Verified Guest ✓' : 'Direct Booking' }}</span></p>
        <p class="text-slate-600 mt-0.5">Payment Method: <span class="font-medium">{{ booking.payment_provider === 'bakong' ? 'Bakong KHQR (Universal)' : 'Electronic Settlement' }}</span></p>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">Room Details</span>
          <p class="font-bold text-slate-900">{{ booking.room_type }}</p>
          <p class="text-slate-600 font-mono font-semibold">Room {{ booking.room }}</p>
        </div>
        <div>
          <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">Stay Duration</span>
          <p class="text-slate-900"><span class="text-slate-500">In:</span> {{ booking.arrival }}</p>
          <p class="text-slate-900"><span class="text-slate-500">Out:</span> {{ booking.departure }}</p>
          <p class="text-slate-500 font-medium mt-0.5">{{ nights }} Night{{ nights > 1 ? 's' : '' }}</p>
        </div>
      </div>
    </div>

    <!-- Itemized Ledger Table -->
    <div class="mt-6">
      <h3 class="text-xs uppercase font-bold tracking-wider text-slate-700 mb-2">Itemized Charges & Credits</h3>
      <table class="w-full text-xs border-collapse">
        <thead>
          <tr class="border-y-2 border-slate-900 bg-slate-100 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
            <th class="py-2.5 px-3 text-left">Date</th>
            <th class="py-2.5 px-3 text-left">Description</th>
            <th class="py-2.5 px-3 text-left">Category</th>
            <th class="py-2.5 px-3 text-right">Charges (USD)</th>
            <th class="py-2.5 px-3 text-right">Credits (USD)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-200">
          <tr v-for="(entry, idx) in booking.entries" :key="idx" class="hover:bg-slate-50">
            <td class="py-2 px-3 text-slate-600 font-mono">{{ entry.service_date }}</td>
            <td class="py-2 px-3 text-slate-900 font-medium">{{ entry.description }}</td>
            <td class="py-2 px-3 text-slate-600 font-mono text-[10px] uppercase">{{ entry.category }}</td>
            <td class="py-2 px-3 text-right text-slate-900 font-mono font-medium">{{ money(entry.amount_minor) }}</td>
            <td class="py-2 px-3 text-right text-slate-400 font-mono">—</td>
          </tr>
          <!-- If fully paid, show settled payment credit line -->
          <tr v-if="isFullyPaid" class="bg-emerald-50/60 font-medium">
            <td class="py-2 px-3 text-slate-600 font-mono">{{ printedDate }}</td>
            <td class="py-2 px-3 text-emerald-900">
              Payment Settled · {{ booking.payment_provider === 'bakong' ? 'Bakong KHQR' : 'Hotel Settlement' }}
            </td>
            <td class="py-2 px-3 text-emerald-700 font-mono text-[10px] uppercase">PAYMENT</td>
            <td class="py-2 px-3 text-right text-slate-400 font-mono">—</td>
            <td class="py-2 px-3 text-right text-emerald-800 font-mono font-bold">{{ money(totalPayments) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Totals Summary Breakdown -->
    <div class="mt-6 pt-4 border-t-2 border-slate-900 flex justify-between items-start">
      <!-- Stamp / Note -->
      <div class="max-w-xs">
        <div v-if="isFullyPaid" class="inline-flex items-center gap-2 px-4 py-2 border-2 border-emerald-600 rounded-lg text-emerald-800 font-bold tracking-widest uppercase text-xs">
          <span>✓ PAID IN FULL</span>
        </div>
        <div v-else class="inline-flex items-center gap-2 px-4 py-2 border-2 border-amber-600 rounded-lg text-amber-800 font-bold tracking-widest uppercase text-xs">
          <span>⚠ BALANCE DUE: {{ money(booking.balance_minor) }}</span>
        </div>
        <p class="text-[11px] text-slate-500 mt-3 leading-relaxed">
          All room rates are inclusive of government taxes, service charge, and Wi-Fi access.
        </p>
      </div>

      <!-- Financial Calculation -->
      <div class="w-64 space-y-1.5 text-xs text-slate-700">
        <div class="flex justify-between py-1 border-b border-slate-200">
          <span class="text-slate-500">Total Charges:</span>
          <span class="font-mono font-semibold text-slate-900">{{ money(totalCharges) }}</span>
        </div>
        <div class="flex justify-between py-1 border-b border-slate-200">
          <span class="text-slate-500">Taxes & Fees (Included):</span>
          <span class="font-mono text-slate-600">$0.00</span>
        </div>
        <div class="flex justify-between py-1 border-b border-slate-200">
          <span class="text-slate-500">Total Payments:</span>
          <span class="font-mono font-semibold text-emerald-700">{{ money(totalPayments) }}</span>
        </div>
        <div class="flex justify-between py-2 text-sm font-bold border-b-2 border-slate-900 text-slate-900">
          <span>Balance Due:</span>
          <span class="font-mono" :class="isFullyPaid ? 'text-emerald-700' : 'text-amber-700'">
            {{ money(booking.balance_minor) }} {{ booking.currency }}
          </span>
        </div>
      </div>
    </div>

    <!-- Official Footer -->
    <div class="mt-12 pt-6 border-t border-slate-200 text-center text-slate-500 text-[11px] space-y-1">
      <p class="font-serif italic text-slate-700 text-xs">"Thank you for staying at Luma Haven. We look forward to welcoming you back."</p>
      <p class="text-[10px] text-slate-400">
        Luma Haven Boutique Hotel · Electronic Guest Folio · Computer-generated document valid without signature.
      </p>
    </div>
  </div>
</template>
