<template>
  <div class="ag-logo" :class="{ light, wave, center }">
    <svg class="ag-house" viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 3.2 4.2 13.1V28h8.1v-8.2h7.4V28h8.1V13.1L16 3.2Z" :fill="light ? '#fff' : '#F96141'" />
    </svg>
    <span class="ag-word">
      Harbor
      <svg v-if="wave" class="ag-wave" viewBox="0 0 72 8" aria-hidden="true">
        <path d="M1 5c6-4 10-4 16 0s10 4 16 0 10-4 16 0 10 4 16 0" fill="none" :stroke="light ? '#fff' : '#F96141'" stroke-width="1.6" stroke-linecap="round" />
      </svg>
    </span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ light?: boolean; wave?: boolean; center?: boolean }>()
</script>
