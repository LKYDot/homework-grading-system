<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import AppLayout from '@/components/AppLayout.vue'

const route = useRoute()
const isAuthPage = computed(() => ['login', 'register'].includes(route.name as string))
</script>

<template>
  <AppLayout v-if="!isAuthPage">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </AppLayout>
  <router-view v-else v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>
