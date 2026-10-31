<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { api, staffApi, adminApi, queryClient } from '../../services/api'
import type { VisualAsset, Room } from '../../types'

const props = withDefaults(defineProps<{
  portal?: 'staff' | 'admin'
}>(), {
  portal: 'staff',
})

const selectedCategory = ref<string>('ALL')
const activeModal = ref<'edit' | 'upload' | null>(null)
const editingAsset = ref<VisualAsset | null>(null)
const errorNotice = ref('')
const successNotice = ref('')
const busy = ref(false)

// Edit form state
const editForm = ref({
  title: '',
  caption: '',
  alt_text: '',
  category: 'GALLERY',
  room_type_id: null as number | null,
  display_order: 1,
  is_active: true,
  source_type: 'CONCEPT' as 'CONCEPT' | 'VERIFIED' | 'PLACEHOLDER',
  facility_claim: '',
})

// Upload form state
const uploadForm = ref({
  file: null as File | null,
  previewUrl: '',
  title: '',
  caption: '',
  alt_text: '',
  category: 'GALLERY',
  room_type_id: null as number | null,
  display_order: 1,
  is_active: true,
  source_type: 'CONCEPT' as 'CONCEPT' | 'VERIFIED' | 'PLACEHOLDER',
  facility_claim: '',
})

const fetchAssets = () => {
  const path = props.portal === 'admin' ? '/admin/visual-assets' : '/staff/visual-assets'
  return props.portal === 'admin' ? adminApi<VisualAsset[]>(path) : staffApi<VisualAsset[]>(path)
}

const assetsQuery = useQuery({
  queryKey: ['staff-visual-assets', props.portal],
  queryFn: fetchAssets,
})

const roomsQuery = useQuery({
  queryKey: ['rooms'],
  queryFn: () => api<Room[]>('/rooms'),
})

// Unique room types from rooms list
const roomTypes = computed(() => {
  const rooms = roomsQuery.data.value || []
  const seen = new Set<string>()
  const list: { id: number; name: string }[] = []
  for (const r of rooms) {
    if (!seen.has(r.type)) {
      seen.add(r.type)
      list.push({ id: r.id, name: r.type })
    }
  }
  return list
})

const filteredAssets = computed(() => {
  const items = assetsQuery.data.value || []
  if (selectedCategory.value === 'ALL') return items
  return items.filter(a => a.category === selectedCategory.value)
})

const categories = [
  { id: 'ALL', label: 'All Assets' },
  { id: 'HERO', label: 'Hero' },
  { id: 'BRANDING', label: 'Branding & Logo' },
  { id: 'GALLERY', label: 'Gallery' },
  { id: 'ROOM_TYPE', label: 'Room Types' },
  { id: 'EXPERIENCE', label: 'Experience' },
  { id: 'OTHER', label: 'Other' },
]

function openEdit(asset: VisualAsset) {
  editingAsset.value = asset
  editForm.value = {
    title: asset.title,
    caption: asset.caption,
    alt_text: asset.alt_text,
    category: asset.category,
    room_type_id: asset.room_type_id,
    display_order: asset.display_order,
    is_active: asset.is_active,
    source_type: asset.source_type,
    facility_claim: asset.facility_claim,
  }
  errorNotice.value = ''
  activeModal.value = 'edit'
}

function openUpload() {
  uploadForm.value = {
    file: null,
    previewUrl: '',
    title: '',
    caption: '',
    alt_text: '',
    category: selectedCategory.value !== 'ALL' ? selectedCategory.value : 'GALLERY',
    room_type_id: null,
    display_order: 1,
    is_active: true,
    source_type: 'CONCEPT',
    facility_claim: '',
  }
  errorNotice.value = ''
  activeModal.value = 'upload'
}

function closeModal() {
  activeModal.value = null
  editingAsset.value = null
  if (uploadForm.value.previewUrl) {
    URL.revokeObjectURL(uploadForm.value.previewUrl)
    uploadForm.value.previewUrl = ''
  }
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const file = input.files[0]
    uploadForm.value.file = file
    uploadForm.value.previewUrl = URL.createObjectURL(file)
    if (!uploadForm.value.title) {
      uploadForm.value.title = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ')
    }
    if (!uploadForm.value.alt_text) {
      uploadForm.value.alt_text = `Luma Haven ${uploadForm.value.title}`
    }
  }
}

