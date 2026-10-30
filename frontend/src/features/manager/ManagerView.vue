<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import PortalLayout from '../../layouts/PortalLayout.vue'
import ManagerDashboard from './ManagerDashboard.vue'
import Notice from '../../components/Notice.vue'
import { staffApi, queryClient } from '../../services/api'
import type { StaffUser } from '../../types'

const user = ref<StaffUser | null>(null)
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

const identity = useQuery({ queryKey: ['auth', 'me', 'manager'], queryFn: () => staffApi<StaffUser>('/auth/me') })
watch(identity.data, current => {
  if (current && 'username' in current) user.value = current
}, { immediate: true })

const isManagerRole = computed(() => ['ADMIN', 'MANAGER', 'ACCOUNTANT'].includes(user.value?.role || ''))

async function signIn() {
  error.value = ''
  busy.value = true
  try {
    const account = await staffApi<StaffUser>('/auth/login', { username: username.value, password: password.value })
    password.value = ''
    queryClient.clear()
    user.value = account
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

async function signOut() {
  try {
    await staffApi('/auth/logout', {})
    user.value = null
    queryClient.clear()
  } catch (caught) {
    error.value = String(caught)
  }
}
</script>

<template>
  <PortalLayout area="staff">
    <div v-if="identity.isPending.value" role="status" class="space-y-4">
      <p>Checking manager session…</p>
      <div class="skeleton h-8 w-48" />
      <div class="skeleton h-32 w-full" />
    </div>

    <!-- Login -->
    <form v-else-if="!user" class="card portal-login p-8 max-w-md mx-auto space-y-5" @submit.prevent="signIn">
      <p class="label">Management portal</p>
      <h1 class="text-3xl font-serif">Executive sign in</h1>
      <input v-model="username" class="field" placeholder="Username" aria-label="Username" required />
      <input v-model="password" class="field" placeholder="Password" aria-label="Password" type="password" required />
      <button class="btn w-full" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
      <Notice :message="error" />
    </form>

    <!-- Role Guard -->
    <div v-else-if="!isManagerRole" class="card p-8 max-w-xl mx-auto space-y-4">
      <h1 class="text-3xl font-serif">Management access required</h1>
      <p class="text-sm text-[var(--muted)]">Your staff role ({{ user.role }}) does not have permission to view executive management dashboards and financial reports.</p>
      <RouterLink class="btn inline-block" to="/staff">Go to staff operations</RouterLink>
    </div>

    <!-- Dashboard -->
    <div v-else class="space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
        <div>
          <span class="label uppercase tracking-widest text-xs">Hotel Management Information System</span>
          <p class="text-sm text-[var(--muted)]">Signed in as <strong>{{ user.username }}</strong> ({{ user.role }})</p>
        </div>
        <div class="flex items-center gap-3">
          <RouterLink to="/staff" class="btn-secondary text-xs">Staff Desk</RouterLink>
          <RouterLink v-if="user.role === 'ADMIN'" to="/admin" class="btn-secondary text-xs">Admin Console</RouterLink>
          <button type="button" class="btn-secondary text-xs" @click="signOut">Sign out</button>
        </div>
      </div>

      <ManagerDashboard portal="staff" :user="user" />
    </div>
  </PortalLayout>
</template>
