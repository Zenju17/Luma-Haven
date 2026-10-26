<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import QrcodeVue from 'qrcode.vue'
import { api } from '../lib/api'
import type { Booking } from '../types'

const router = useRouter()

const reference = ref('')
const email = ref('')
const code = ref('')
const sent = ref(false)
const msg = ref('')

const verifyUrl = computed(() => `${window.location.origin}/verify`)

async function submit() {
  try {
    if (!sent.value) {
      await api('/guest-access/request-otp', { reference: reference.value, email: email.value })
      sent.value = true
      msg.value = 'Check your verification message.'
    } else {
      const booking = await api<Booking>('/guest-access/verify-otp', {
        reference: reference.value,
        email: email.value,
        code: code.value,
      })
      router.push(`/booking/${booking.id}`)
    }
  } catch (e) {
    msg.value = String(e)
  }
}
</script>

<template>
  <div class="grid md:grid-cols-2 gap-10 max-w-4xl mx-auto items-center">
    <div>
      <p class="label">Your stay, your way</p>
      <h1 class="text-4xl">Welcome back.</h1>
      <p class="mt-4 text-[#6a7f73]">
        Use your booking reference and email to request a one-time code. For local development, find
        your code in the backend container logs.
      </p>
      <div class="card p-5 mt-8 inline-block text-center">
        <QrcodeVue :value="verifyUrl" :size="150" />
        <p class="text-xs mt-3">Lobby booking verification QR</p>
      </div>
    </div>

    <form class="card p-8 space-y-5" @submit.prevent="submit">
      <h2 class="text-2xl">Verify your booking</h2>
      <label class="block">
        <span class="label">Booking reference</span>
        <input v-model="reference" class="field" required />
      </label>
      <label class="block">
        <span class="label">Email address</span>
        <input v-model="email" class="field" required type="email" />
      </label>
      <label v-if="sent" class="block">
        <span class="label">Six-digit code</span>
        <input
          v-model="code"
          class="field"
          required
          inputmode="numeric"
          maxlength="6"
        />
      </label>
      <button class="btn w-full">
        {{ sent ? 'Verify and continue' : 'Send verification code' }}
      </button>
      <p role="status" class="text-sm">{{ msg }}</p>
    </form>
  </div>
</template>