async function saveEdit() {
  if (!editingAsset.value) return
  busy.value = true
  errorNotice.value = ''
  try {
    const path = props.portal === 'admin'
      ? `/admin/visual-assets/${editingAsset.value.id}`
      : `/staff/visual-assets/${editingAsset.value.id}`
    const fn = props.portal === 'admin' ? adminApi : staffApi

    await fn(path, editForm.value, 'PATCH')

    successNotice.value = `Asset "${editForm.value.title}" updated successfully.`
    closeModal()
    await assetsQuery.refetch()
    await queryClient.invalidateQueries({ queryKey: ['visual-assets'] })
  } catch (err) {
    errorNotice.value = String(err)
  } finally {
    busy.value = false
  }
}

async function toggleActive(asset: VisualAsset) {
  busy.value = true
  errorNotice.value = ''
  try {
    const path = props.portal === 'admin'
      ? `/admin/visual-assets/${asset.id}`
      : `/staff/visual-assets/${asset.id}`
    const fn = props.portal === 'admin' ? adminApi : staffApi

    await fn(path, { is_active: !asset.is_active }, 'PATCH')
    await assetsQuery.refetch()
    await queryClient.invalidateQueries({ queryKey: ['visual-assets'] })
  } catch (err) {
    errorNotice.value = String(err)
  } finally {
    busy.value = false
  }
}

async function deleteAsset(asset: VisualAsset) {
  if (!confirm(`Are you sure you want to permanently delete "${asset.title}"?`)) return
  busy.value = true
  errorNotice.value = ''
  try {
    const path = props.portal === 'admin'
      ? `/admin/visual-assets/${asset.id}`
      : `/staff/visual-assets/${asset.id}`
    const fn = props.portal === 'admin' ? adminApi : staffApi

    await fn(path, {}, 'DELETE')
    successNotice.value = `Asset "${asset.title}" deleted.`
    await assetsQuery.refetch()
    await queryClient.invalidateQueries({ queryKey: ['visual-assets'] })
  } catch (err) {
    errorNotice.value = String(err)
  } finally {
    busy.value = false
  }
}

