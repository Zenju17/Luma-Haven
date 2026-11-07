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

// Images whose long edge is below this look soft in lightboxes on HiDPI/phone screens.
const MIN_SHARP_EDGE_PX = 1600
const uploadDims = ref<{ width: number; height: number } | null>(null)
const isLowRes = (width: number, height: number) => width > 0 && Math.max(width, height) < MIN_SHARP_EDGE_PX

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
    uploadDims.value = null
    const probe = new Image()
    probe.onload = () => { uploadDims.value = { width: probe.naturalWidth, height: probe.naturalHeight } }
    probe.src = uploadForm.value.previewUrl
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
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--rule)]">
      <div>
        <h2 class="serif text-2xl font-semibold text-[var(--river)]">
          Visual Assets &amp; Media Management
        </h2>
        <p class="text-xs sm:text-sm text-[var(--silt)]">
          Manage homepage concepts, gallery slides, and room type photography. Update captions, assign room types, or upload replacements.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="btn text-xs font-semibold px-4 py-2 flex items-center gap-2"
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
    <div v-if="successNotice" class="p-4 rounded-xl bg-[var(--status-available)]/10 border border-[var(--status-available)]/30 text-[var(--status-available)] text-sm flex items-center justify-between">
      <span>{{ successNotice }}</span>
      <button type="button" class="text-xs opacity-70 hover:opacity-100" @click="successNotice = ''">Dismiss</button>
    </div>

    <!-- Category Filter Tabs -->
    <div class="flex flex-wrap items-center gap-2 border-b border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)] pb-2">
      <button
        v-for="cat in categories"
        :key="cat.id"
        type="button"
        :class="[
 'px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
 selectedCategory === cat.id
            ? 'bg-[var(--river)] text-[var(--on-river)] font-semibold'
            : 'bg-[var(--sunk)] text-[var(--silt)] hover:text-[var(--river)]',
        ]"
        @click="selectedCategory = cat.id"
      >
        {{ cat.label }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="assetsQuery.isPending.value" role="status" class="py-12 space-y-4 text-center">
      <p class="text-sm text-[var(--silt)]">Loading visual assets…</p>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="h-56 skeleton rounded-xl" />
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredAssets.length === 0"
      class="card p-12 text-center space-y-3 rounded-2xl border border-[var(--rule)]"
    >
      <p class="serif text-xl font-medium text-[var(--river)]">
        No assets found in category "{{ selectedCategory }}".
      </p>
      <p class="text-xs sm:text-sm text-[var(--silt)]">
        Click "Upload Asset" above to add new imagery.
      </p>
    </div>

    <!-- Asset Cards Grid -->
    <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <article
        v-for="asset in filteredAssets"
        :key="asset.id"
        class="card rounded-2xl border border-[var(--rule)] bg-[var(--paper)] overflow-hidden transition-all flex flex-col justify-between"
      >
        <!-- Thumbnail & Badges -->
        <div class="relative aspect-[16/10] bg-[var(--river)] overflow-hidden border-b border-[var(--rule)]">
          <img
            :src="asset.image_url"
            :alt="asset.alt_text"
            class="w-full h-full object-cover object-center"
            loading="lazy"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-[var(--river)]/50 via-transparent to-transparent pointer-events-none" />

          <!-- Category Badge -->
          <span class="absolute top-3 left-3 px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--paper)] text-[var(--river)]">
            {{ asset.category }}
          </span>

          <!-- Source Type / Concept Badge -->
          <span
            v-if="asset.source_type === 'CONCEPT'"
            class="absolute top-3 right-3 px-2 py-0.5 rounded text-[10px] font-medium bg-black/70 text-[color:var(--laterite)] border border-[color:var(--laterite)]/30"
          >
            Design Concept
          </span>
          <span
            v-else
            class="absolute top-3 right-3 px-2 py-0.5 rounded text-[10px] font-medium bg-[var(--paper)] text-[var(--status-available)] border border-[var(--status-available)]/30"
          >
            Verified Photo
          </span>

          <!-- Active Toggle Pill on image -->
          <button
            type="button"
            :class="[
 'absolute bottom-3 left-3 px-2.5 py-0.5 rounded-full text-[11px] font-semibold transition-colors flex items-center gap-1.5',
 asset.is_active
                ? 'bg-[var(--status-available)] text-white'
                : 'bg-[var(--paper)] text-[var(--silt)] border border-[var(--rule)]',
            ]"
            :title="asset.is_active ? 'Click to deactivate' : 'Click to activate'"
            @click="toggleActive(asset)"
          >
            <span :class="['w-1.5 h-1.5 rounded-full', asset.is_active ? 'bg-white' : 'bg-[var(--silt)]']" />
            {{ asset.is_active ? 'Active' : 'Draft / Hidden' }}
          </button>

          <!-- Order Tag -->
          <span class="absolute bottom-3 right-3 px-2 py-0.5 rounded text-[10px] tabular-nums bg-black/60 text-white">
            Order #{{ asset.display_order }}
          </span>
        </div>

        <!-- Body & Details -->
        <div class="p-5 grow flex flex-col justify-between space-y-4">
          <div class="space-y-2">
            <h3 class="serif text-lg font-medium text-[var(--river)] line-clamp-1">
              {{ asset.title }}
            </h3>

            <p class="text-xs text-[var(--silt)] line-clamp-2">
              {{ asset.caption || 'No caption provided.' }}
            </p>

            <!-- Metadata info -->
            <div class="pt-2 border-t border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)] space-y-1 text-[11px] text-[var(--silt)]">
              <p v-if="asset.room_type_name" class="flex items-center gap-1.5">
                <strong class="text-[var(--river)]">Room:</strong> {{ asset.room_type_name }}
              </p>
              <p v-else-if="asset.category === 'ROOM_TYPE'" class="text-[var(--status-dirty)] font-semibold">
                Unassigned Room Type
              </p>
              <p v-if="asset.facility_claim" class="text-[var(--status-dirty)] flex items-center gap-1">
                <span>⚠️</span> Claim: {{ asset.facility_claim }}
              </p>
              <p v-if="isLowRes(asset.width, asset.height)" class="text-[var(--status-dirty)] font-semibold">
                ⚠️ Low resolution: will look blurry when enlarged
              </p>
              <p class="tabular-nums text-[10px] text-[var(--silt)] truncate">
                {{ asset.original_filename }} ({{ asset.width }}×{{ asset.height }} · {{ Math.round(asset.file_size_bytes / 1024) }} KB)
              </p>
            </div>
          </div>

          <!-- Actions -->
          <div class="pt-3 border-t border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)] flex items-center justify-between gap-2">
            <button
              type="button"
              class="btn-secondary text-xs font-semibold px-3 py-1.5"
              @click="openEdit(asset)"
            >
              Edit Details
            </button>

            <button
              type="button"
              class="text-xs text-[var(--status-out)] hover:text-[var(--status-out)] transition-colors p-1"
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
      class="fixed inset-0 z-50 bg-[var(--scrim)] flex items-center justify-center p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-modal-title"
    >
      <div class="card p-6 sm:p-8 max-w-xl w-full rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-[var(--shadow-float)] space-y-5 my-8">
        <div class="flex items-center justify-between pb-3 border-b border-[var(--rule)]">
          <h3 id="edit-modal-title" class="serif text-xl font-semibold text-[var(--river)]">
            Edit Visual Asset
          </h3>
          <button type="button" class="text-lg text-[var(--silt)] hover:text-[var(--river)]" @click="closeModal">✕</button>
        </div>

        <form class="space-y-4" @submit.prevent="saveEdit">
          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Title</label>
            <input v-model="editForm.title" class="field w-full" required />
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Caption</label>
            <textarea v-model="editForm.caption" class="field w-full h-20 text-sm" placeholder="Atmospheric description or guest note…" />
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Alt Text (Accessibility)</label>
            <input v-model="editForm.alt_text" class="field w-full" required />
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Category</label>
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
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Assigned Room Type</label>
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
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Display Order</label>
              <input v-model.number="editForm.display_order" type="number" min="0" class="field w-full" />
            </div>

            <div>
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Source Type</label>
              <select v-model="editForm.source_type" class="field w-full">
                <option value="CONCEPT">AI Concept Visualization</option>
                <option value="VERIFIED">Verified Hotel Photograph</option>
                <option value="PLACEHOLDER">Graphic Placeholder</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">
              Facility Claim Note (if unverified)
            </label>
            <input
              v-model="editForm.facility_claim"
              class="field w-full text-xs"
              placeholder="e.g. Unverified Rooftop Pool Concept"
            />
          </div>

          <div class="flex items-center gap-3 pt-2">
            <input id="edit-active" v-model="editForm.is_active" type="checkbox" class="w-4 h-4 rounded text-[var(--laterite)]" />
            <label for="edit-active" class="text-sm font-medium text-[var(--river)] cursor-pointer">
              Active (Visible on public guest pages)
            </label>
          </div>

          <Notice v-if="errorNotice" :message="errorNotice" />

          <div class="pt-4 border-t border-[var(--rule)] flex items-center justify-end gap-3">
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
      class="fixed inset-0 z-50 bg-[var(--scrim)] flex items-center justify-center p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-modal-title"
    >
      <div class="card p-6 sm:p-8 max-w-xl w-full rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-[var(--shadow-float)] space-y-5 my-8">
        <div class="flex items-center justify-between pb-3 border-b border-[var(--rule)]">
          <h3 id="upload-modal-title" class="serif text-xl font-semibold text-[var(--river)]">
            Upload Visual Asset
          </h3>
          <button type="button" class="text-lg text-[var(--silt)] hover:text-[var(--river)]" @click="closeModal">✕</button>
        </div>

        <form class="space-y-4" @submit.prevent="submitUpload">
          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">
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
          <div v-if="uploadForm.previewUrl" class="aspect-[16/9] w-full rounded-xl overflow-hidden bg-black/30 border border-[var(--rule)] relative">
            <img :src="uploadForm.previewUrl" alt="Upload preview" class="w-full h-full object-cover" />
          </div>
          <p
            v-if="uploadForm.previewUrl && uploadDims && isLowRes(uploadDims.width, uploadDims.height)"
            role="alert"
            class="text-xs rounded-lg px-3 py-2 bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] border border-[var(--status-dirty)]/30 "
          >
            ⚠️ This image is only {{ uploadDims.width }}×{{ uploadDims.height }} px and will look blurry when enlarged.
            Use at least {{ MIN_SHARP_EDGE_PX }} px on the long edge (2400 px recommended).
          </p>

          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Title</label>
            <input v-model="uploadForm.title" class="field w-full" placeholder="e.g. Courtyard Twilight" required />
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Caption</label>
            <textarea v-model="uploadForm.caption" class="field w-full h-20 text-sm" placeholder="Description of space…" />
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Alt Text</label>
            <input v-model="uploadForm.alt_text" class="field w-full" required />
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Category</label>
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
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Assigned Room Type</label>
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
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Display Order</label>
              <input v-model.number="uploadForm.display_order" type="number" min="0" class="field w-full" />
            </div>

            <div>
              <label class="block text-xs font-semibold text-[var(--silt)] mb-1">Source Type</label>
              <select v-model="uploadForm.source_type" class="field w-full">
                <option value="CONCEPT">AI Concept Visualization</option>
                <option value="VERIFIED">Verified Hotel Photograph</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--silt)] mb-1">
              Facility Claim Note (if unverified)
            </label>
            <input
              v-model="uploadForm.facility_claim"
              class="field w-full text-xs"
              placeholder="e.g. Unverified Amenity Concept"
            />
          </div>

          <div class="flex items-center gap-3 pt-2">
            <input id="upload-active" v-model="uploadForm.is_active" type="checkbox" class="w-4 h-4 rounded text-[var(--laterite)]" />
            <label for="upload-active" class="text-sm font-medium text-[var(--river)] cursor-pointer">
              Active immediately
            </label>
          </div>

          <Notice v-if="errorNotice" :message="errorNotice" />

          <div class="pt-4 border-t border-[var(--rule)] flex items-center justify-end gap-3">
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
