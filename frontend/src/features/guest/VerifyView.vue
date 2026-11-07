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

async function resend() {
  if (pending.value) return
  pending.value = true
  message.value = ''
  failed.value = false
  try {
    await api('/guest-access/request-otp', { reference: reference.value, email: email.value })
    message.value = 'A fresh verification code has been sent to your email.'
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
    <div class="vf">
      <div class="vf-intro">
        <h1 class="vf-title">Find your booking</h1>
        <p>Enter your booking reference and email to request a one-time code. You can also verify in person at reception.</p>
        <div class="vf-qr">
          <QrcodeVue :value="lobbyUrl" :size="150" level="M" render-as="svg" />
          <p>Lobby booking verification QR</p>
        </div>
      </div>
      <form class="vf-form" @submit.prevent="verify">
        <h2>Verify your booking</h2>
        <label class="block"><span class="vf-label">Booking reference</span><input v-model="reference" class="field" required /></label>
        <label class="block"><span class="vf-label">Email address</span><input v-model="email" class="field" type="email" required /></label>
        <Transition name="slide-up">
          <div v-if="sent" class="space-y-2">
            <label class="block"><span class="vf-label">Six-digit code</span><input v-model="code" class="field" inputmode="numeric" maxlength="6" required /></label>
            <div class="vf-resend">
              <span>Didn't receive the email?</span>
              <button type="button" :disabled="pending" @click="resend">Resend code</button>
            </div>
          </div>
        </Transition>
        <button class="btn w-full" :disabled="pending">{{ sent ? 'Verify and continue' : 'Send verification code' }}</button>
        <Notice :message="message" :status="!failed" />
      </form>
    </div>
  </SiteLayout>
</template>

<style scoped>
.vf { display: grid; gap: 2rem; max-width: 64rem; margin: 1.5rem auto 2rem; }
.vf-intro { display: grid; gap: 1rem; align-content: start; }
.vf-intro p { color: var(--silt); }
.vf-title { font-size: 3.0625rem; color: var(--river); }
.vf-qr { justify-self: start; padding: 1rem; background: var(--paper); border: 1px solid var(--rule); border-radius: var(--radius-photo); text-align: center; }
.vf-qr :deep(svg) { background: #fff; padding: 8px; border-radius: 8px; }
.vf-qr p { font-size: .875rem; margin-top: .5rem; }
.vf-form { display: grid; gap: 1.25rem; padding: 1.5rem; max-width: 560px; background: var(--paper); border: 1px solid var(--rule); border-radius: var(--radius-panel); }
.vf-form h2 { font-size: 1.9375rem; color: var(--river); }
.vf-label { display: block; margin-bottom: .35rem; color: var(--river); font-size: .875rem; font-weight: 500; }
.vf-resend { display: flex; justify-content: space-between; align-items: center; color: var(--silt); font-size: .875rem; }
.vf-resend button { min-height: 44px; text-decoration: underline; color: var(--river); font-weight: 500; }
@media (min-width: 900px) { .vf { grid-template-columns: 1fr 1fr; gap: 4rem; align-items: start; } }
</style>