async function submitUpload() {
  if (!uploadForm.value.file) {
    errorNotice.value = 'Please choose an image file to upload.'
    return
  }
  busy.value = true
  errorNotice.value = ''
  try {
    const formData = new FormData()
    formData.append('image', uploadForm.value.file)
    formData.append('title', uploadForm.value.title)
    formData.append('caption', uploadForm.value.caption)
    formData.append('alt_text', uploadForm.value.alt_text)
    formData.append('category', uploadForm.value.category)
    if (uploadForm.value.room_type_id) {
      formData.append('room_type_id', String(uploadForm.value.room_type_id))
    }
    formData.append('display_order', String(uploadForm.value.display_order))
    formData.append('is_active', String(uploadForm.value.is_active))
    formData.append('source_type', uploadForm.value.source_type)
    formData.append('facility_claim', uploadForm.value.facility_claim)

    const path = props.portal === 'admin' ? '/admin/visual-assets' : '/staff/visual-assets'
    const fn = props.portal === 'admin' ? adminApi : staffApi

    await fn(path, formData, 'POST')

    successNotice.value = `New visual asset "${uploadForm.value.title}" uploaded successfully.`
    closeModal()
    await assetsQuery.refetch()
    await queryClient.invalidateQueries({ queryKey: ['visual-assets'] })
  } catch (err) {
    errorNotice.value = String(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header Controls -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--glass-border)]">
      <div>
        <h2 class="serif text-2xl font-semibold text-[var(--brand-text)]">
          Visual Assets &amp; Media Management
        </h2>
        <p class="text-xs sm:text-sm text-[var(--muted)]">
          Manage homepage concepts, gallery slides, and room type photography. Update captions, assign room types, or upload replacements.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="btn text-xs font-semibold px-4 py-2 flex items-center gap-2 shadow-xs"
          @click="openUpload"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Upload Asset
        </button>
      </div>
    </div>

    <!-- Notices -->
    <Notice v-if="errorNotice" :message="errorNotice" />
    <div v-if="successNotice" class="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 text-sm flex items-center justify-between">
      <span>{{ successNotice }}</span>
      <button type="button" class="text-xs opacity-70 hover:opacity-100" @click="successNotice = ''">Dismiss</button>
    </div>

    <!-- Category Filter Tabs -->
    <div class="flex flex-wrap items-center gap-2 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330] pb-2">
      <button
        v-for="cat in categories"
        :key="cat.id"
        type="button"
        :class="[
          'px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
          selectedCategory === cat.id
            ? 'bg-[var(--brass)] text-stone-900 font-semibold shadow-xs'
            : 'bg-[var(--surface-muted)] text-[var(--muted)] hover:text-[var(--brand-text)]',
        ]"
        @click="selectedCategory = cat.id"
      >
        {{ cat.label }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="assetsQuery.isPending.value" role="status" class="py-12 space-y-4 text-center">
      <p class="text-sm text-[var(--muted)]">Loading visual assets…</p>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="h-56 skeleton rounded-xl" />
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredAssets.length === 0"
      class="card p-12 text-center space-y-3 rounded-2xl border border-[var(--glass-border)]"
    >
      <p class="serif text-xl font-medium text-[var(--brand-text)]">
        No assets found in category "{{ selectedCategory }}".
      </p>
      <p class="text-xs sm:text-sm text-[var(--muted)]">
        Click "Upload Asset" above to add new imagery.
      </p>
    </div>

    <!-- Asset Cards Grid -->
    <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <article
        v-for="asset in filteredAssets"
        :key="asset.id"
        class="card rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)] overflow-hidden shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
      >
        <!-- Thumbnail & Badges -->
        <div class="relative aspect-[16/10] bg-[var(--deep)] overflow-hidden border-b border-[var(--glass-border)]">
          <img
            :src="asset.image_url"
            :alt="asset.alt_text"
            class="w-full h-full object-cover object-center"
            loading="lazy"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-[var(--deep)]/50 via-transparent to-transparent pointer-events-none" />

          <!-- Category Badge -->
          <span class="absolute top-3 left-3 px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider uppercase bg-[var(--deep)]/90 text-stone-200 border border-[var(--glass-border)] backdrop-blur-xs">
            {{ asset.category }}
          </span>

          <!-- Source Type / Concept Badge -->
          <span
            v-if="asset.source_type === 'CONCEPT'"
            class="absolute top-3 right-3 px-2 py-0.5 rounded text-[10px] font-medium bg-black/70 text-[#d9b87f] border border-[#d9b87f]/30 backdrop-blur-xs"
          >
            Design Concept
          </span>
          <span
            v-else
            class="absolute top-3 right-3 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-950/80 text-emerald-200 border border-emerald-500/30 backdrop-blur-xs"
          >
            Verified Photo
          </span>

          <!-- Active Toggle Pill on image -->
          <button
            type="button"
            :class="[
              'absolute bottom-3 left-3 px-2.5 py-0.5 rounded-full text-[11px] font-semibold transition-colors flex items-center gap-1.5 shadow-xs',
              asset.is_active
                ? 'bg-emerald-600 text-white'
                : 'bg-stone-800 text-stone-400 border border-stone-600',
            ]"
            :title="asset.is_active ? 'Click to deactivate' : 'Click to activate'"
            @click="toggleActive(asset)"
          >
            <span :class="['w-1.5 h-1.5 rounded-full', asset.is_active ? 'bg-white' : 'bg-stone-500']" />
            {{ asset.is_active ? 'Active' : 'Draft / Hidden' }}
          </button>

          <!-- Order Tag -->
          <span class="absolute bottom-3 right-3 px-2 py-0.5 rounded text-[10px] font-mono bg-black/60 text-stone-300 backdrop-blur-xs">
            Order #{{ asset.display_order }}
          </span>
        </div>

        <!-- Body & Details -->
        <div class="p-5 grow flex flex-col justify-between space-y-4">
          <div class="space-y-2">
            <h3 class="serif text-lg font-medium text-[var(--brand-text)] line-clamp-1">
              {{ asset.title }}
            </h3>

            <p class="text-xs text-[var(--muted)] line-clamp-2">
              {{ asset.caption || 'No caption provided.' }}
            </p>

            <!-- Metadata info -->
            <div class="pt-2 border-t border-[var(--line,#e2e8e0)] dark:border-[#1a3330] space-y-1 text-[11px] text-[var(--muted)]">
              <p v-if="asset.room_type_name" class="flex items-center gap-1.5">
                <strong class="text-[var(--brand-text)]">Room:</strong> {{ asset.room_type_name }}
              </p>
              <p v-else-if="asset.category === 'ROOM_TYPE'" class="text-amber-600 dark:text-amber-400 font-semibold">
                Unassigned Room Type
              </p>
              <p v-if="asset.facility_claim" class="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                <span>⚠️</span> Claim: {{ asset.facility_claim }}
              </p>
              <p class="font-mono text-[10px] text-[var(--muted)] truncate">
                {{ asset.original_filename }} ({{ asset.width }}×{{ asset.height }} · {{ Math.round(asset.file_size_bytes / 1024) }} KB)
              </p>
            </div>
          </div>

          <!-- Actions -->
          <div class="pt-3 border-t border-[var(--line,#e2e8e0)] dark:border-[#1a3330] flex items-center justify-between gap-2">
            <button
              type="button"
              class="btn-secondary text-xs font-semibold px-3 py-1.5"
              @click="openEdit(asset)"
            >
              Edit Details
            </button>

            <button
              type="button"
              class="text-xs text-rose-500 hover:text-rose-700 dark:hover:text-rose-400 transition-colors p-1"
              title="Delete asset"
              @click="deleteAsset(asset)"
            >
              Delete
            </button>
          </div>
        </div>
      </article>
    </div>

    <!-- Edit Modal -->
    <div
      v-if="activeModal === 'edit' && editingAsset"
      class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-modal-title"
    >
      <div class="card p-6 sm:p-8 max-w-xl w-full rounded-2xl bg-[var(--surface-raised)] border border-[var(--glass-border)] shadow-2xl space-y-5 my-8">
        <div class="flex items-center justify-between pb-3 border-b border-[var(--glass-border)]">
          <h3 id="edit-modal-title" class="serif text-xl font-semibold text-[var(--brand-text)]">
            Edit Visual Asset
          </h3>
          <button type="button" class="text-lg text-[var(--muted)] hover:text-[var(--brand-text)]" @click="closeModal">✕</button>
        </div>

        <form class="space-y-4" @submit.prevent="saveEdit">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Title</label>
            <input v-model="editForm.title" class="field w-full" required />
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Caption</label>
            <textarea v-model="editForm.caption" class="field w-full h-20 text-sm" placeholder="Atmospheric description or guest note…" />
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Alt Text (Accessibility)</label>
            <input v-model="editForm.alt_text" class="field w-full" required />
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Category</label>
              <select v-model="editForm.category" class="field w-full">
                <option value="BRANDING">Branding &amp; Logo</option>
                <option value="HERO">Homepage Hero</option>
                <option value="GALLERY">Homepage Gallery</option>
                <option value="ROOM_TYPE">Room Type Gallery</option>
                <option value="EXPERIENCE">Experience &amp; Feature</option>
                <option value="OTHER">Other</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Assigned Room Type</label>
              <select v-model="editForm.room_type_id" class="field w-full">
                <option :value="null">(Unassigned)</option>
                <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">
                  {{ rt.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Display Order</label>
              <input v-model.number="editForm.display_order" type="number" min="0" class="field w-full" />
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Source Type</label>
              <select v-model="editForm.source_type" class="field w-full">
                <option value="CONCEPT">AI Concept Visualization</option>
                <option value="VERIFIED">Verified Hotel Photograph</option>
                <option value="PLACEHOLDER">Graphic Placeholder</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">
              Facility Claim Note (if unverified)
            </label>
            <input
              v-model="editForm.facility_claim"
              class="field w-full text-xs"
              placeholder="e.g. Unverified Rooftop Pool Concept"
            />
          </div>

          <div class="flex items-center gap-3 pt-2">
            <input id="edit-active" v-model="editForm.is_active" type="checkbox" class="w-4 h-4 rounded text-[var(--brass)]" />
            <label for="edit-active" class="text-sm font-medium text-[var(--brand-text)] cursor-pointer">
              Active (Visible on public guest pages)
            </label>
          </div>

          <Notice v-if="errorNotice" :message="errorNotice" />

          <div class="pt-4 border-t border-[var(--glass-border)] flex items-center justify-end gap-3">
            <button type="button" class="btn-secondary text-xs px-4 py-2" @click="closeModal">Cancel</button>
            <button type="submit" class="btn text-xs font-semibold px-5 py-2" :disabled="busy">
              {{ busy ? 'Saving…' : 'Save Changes' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Upload Modal -->
    <div
      v-if="activeModal === 'upload'"
      class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-modal-title"
    >
      <div class="card p-6 sm:p-8 max-w-xl w-full rounded-2xl bg-[var(--surface-raised)] border border-[var(--glass-border)] shadow-2xl space-y-5 my-8">
        <div class="flex items-center justify-between pb-3 border-b border-[var(--glass-border)]">
          <h3 id="upload-modal-title" class="serif text-xl font-semibold text-[var(--brand-text)]">
            Upload Visual Asset
          </h3>
          <button type="button" class="text-lg text-[var(--muted)] hover:text-[var(--brand-text)]" @click="closeModal">✕</button>
        </div>

        <form class="space-y-4" @submit.prevent="submitUpload">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">
              Image File (.png, .jpg, .webp up to 10MB)
            </label>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              class="field w-full text-xs"
              required
              @change="onFileSelect"
            />
          </div>

          <!-- Image Preview -->
          <div v-if="uploadForm.previewUrl" class="aspect-[16/9] w-full rounded-xl overflow-hidden bg-black/30 border border-[var(--glass-border)] relative">
            <img :src="uploadForm.previewUrl" alt="Upload preview" class="w-full h-full object-cover" />
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Title</label>
            <input v-model="uploadForm.title" class="field w-full" placeholder="e.g. Courtyard Twilight" required />
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Caption</label>
            <textarea v-model="uploadForm.caption" class="field w-full h-20 text-sm" placeholder="Description of space…" />
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Alt Text</label>
            <input v-model="uploadForm.alt_text" class="field w-full" required />
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Category</label>
              <select v-model="uploadForm.category" class="field w-full">
                <option value="GALLERY">Homepage Gallery</option>
                <option value="HERO">Homepage Hero</option>
                <option value="BRANDING">Branding &amp; Logo</option>
                <option value="ROOM_TYPE">Room Type Gallery</option>
                <option value="EXPERIENCE">Experience &amp; Feature</option>
                <option value="OTHER">Other</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Assigned Room Type</label>
              <select v-model="uploadForm.room_type_id" class="field w-full">
                <option :value="null">(Unassigned)</option>
                <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">
                  {{ rt.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Display Order</label>
              <input v-model.number="uploadForm.display_order" type="number" min="0" class="field w-full" />
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">Source Type</label>
              <select v-model="uploadForm.source_type" class="field w-full">
                <option value="CONCEPT">AI Concept Visualization</option>
                <option value="VERIFIED">Verified Hotel Photograph</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">
              Facility Claim Note (if unverified)
            </label>
            <input
              v-model="uploadForm.facility_claim"
              class="field w-full text-xs"
              placeholder="e.g. Unverified Amenity Concept"
            />
          </div>

          <div class="flex items-center gap-3 pt-2">
            <input id="upload-active" v-model="uploadForm.is_active" type="checkbox" class="w-4 h-4 rounded text-[var(--brass)]" />
            <label for="upload-active" class="text-sm font-medium text-[var(--brand-text)] cursor-pointer">
              Active immediately
            </label>
          </div>

          <Notice v-if="errorNotice" :message="errorNotice" />

          <div class="pt-4 border-t border-[var(--glass-border)] flex items-center justify-end gap-3">
            <button type="button" class="btn-secondary text-xs px-4 py-2" @click="closeModal">Cancel</button>
            <button type="submit" class="btn text-xs font-semibold px-5 py-2" :disabled="busy">
              {{ busy ? 'Uploading…' : 'Upload & Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
