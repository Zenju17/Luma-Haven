<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { staffApi, queryClient } from '../../services/api'
import type { Room, Task } from '../../types'

interface ExtendedTask extends Task {
  priority?: 'NORMAL' | 'HIGH' | 'URGENT'
  created_at?: string
  completed_at?: string
}

const props = defineProps<{
  userRole: string
  username: string
}>()

const busy = ref(false)
const error = ref('')
const successNotice = ref('')
const activeTab = ref<'queue' | 'history'>('queue')
const filterAssignee = ref<'all' | 'me'>('all')

// Tasks Query
const tasks = useQuery({
  queryKey: computed(() => ['housekeeping-tasks', filterAssignee.value]),
  queryFn: () => staffApi<ExtendedTask[]>(`/housekeeping/tasks${filterAssignee.value === 'me' ? '?assignee=me' : ''}`),
})

const historyTasks = useQuery({
  queryKey: ['housekeeping-history'],
  queryFn: () => staffApi<ExtendedTask[]>('/housekeeping/tasks?history=true'),
  enabled: computed(() => activeTab.value === 'history'),
})

const rooms = useQuery({
  queryKey: ['rooms', 'housekeeping'],
  queryFn: () => staffApi<Room[]>('/rooms'),
})

// Inspection Notes Modal
const inspectionTask = ref<ExtendedTask | null>(null)
const inspectionNotes = ref('')

function openInspectionModal(task: ExtendedTask) {
  inspectionTask.value = task
  inspectionNotes.value = 'Linen replaced, sanitized, amenities restocked.'
}

async function submitInspection() {
  if (!inspectionTask.value) return
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/housekeeping/tasks/${inspectionTask.value.id}/transition`, {
      status: 'INSPECTION',
      notes: inspectionNotes.value
    })
    successNotice.value = `Room ${inspectionTask.value.room__number} cleaning finished. Awaiting supervisor inspection.`
    inspectionTask.value = null
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['housekeeping-tasks'] }),
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    ])
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

// Quick Start Cleaning
async function startCleaning(taskId: number, roomNumber: string) {
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/housekeeping/tasks/${taskId}/transition`, { status: 'CLEANING' })
    successNotice.value = `Started cleaning Room ${roomNumber}.`
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['housekeeping-tasks'] }),
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    ])
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

// Maintenance Report Modal
const showMaintenanceModal = ref(false)
const maintRoomId = ref<number | ''>('')
const maintPriority = ref<'NORMAL' | 'HIGH' | 'URGENT'>('NORMAL')
const maintDescription = ref('')

