import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

export type AuthStatus = 'anonymous' | 'authenticated';

export const useAuthStore = defineStore('auth', () => {
  const status = ref<AuthStatus>('anonymous');
  const displayName = ref('匿名用户');
  const isAuthenticated = computed(() => status.value === 'authenticated');

  function reflectSession(nextStatus: AuthStatus, nextDisplayName?: string): void {
    status.value = nextStatus;
    displayName.value = nextDisplayName?.trim() || '匿名用户';
  }

  return { displayName, isAuthenticated, reflectSession, status };
});
