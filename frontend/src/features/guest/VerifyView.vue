<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import QrcodeVue from 'qrcode.vue'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import type { Booking } from '../../types'

const router = useRouter()
const reference = ref('')
const email = ref('')
const code = ref('')
const sent = ref(false)
const message = ref('')
const failed = ref(false)
const pending = ref(false)
const lobbyUrl = `${window.location.origin}/verify`

async function verify() {
  pending.value = true
  message.value = ''
  failed.value = false
  try {
    if (!sent.value) {
      await api('/guest-access/request-otp', { reference: reference.value, email: email.value })
      sent.value = true
      message.value = 'Check your verification message.'
    } else {
      const booking = await api<Booking>('/guest-access/verify-otp', {
        reference: reference.value, email: email.value, code: code.value,
      })
      await router.push(`/booking/${booking.id}`)
    }
  } catch (error) {
    failed.value = true
    message.value = String(error)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <SiteLayout>
    <div class="grid md:grid-cols-2 gap-10 max-w-4xl mx-auto items-center animate-[fadeIn_0.4s_ease-out]">
      <div>
        <h1 class="text-4xl text-[var(--brand-text)]">Find your booking.</h1>
        <p class="mt-4 text-[var(--muted)]">Enter your booking reference and email to request a one-time code. For local development, find the code in the backend container logs.</p>
        <div class="card qr-frame p-5 mt-8 inline-block text-center shadow-md">
          <div class="p-2 bg-white rounded-lg inline-block">
            <QrcodeVue :value="lobbyUrl" :size="150" level="M" render-as="svg" />
          </div>
          <p class="text-xs mt-3 text-[var(--muted)]">Lobby booking verification QR</p>
        </div>
      </div>
      <form class="card verification-form p-8 space-y-5" @submit.prevent="verify">
        <div class="flex items-center gap-3 pb-2 border-b border-[var(--line)]">
          <img src="/images/luma-haven/branding/logo.png" alt="Luma Haven Logo" class="w-8 h-8 object-contain" />
          <h2 class="text-2xl text-[var(--brand-text)] serif">Verify your booking</h2>
        </div>
        <label class="block"><span class="label">Booking reference</span><input v-model="reference" class="field" required /></label>
        <label class="block"><span class="label">Email address</span><input v-model="email" class="field" type="email" required /></label>
        <Transition name="slide-up">
          <label v-if="sent" class="block"><span class="label">Six-digit code</span><input v-model="code" class="field" inputmode="numeric" maxlength="6" required /></label>
        </Transition>
        <button class="btn w-full" :disabled="pending">{{ sent ? 'Verify and continue' : 'Send verification code' }}</button>
        <Notice :message="message" :status="!failed" />
      </form>
    </div>
  </SiteLayout>
</template>
