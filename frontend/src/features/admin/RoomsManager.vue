<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { adminApi } from '../../services/api'
import { money } from '../../types'

interface RoomTypeData {
  id: number
  name: string
  description: string
  capacity: number
  amenities: string[]
  nightly_rate_minor: number
  total_rooms: number
}

interface RoomData {
  id: number
  number: string
  type_id: number
  type_name: string
  capacity: number
  nightly_rate_minor: number
  cleaning: string
  in_service: boolean
  active_stay: boolean
}

const activeTab = ref<'types' | 'rooms'>('types')
const error = ref('')
const successNotice = ref('')
const busy = ref(false)

// Queries
const roomTypes = useQuery({
  queryKey: ['admin', 'room-types'],
  queryFn: () => adminApi<RoomTypeData[]>('/admin/room-types'),
})

const rooms = useQuery({
  queryKey: ['admin', 'rooms'],
  queryFn: () => adminApi<RoomData[]>('/admin/rooms'),
})

// Room filter / search
const roomSearch = ref('')
const selectedTypeFilter = ref<number | 'all'>('all')

const filteredRooms = computed(() => {
  const list = rooms.data.value ?? []
  return list.filter(r => {
    const matchesSearch = !roomSearch.value || r.number.toLowerCase().includes(roomSearch.value.toLowerCase()) || r.type_name.toLowerCase().includes(roomSearch.value.toLowerCase())
    const matchesType = selectedTypeFilter.value === 'all' || r.type_id === selectedTypeFilter.value
    return matchesSearch && matchesType
  })
})

// ── Room Type Modal State ─────────────────────────────────────
const showTypeModal = ref(false)
const editingTypeId = ref<number | null>(null)
const typeForm = ref({
  name: '',
  description: '',
  capacity: 2,
  rateDollars: '120.00',
  amenities: [] as string[],
  newAmenity: '',
})

const PRESET_AMENITIES = [
  'King Bed', 'Twin Beds', 'Ocean View', 'Balcony', 'Rain Shower',
  'Bathtub', 'Espresso Bar', 'Mini Bar', 'High-speed Wi-Fi',
  'Work Desk', 'Air Conditioning', 'Bathrobes & Slippers', 'In-room Safe'
]

function openCreateType() {
  editingTypeId.value = null
  typeForm.value = {
    name: '',
    description: '',
    capacity: 2,
    rateDollars: '120.00',
    amenities: ['King Bed', 'Rain Shower', 'High-speed Wi-Fi'],
    newAmenity: '',
  }
  error.value = ''
  successNotice.value = ''
  showTypeModal.value = true
}

function openEditType(rt: RoomTypeData) {
  editingTypeId.value = rt.id
  typeForm.value = {
    name: rt.name,
    description: rt.description,
    capacity: rt.capacity,
    rateDollars: (rt.nightly_rate_minor / 100).toFixed(2),
    amenities: [...(rt.amenities || [])],
    newAmenity: '',
  }
  error.value = ''
  successNotice.value = ''
  showTypeModal.value = true
}

function closeTypeModal() {
  showTypeModal.value = false
  editingTypeId.value = null
}

function toggleAmenity(amenity: string) {
  const index = typeForm.value.amenities.indexOf(amenity)
  if (index >= 0) {
    typeForm.value.amenities.splice(index, 1)
  } else {
    typeForm.value.amenities.push(amenity)
  }
}

function addCustomAmenity() {
  const val = typeForm.value.newAmenity.trim()
  if (val && !typeForm.value.amenities.includes(val)) {
    typeForm.value.amenities.push(val)
  }
  typeForm.value.newAmenity = ''
}