async function submitMaintenance() {
  if (!maintRoomId.value || !maintDescription.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    await staffApi('/maintenance/tickets', {
      room_id: Number(maintRoomId.value),
      priority: maintPriority.value,
      description: maintDescription.value.trim()
    })
    successNotice.value = `Maintenance issue reported. Room taken out of service.`
    showMaintenanceModal.value = false
    maintRoomId.value = ''
    maintDescription.value = ''
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['housekeeping-tasks'] }),
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    ])
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-8">
    <Notice :message="error || (tasks.error.value ? String(tasks.error.value) : '')" />
    <div v-if="successNotice" class="p-4 rounded-xl bg-[var(--status-available)]/10 border border-[var(--status-available)]/30 text-[var(--status-available)] text-sm flex items-center justify-between">
      <span>{{ successNotice }}</span>
      <button class="text-xs font-semibold hover:underline ml-4" @click="successNotice = ''">Dismiss</button>
    </div>

    <!-- Header Actions & Tabs -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <button
          class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
          :class="activeTab === 'queue' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'btn-secondary'"
          @click="activeTab = 'queue'"
        >
          Cleaning Queue
        </button>
        <button
          class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
          :class="activeTab === 'history' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'btn-secondary'"
          @click="activeTab = 'history'"
        >
          Turnaround History
        </button>
      </div>

      <div class="flex items-center gap-3">
        <div v-if="activeTab === 'queue'" class="flex items-center gap-1 border border-[var(--rule)] rounded-lg p-1 bg-[var(--paper)]">
          <button
            class="px-3 py-1 text-xs rounded"
            :class="filterAssignee === 'all' ? 'bg-[var(--rule)] font-bold' : 'text-[var(--silt)]'"
            @click="filterAssignee = 'all'"
          >
            All Rooms
          </button>
          <button
            class="px-3 py-1 text-xs rounded"
            :class="filterAssignee === 'me' ? 'bg-[var(--rule)] font-bold' : 'text-[var(--silt)]'"
            @click="filterAssignee = 'me'"
          >
            Assigned to Me
          </button>
        </div>
        <button class="btn text-xs" @click="showMaintenanceModal = true">
          + Report Maintenance
        </button>
      </div>
    </div>

    <!-- TAB 1: Cleaning Queue -->
    <section v-if="activeTab === 'queue'" class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-serif">Housekeeping Task Board</h2>
          <p class="text-xs text-[var(--silt)] mt-1">Rooms ordered by urgency. Mark rooms in progress, then request inspection upon completion.</p>
        </div>
        <span class="badge">{{ tasks.data.value?.length || 0 }} tasks</span>
      </div>

      <div v-if="tasks.data.value?.length === 0" class="py-12 text-center text-sm text-[var(--silt)]">
        All assigned rooms are clean and in service. Good job!
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="task in tasks.data.value"
          :key="task.id"
          class="p-4 rounded-xl border border-[var(--rule)] bg-[var(--paper)]/60 flex flex-wrap items-center justify-between gap-4"
        >
          <div class="space-y-1">
            <div class="flex items-center gap-3">
              <span class="text-lg font-bold">Room {{ task.room__number }}</span>
              <span
                class="badge text-[10px] font-bold "
                :class="{
                  'bg-[var(--status-out)]/10 text-[var(--status-out)] border-[var(--status-out)]/30': task.priority === 'URGENT',
 'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] border-[var(--status-dirty)]/30': task.priority === 'HIGH',
                  'bg-[var(--sunk)] text-[var(--silt)] border-[var(--rule)]': !task.priority || task.priority === 'NORMAL'
                }"
              >
                {{ task.priority || 'NORMAL' }} PRIORITY
              </span>
              <span
                class="badge text-[10px] font-bold"
                :class="{
                  'bg-[var(--status-out)]/10 text-[var(--status-out)] border-[var(--status-out)]/30': task.status === 'DIRTY',
 'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] border-[var(--status-dirty)]/30': task.status === 'CLEANING',
                  'bg-[var(--status-occupied)]/10 text-[var(--status-occupied)] border-[var(--status-occupied)]/30': task.status === 'INSPECTION'
                }"
              >
                {{ task.status }}
              </span>
            </div>
            <p v-if="task.notes" class="text-xs text-[var(--silt)] italic">Notes: "{{ task.notes }}"</p>
            <p class="text-xs text-[var(--silt)]">
              Assigned: {{ task.assignee__username || 'Unassigned pool' }}
            </p>
          </div>

          <!-- Workflow Action Buttons -->
          <div class="flex items-center gap-2">
            <button
              v-if="task.status === 'DIRTY'"
              class="btn text-xs py-2 px-4"
              :disabled="busy"
              @click="startCleaning(task.id, task.room__number)"
            >
              Start cleaning →
            </button>
            <button
              v-else-if="task.status === 'CLEANING'"
              class="btn-secondary text-xs py-2 px-4 font-semibold"
              :disabled="busy"
              @click="openInspectionModal(task)"
            >
              Request inspection →
            </button>
            <span
              v-else-if="task.status === 'INSPECTION'"
              class="badge bg-[var(--status-occupied)]/10 text-[var(--status-occupied)] border-[var(--status-occupied)]/30 text-xs py-1.5 px-3"
            >
              Awaiting Supervisor Inspection
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2: Turnaround History -->
    <section v-else-if="activeTab === 'history'" class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-serif">Completed Cleaning History</h2>
          <p class="text-xs text-[var(--silt)] mt-1">Audit log of inspected and released rooms.</p>
        </div>
      </div>

      <div v-if="historyTasks.data.value?.length === 0" class="py-12 text-center text-sm text-[var(--silt)]">
        No completed tasks in history yet.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="task in historyTasks.data.value"
          :key="task.id"
          class="p-4 rounded-xl border border-[var(--rule)] bg-[var(--paper)]/40 flex items-center justify-between"
        >
          <div>
            <span class="font-bold text-base">Room {{ task.room__number }}</span>
            <span class="badge ml-3 text-[10px] bg-[var(--status-available)]/10 text-[var(--status-available)]">READY</span>
            <p v-if="task.notes" class="text-xs text-[var(--silt)] mt-1">"{{ task.notes }}"</p>
          </div>
          <span class="text-xs text-[var(--silt)]">Cleaned by {{ task.assignee__username || 'Housekeeping' }}</span>
        </div>
      </div>
    </section>

    <!-- Modal: Request Inspection with Notes -->
    <div
      v-if="inspectionTask"
      class="fixed inset-0 z-50 bg-[var(--scrim)] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      @click.self="inspectionTask = null"
    >
      <div class="card p-6 w-full max-w-md space-y-4">
        <h3 class="text-xl font-serif">Request Inspection · Room {{ inspectionTask.room__number }}</h3>
        <p class="text-xs text-[var(--silt)]">Provide notes regarding room readiness before submitting for inspection.</p>
        <textarea
          v-model="inspectionNotes"
          class="field w-full h-24 text-xs normal-case"
          placeholder="e.g. Bed linen replaced, bathroom sanitized, supplies restocked..."
        />
        <div class="flex justify-end gap-2 pt-2">
          <button class="btn-secondary text-xs" @click="inspectionTask = null">Cancel</button>
          <button class="btn text-xs" :disabled="busy" @click="submitInspection">
            Submit for Inspection →
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: Report Maintenance Issue -->
    <div
      v-if="showMaintenanceModal"
      class="fixed inset-0 z-50 bg-[var(--scrim)] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      @click.self="showMaintenanceModal = false"
    >
      <div class="card p-6 w-full max-w-md space-y-4">
        <h3 class="text-xl font-serif">Report Maintenance Ticket</h3>
        <p class="text-xs text-[var(--silt)]">Flag damaged or malfunctioning equipment to take the room out of service.</p>

        <div>
          <label class="label text-[10px]">Select Room</label>
          <select v-model="maintRoomId" class="field text-xs w-full mt-1">
            <option value="">Select room…</option>
            <option v-for="rm in rooms.data.value || []" :key="rm.id" :value="rm.id">
              Room {{ rm.number }} ({{ rm.type }})
            </option>
          </select>
        </div>

        <div>
          <label class="label text-[10px]">Priority Level</label>
          <select v-model="maintPriority" class="field text-xs w-full mt-1">
            <option value="NORMAL">Normal</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent (Immediate block)</option>
          </select>
        </div>

        <div>
          <label class="label text-[10px]">Issue Description</label>
          <textarea
            v-model="maintDescription"
            class="field w-full h-20 text-xs mt-1 normal-case"
            placeholder="Describe the issue (e.g. leaking faucet, air conditioner making loud noise...)"
          />
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button class="btn-secondary text-xs" @click="showMaintenanceModal = false">Cancel</button>
          <button
            class="btn text-xs"
            :disabled="busy || !maintRoomId || !maintDescription.trim()"
            @click="submitMaintenance"
          >
            Create Ticket & Block Room
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