async function saveRoomType() {
  if (busy.value) return
  error.value = ''
  successNotice.value = ''

  const rateFloat = parseFloat(typeForm.value.rateDollars)
  if (isNaN(rateFloat) || rateFloat <= 0) {
    error.value = 'Please enter a valid positive nightly rate.'
    return
  }

  busy.value = true
  const payload = {
    name: typeForm.value.name.trim(),
    description: typeForm.value.description.trim(),
    capacity: Number(typeForm.value.capacity),
    amenities: typeForm.value.amenities,
    nightly_rate_minor: Math.round(rateFloat * 100),
  }

  try {
    if (editingTypeId.value) {
      await adminApi(`/admin/room-types/${editingTypeId.value}`, payload, 'PATCH')
      successNotice.value = `Room type "${payload.name}" updated successfully.`
    } else {
      await adminApi('/admin/room-types', payload)
      successNotice.value = `Room type "${payload.name}" created successfully.`
    }
    await roomTypes.refetch()
    await rooms.refetch()
    closeTypeModal()
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

async function deleteRoomType(rt: RoomTypeData) {
  if (rt.total_rooms > 0) {
    error.value = `Cannot delete "${rt.name}" because it currently has ${rt.total_rooms} assigned room(s). Reassign or delete rooms first.`
    return
  }
  if (!confirm(`Are you sure you want to delete room type "${rt.name}"? This cannot be undone.`)) return

  busy.value = true
  error.value = ''
  successNotice.value = ''
  try {
    await adminApi(`/admin/room-types/${rt.id}`, {}, 'DELETE')
    successNotice.value = `Room type "${rt.name}" was deleted.`
    await roomTypes.refetch()
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

// ── Room Modal State ──────────────────────────────────────────
const showRoomModal = ref(false)
const editingRoomId = ref<number | null>(null)
const roomForm = ref({
  number: '',
  type_id: 0,
  in_service: true,
  cleaning: 'READY',
})

function openCreateRoom() {
  editingRoomId.value = null
  const defaultTypeId = roomTypes.data.value?.[0]?.id ?? 0
  roomForm.value = {
    number: '',
    type_id: defaultTypeId,
    in_service: true,
    cleaning: 'READY',
  }
  error.value = ''
  successNotice.value = ''
  showRoomModal.value = true
}

function openEditRoom(r: RoomData) {
  editingRoomId.value = r.id
  roomForm.value = {
    number: r.number,
    type_id: r.type_id,
    in_service: r.in_service,
    cleaning: r.cleaning,
  }
  error.value = ''
  successNotice.value = ''
  showRoomModal.value = true
}

function closeRoomModal() {
  showRoomModal.value = false
  editingRoomId.value = null
}

async function saveRoom() {
  if (busy.value) return
  error.value = ''
  successNotice.value = ''

  if (!roomForm.value.number.trim()) {
    error.value = 'Please enter a room number.'
    return
  }
  if (!roomForm.value.type_id) {
    error.value = 'Please select a room type.'
    return
  }

  busy.value = true
  const payload = {
    number: roomForm.value.number.trim(),
    type_id: roomForm.value.type_id,
    in_service: roomForm.value.in_service,
    cleaning: roomForm.value.cleaning,
  }

  try {
    if (editingRoomId.value) {
      await adminApi(`/admin/rooms/${editingRoomId.value}`, payload, 'PATCH')
      successNotice.value = `Room ${payload.number} updated successfully.`
    } else {
      await adminApi('/admin/rooms', payload)
      successNotice.value = `Room ${payload.number} created successfully.`
    }
    await rooms.refetch()
    await roomTypes.refetch()
    closeRoomModal()
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

async function deleteRoom(r: RoomData) {
  if (r.active_stay) {
    error.value = `Cannot delete Room ${r.number} because a guest is currently checked in.`
    return
  }
  if (!confirm(`Are you sure you want to delete Room ${r.number}? This will permanently remove the room record.`)) return

  busy.value = true
  error.value = ''
  successNotice.value = ''
  try {
    await adminApi(`/admin/rooms/${r.id}`, {}, 'DELETE')
    successNotice.value = `Room ${r.number} was deleted.`
    await rooms.refetch()
    await roomTypes.refetch()
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

function cleaningBadgeClass(status: string) {
  switch (status) {
    case 'READY': return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300 border-emerald-300'
    case 'CLEANING': return 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300 border-amber-300'
    case 'INSPECTION': return 'bg-purple-100 text-purple-800 dark:bg-purple-950/70 dark:text-purple-300 border-purple-300'
    case 'DIRTY': return 'bg-rose-100 text-rose-800 dark:bg-rose-950/70 dark:text-rose-300 border-rose-300'
    default: return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header with Sub-tabs and Create button -->
    <div class="flex flex-wrap items-center justify-between gap-4 mt-6">
      <div>
        <h2 class="text-2xl font-serif">Rooms & Inventory Control</h2>
        <p class="text-sm text-[var(--muted)] mt-1">
          Full management of room types, descriptions, capacities, amenities, and individual room service status.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <div class="inline-flex rounded-lg p-1 bg-[var(--surface-muted)] border border-[var(--line)]">
          <button
            type="button"
            class="px-3 py-1.5 text-xs font-semibold rounded-md transition"
            :class="activeTab === 'types' ? 'bg-[var(--surface)] text-[var(--ink)] shadow-sm' : 'text-[var(--muted)] hover:text-[var(--ink)]'"
            @click="activeTab = 'types'"
          >
            Room Types ({{ roomTypes.data.value?.length ?? 0 }})
          </button>
          <button
            type="button"
            class="px-3 py-1.5 text-xs font-semibold rounded-md transition"
            :class="activeTab === 'rooms' ? 'bg-[var(--surface)] text-[var(--ink)] shadow-sm' : 'text-[var(--muted)] hover:text-[var(--ink)]'"
            @click="activeTab = 'rooms'"
          >
            All Rooms ({{ rooms.data.value?.length ?? 0 }})
          </button>
        </div>

        <button
          v-if="activeTab === 'types'"
          type="button"
          class="btn text-sm flex items-center gap-1.5"
          @click="openCreateType"
        >
          <span>+ Add Room Type</span>
        </button>
        <button
          v-else
          type="button"
          class="btn text-sm flex items-center gap-1.5"
          @click="openCreateRoom"
        >
          <span>+ Add Physical Room</span>
        </button>
      </div>
    </div>

    <Notice :message="error" />
    <Notice :message="successNotice" status />

    <!-- ── TAB 1: ROOM TYPES ──────────────────────────────────── -->
    <div v-if="activeTab === 'types'" class="space-y-4">
      <div v-if="roomTypes.isPending.value" role="status" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <div v-for="i in 3" :key="i" class="card p-6 space-y-3">
          <div class="skeleton h-6 w-32 rounded"></div>
          <div class="skeleton h-4 w-48 rounded"></div>
          <div class="skeleton h-12 w-full rounded"></div>
        </div>
      </div>

      <p v-else-if="roomTypes.data.value?.length === 0" class="card p-8 text-center text-[var(--muted)]">
        No room types configured. Click "+ Add Room Type" to create the first category.
      </p>

      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <article
          v-for="rt in roomTypes.data.value"
          :key="rt.id"
          class="card p-6 flex flex-col justify-between border border-[var(--line)] hover:border-[var(--brand)] transition group"
        >
          <div>
            <div class="flex items-start justify-between gap-3 mb-2">
              <div>
                <span class="text-xs font-bold text-[var(--brand)]">
                  Capacity: {{ rt.capacity }} guest{{ rt.capacity > 1 ? 's' : '' }}
                </span>
                <h3 class="text-xl font-serif mt-1 text-[var(--ink)]">{{ rt.name }}</h3>
              </div>
              <span class="text-lg tabular-nums font-bold text-[var(--brand-text)] whitespace-nowrap">
                {{ money(rt.nightly_rate_minor) }}
                <span class="text-xs font-normal text-[var(--muted)]">/ night</span>
              </span>
            </div>

            <p class="text-xs text-[var(--muted)] line-clamp-3 mt-2 leading-relaxed">
              {{ rt.description || 'No description provided.' }}
            </p>

            <!-- Amenities Chips -->
            <div v-if="rt.amenities?.length" class="mt-4 flex flex-wrap gap-1.5">
              <span
                v-for="a in rt.amenities.slice(0, 5)"
                :key="a"
                class="px-2 py-0.5 rounded-full text-[11px] bg-[var(--surface-muted)] text-[var(--ink)] border border-[var(--line)]"
              >
                {{ a }}
              </span>
              <span v-if="rt.amenities.length > 5" class="text-[11px] text-[var(--muted)] self-center">
                +{{ rt.amenities.length - 5 }} more
              </span>
            </div>
          </div>

          <div class="mt-6 pt-4 border-t border-[var(--line)] flex items-center justify-between text-xs">
            <span class="text-[var(--muted)]">
              <strong>{{ rt.total_rooms }}</strong> room{{ rt.total_rooms === 1 ? '' : 's' }} assigned
            </span>

            <div class="flex items-center gap-2">
              <button
                type="button"
                class="btn-secondary text-xs px-2.5 py-1"
                @click="openEditType(rt)"
              >
                Edit
              </button>
              <button
                type="button"
                class="btn-secondary text-xs px-2.5 py-1 text-rose-600 hover:text-rose-700 dark:text-rose-400"
                :disabled="rt.total_rooms > 0"
                :title="rt.total_rooms > 0 ? 'Cannot delete: rooms are assigned' : 'Delete room type'"
                @click="deleteRoomType(rt)"
              >
                Delete
              </button>
            </div>
          </div>
        </article>
      </div>
    </div>

    <!-- ── TAB 2: PHYSICAL ROOMS ──────────────────────────────── -->
    <div v-else class="space-y-4">
      <!-- Search & Filters -->
      <div class="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-[var(--surface-muted)] border border-[var(--line)]">
        <div class="flex flex-wrap items-center gap-3">
          <input
            v-model="roomSearch"
            type="search"
            placeholder="Search room number or type…"
            class="field text-sm w-64"
          />
          <select v-model="selectedTypeFilter" class="field text-sm">
            <option :value="'all'">All Room Types</option>
            <option v-for="t in roomTypes.data.value" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <span class="text-xs text-[var(--muted)]">Showing {{ filteredRooms.length }} of {{ rooms.data.value?.length ?? 0 }} rooms</span>
      </div>

      <div v-if="rooms.isPending.value" role="status" class="card p-6">
        <p>Loading rooms…</p>
      </div>

      <div v-else class="card overflow-auto">
        <table class="data-table w-full text-left text-sm min-w-[700px]">
          <thead>
            <tr class="bg-[var(--surface-muted)] border-b border-[var(--line)] text-xs text-[var(--muted)] font-semibold">
              <th class="py-3 px-4">Room #</th>
              <th class="py-3 px-4">Type</th>
              <th class="py-3 px-4">Nightly Rate</th>
              <th class="py-3 px-4">Capacity</th>
              <th class="py-3 px-4">Cleaning</th>
              <th class="py-3 px-4">Service Status</th>
              <th class="py-3 px-4">Occupancy</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in filteredRooms"
              :key="r.id"
              class="border-t border-[var(--line)] hover:bg-[var(--surface-muted)]/50 transition"
            >
              <td class="py-3 px-4 tabular-nums font-bold text-base text-[var(--ink)]">
                {{ r.number }}
              </td>
              <td class="py-3 px-4 font-medium">{{ r.type_name }}</td>
              <td class="py-3 px-4 tabular-nums">{{ money(r.nightly_rate_minor) }}</td>
              <td class="py-3 px-4 text-xs text-[var(--muted)]">{{ r.capacity }} guest(s)</td>
              <td class="py-3 px-4">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border"
                  :class="cleaningBadgeClass(r.cleaning)"
                >
                  {{ r.cleaning }}
                </span>
              </td>
              <td class="py-3 px-4">
                <span
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border"
                  :class="r.in_service ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300'"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="r.in_service ? 'bg-emerald-500' : 'bg-rose-500'"></span>
                  {{ r.in_service ? 'In Service' : 'Maintenance' }}
                </span>
              </td>
              <td class="py-3 px-4">
                <span v-if="r.active_stay" class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                  Occupied
                </span>
                <span v-else class="text-xs text-[var(--muted)]">Vacant</span>
              </td>
              <td class="py-3 px-4 text-right whitespace-nowrap">
                <div class="inline-flex items-center gap-2">
                  <button type="button" class="btn-secondary text-xs px-2.5 py-1" @click="openEditRoom(r)">Edit</button>
                  <button
                    type="button"
                    class="btn-secondary text-xs px-2.5 py-1 text-rose-600 hover:text-rose-700 dark:text-rose-400"
                    :disabled="r.active_stay"
                    :title="r.active_stay ? 'Cannot delete occupied room' : 'Delete room'"
                    @click="deleteRoom(r)"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── ROOM TYPE MODAL ────────────────────────────────────── -->
    <Transition name="modal">
      <div
        v-if="showTypeModal"
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        :aria-label="editingTypeId ? 'Edit Room Type' : 'Add Room Type'"
        @click.self="closeTypeModal"
      >
        <form class="card p-8 w-full max-w-xl max-h-[90vh] overflow-y-auto space-y-5" @submit.prevent="saveRoomType">
          <button type="button" class="float-right text-lg text-[var(--muted)] hover:text-[var(--ink)]" aria-label="Close" @click="closeTypeModal">✕</button>
          <div>
            <p class="label mb-0">Room Inventory</p>
            <h3 class="text-2xl font-serif">{{ editingTypeId ? 'Edit Room Type' : 'Create Room Type' }}</h3>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div class="sm:col-span-2">
              <label class="label mb-1">Room Type Name</label>
              <input v-model="typeForm.name" class="field w-full" placeholder="e.g. Deluxe Garden Villa" required />
            </div>

            <div>
              <label class="label mb-1">Nightly Rate (USD $)</label>
              <input v-model="typeForm.rateDollars" type="number" step="0.01" min="1" class="field w-full tabular-nums" placeholder="120.00" required />
            </div>

            <div>
              <label class="label mb-1">Maximum Capacity (Guests)</label>
              <input v-model.number="typeForm.capacity" type="number" min="1" max="20" class="field w-full" required />
            </div>

            <div class="sm:col-span-2">
              <label class="label mb-1">Room Description</label>
              <textarea
                v-model="typeForm.description"
                class="field w-full h-24 text-sm"
                placeholder="Describe room layout, architecture, views, bedding, and aesthetic details…"
              ></textarea>
            </div>

            <div class="sm:col-span-2">
              <label class="label mb-1">Amenities</label>
              <p class="text-xs text-[var(--muted)] mb-2">Click to toggle amenities or add custom ones below:</p>
              
              <div class="flex flex-wrap gap-1.5 mb-3">
                <button
                  v-for="amenity in PRESET_AMENITIES"
                  :key="amenity"
                  type="button"
                  class="px-2.5 py-1 rounded-full text-xs border transition"
                  :class="typeForm.amenities.includes(amenity)
                    ? 'bg-[var(--brand)] text-[var(--brand-ink,white)] border-[var(--brand)] font-semibold'
                    : 'bg-[var(--surface-muted)] text-[var(--muted)] border-[var(--line)] hover:text-[var(--ink)]'"
                  @click="toggleAmenity(amenity)"
                >
                  {{ typeForm.amenities.includes(amenity) ? '✓ ' : '+ ' }}{{ amenity }}
                </button>
              </div>

              <!-- Custom amenity input -->
              <div class="flex gap-2">
                <input
                  v-model="typeForm.newAmenity"
                  type="text"
                  placeholder="Custom amenity (e.g. Private Plunge Pool)…"
                  class="field text-xs flex-1"
                  @keydown.enter.prevent="addCustomAmenity"
                />
                <button type="button" class="btn-secondary text-xs px-3" @click="addCustomAmenity">Add</button>
              </div>
            </div>
          </div>

          <Notice :message="error" />

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-[var(--line)]">
            <button type="button" class="btn-secondary" @click="closeTypeModal">Cancel</button>
            <button class="btn" :disabled="busy">{{ busy ? 'Saving…' : (editingTypeId ? 'Save Changes' : 'Create Room Type') }}</button>
          </div>
        </form>
      </div>
    </Transition>

    <!-- ── ROOM MODAL ─────────────────────────────────────────── -->
    <Transition name="modal">
      <div
        v-if="showRoomModal"
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        :aria-label="editingRoomId ? 'Edit Room' : 'Add Physical Room'"
        @click.self="closeRoomModal"
      >
        <form class="card p-8 w-full max-w-md space-y-5" @submit.prevent="saveRoom">
          <button type="button" class="float-right text-lg text-[var(--muted)] hover:text-[var(--ink)]" aria-label="Close" @click="closeRoomModal">✕</button>
          <div>
            <p class="label mb-0">Room Inventory</p>
            <h3 class="text-2xl font-serif">{{ editingRoomId ? 'Edit Room' : 'Add Physical Room' }}</h3>
          </div>

          <div>
            <label class="label mb-1">Room Number</label>
            <input v-model="roomForm.number" class="field w-full tabular-nums text-base" placeholder="e.g. 101, 202, PH-1" required />
          </div>

          <div>
            <label class="label mb-1">Room Type</label>
            <select v-model="roomForm.type_id" class="field w-full" required>
              <option disabled :value="0">Select a room type</option>
              <option v-for="t in roomTypes.data.value" :key="t.id" :value="t.id">
                {{ t.name }} ({{ money(t.nightly_rate_minor) }}/night)
              </option>
            </select>
          </div>

          <div>
            <label class="label mb-1">Cleaning Status</label>
            <select v-model="roomForm.cleaning" class="field w-full">
              <option value="READY">READY (Clean & inspected)</option>
              <option value="CLEANING">CLEANING (Housekeeper in room)</option>
              <option value="INSPECTION">INSPECTION (Pending supervisor check)</option>
              <option value="DIRTY">DIRTY (Needs turnover)</option>
            </select>
          </div>

          <div class="flex items-center justify-between p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--line)]">
            <div>
              <p class="text-sm font-semibold text-[var(--ink)]">Operational Service</p>
              <p class="text-xs text-[var(--muted)]">Toggle off to place room in maintenance / out of order</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input v-model="roomForm.in_service" type="checkbox" class="sr-only peer" />
              <div class="w-11 h-6 bg-slate-300 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--brand)]"></div>
            </label>
          </div>

          <Notice :message="error" />

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-[var(--line)]">
            <button type="button" class="btn-secondary" @click="closeRoomModal">Cancel</button>
            <button class="btn" :disabled="busy">{{ busy ? 'Saving…' : (editingRoomId ? 'Update Room' : 'Add Room') }}</button>
          </div>
        </form>
      </div>
    </Transition>
  </div>
</template>
