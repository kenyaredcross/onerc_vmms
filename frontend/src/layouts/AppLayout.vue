<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': collapsed, 'sidebar-open': mobileOpen }">
    <!-- Sidebar -->
    <aside class="sidebar" :aria-label="'Navigation'">
      <!-- Sidebar header: logo + org name -->
      <div class="sidebar__head">
        <div class="sidebar__brand">
          <div class="sidebar__logo-wrap">
            <img v-if="app.logo" :src="app.logo" :alt="app.orgName" class="sidebar__logo-img" />
            <div v-else class="sidebar__logo-abbr">{{ app.orgName.slice(0,2).toUpperCase() }}</div>
          </div>
          <Transition name="label-fade">
            <span v-if="!collapsed" class="sidebar__org-name">{{ app.orgName }}</span>
          </Transition>
        </div>
      </div>

      <!-- Nav links -->
      <nav class="sidebar__nav" role="navigation">
        <router-link
          v-for="item in navItems" :key="item.to"
          :to="item.to"
          class="sidebar__item"
          :class="{ 'sidebar__item--active': isActive(item) }"
          :title="collapsed ? item.label : undefined"
          @click="mobileOpen = false"
        >
          <component :is="item.icon" :size="20" class="sidebar__item-icon" />
          <Transition name="label-fade">
            <span v-if="!collapsed" class="sidebar__item-label">{{ item.label }}</span>
          </Transition>
        </router-link>

        <div class="sidebar__divider" />

        <button class="sidebar__item sidebar__item--logout" @click="handleLogout" :title="collapsed ? 'Sign out' : undefined">
          <LogOut :size="20" class="sidebar__item-icon" />
          <Transition name="label-fade">
            <span v-if="!collapsed" class="sidebar__item-label">Sign Out</span>
          </Transition>
        </button>
      </nav>

      <!-- Collapse toggle -->
      <button class="sidebar__collapse" @click="collapsed = !collapsed" :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'">
        <ChevronLeft v-if="!collapsed" :size="18" />
        <ChevronRight v-else :size="18" />
        <Transition name="label-fade">
          <span v-if="!collapsed" class="sidebar__item-label">Collapse</span>
        </Transition>
      </button>

      <!-- Vol ID footer -->
      <div v-if="!collapsed && auth.user" class="sidebar__footer">
        <AppAvatar :name="auth.user" size="sm" />
        <div class="sidebar__user-info">
          <p class="sidebar__user-email">{{ shortEmail }}</p>
        </div>
      </div>
    </aside>

    <!-- Mobile backdrop -->
    <div class="sidebar-backdrop" @click="mobileOpen = false" />

    <!-- Main area -->
    <div class="main-area">
      <!-- Topbar -->
      <header class="topbar">
        <div class="topbar__left">
          <button class="topbar__hamburger mobile-show" @click="mobileOpen = !mobileOpen" aria-label="Open menu">
            <Menu :size="22" />
          </button>
          <h1 class="topbar__title">{{ pageTitle }}</h1>
        </div>
        <div class="topbar__right">
          <button class="topbar__icon-btn" title="Notifications">
            <Bell :size="20" />
          </button>
          <div class="topbar__user-wrap" ref="userMenuEl">
            <button class="topbar__avatar-btn" @click="userMenuOpen = !userMenuOpen">
              <AppAvatar :name="auth.user || ''" size="sm" />
            </button>
            <Transition name="dropdown">
              <div v-if="userMenuOpen" class="topbar__dropdown">
                <div class="topbar__dropdown-header">
                  <AppAvatar :name="auth.user || ''" size="md" />
                  <div>
                    <p class="topbar__dropdown-name">{{ shortEmail }}</p>
                    <p class="topbar__dropdown-role">{{ app.volunteerLabel }}</p>
                  </div>
                </div>
                <div class="topbar__dropdown-divider" />
                <router-link to="/profile" class="topbar__dropdown-item" @click="userMenuOpen = false">
                  <User :size="15" /> Profile
                </router-link>
                <button class="topbar__dropdown-item topbar__dropdown-item--danger" @click="handleLogout">
                  <LogOut :size="15" /> Sign Out
                </button>
              </div>
            </Transition>
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="page-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import {
  LayoutDashboard, User, Send, CreditCard, LogOut,
  ChevronLeft, ChevronRight, Menu, Bell,
} from 'lucide-vue-next'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'
import AppAvatar from '../components/ui/AppAvatar.vue'

const app  = useAppStore()
const auth = useAuthStore()
const route  = useRoute()
const router = useRouter()

const collapsed    = ref(false)
const mobileOpen   = ref(false)
const userMenuOpen = ref(false)
const userMenuEl   = ref(null)

onClickOutside(userMenuEl, () => { userMenuOpen.value = false })

const navItems = computed(() => [
  { to: '/dashboard',   label: 'Dashboard',              icon: LayoutDashboard },
  { to: '/profile',     label: 'My Profile',             icon: User },
  { to: '/deployments', label: 'Deployments',            icon: Send },
  ...(app.features.membership_enabled ? [{ to: '/membership', label: 'Membership', icon: CreditCard }] : []),
])

function isActive(item) {
  return route.path === item.to || route.path.startsWith(item.to + '/')
}

const pageTitle = computed(() => route.meta.title || '')
const shortEmail = computed(() => (auth.user || '').split('@')[0])

async function handleLogout() {
  userMenuOpen.value = false
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
/* === Shell === */
.app-shell {
  display: flex; min-height: 100vh;
  --sb-w: var(--sidebar-width);
}
.app-shell.sidebar-collapsed { --sb-w: var(--sidebar-collapsed-width); }

/* === Sidebar === */
.sidebar {
  width: var(--sb-w); flex-shrink: 0;
  background: var(--sidebar-bg);
  display: flex; flex-direction: column;
  position: fixed; top: 0; left: 0; bottom: 0; z-index: 200;
  transition: width var(--t-slow);
  overflow: hidden;
}

.sidebar__head { padding: 0 12px; height: var(--topbar-height); display: flex; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); flex-shrink: 0; }
.sidebar__brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.sidebar__logo-wrap { flex-shrink: 0; }
.sidebar__logo-img { height: 32px; width: 32px; object-fit: contain; border-radius: 6px; }
.sidebar__logo-abbr { width: 32px; height: 32px; background: var(--c-primary); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; color: #fff; flex-shrink: 0; }
.sidebar__org-name { font-size: 14px; font-weight: 700; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.sidebar__nav { flex: 1; padding: 10px 8px; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column; gap: 2px; }
.sidebar__item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: var(--radius-md);
  color: var(--sidebar-text); font-size: 14px; font-weight: 500;
  cursor: pointer; text-decoration: none; border: none; background: none;
  transition: background var(--t-fast), color var(--t-fast);
  white-space: nowrap; min-width: 0; width: 100%;
}
.sidebar__item:hover { background: var(--sidebar-item-hover-bg); color: var(--sidebar-text-active); }
.sidebar__item--active { background: var(--sidebar-item-active-bg); color: var(--sidebar-text-active); }
.sidebar__item-icon { flex-shrink: 0; }
.sidebar__item-label { overflow: hidden; text-overflow: ellipsis; }
.sidebar__item--logout { color: rgba(255,100,100,0.85); margin-top: 2px; }
.sidebar__item--logout:hover { background: rgba(255,50,50,0.12); color: #fca5a5; }

.sidebar__divider { height: 1px; background: rgba(255,255,255,0.1); margin: 4px 0; }

.sidebar__collapse {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 10px; margin: 0 8px 8px;
  border-radius: var(--radius-md);
  color: var(--sidebar-text); font-size: 13px; font-weight: 500;
  cursor: pointer; transition: background var(--t-fast), color var(--t-fast);
  white-space: nowrap;
}
.sidebar__collapse:hover { background: var(--sidebar-item-hover-bg); color: var(--sidebar-text-active); }

.sidebar__footer {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-top: 1px solid rgba(255,255,255,0.1);
  flex-shrink: 0; min-width: 0;
}
.sidebar__user-info { min-width: 0; }
.sidebar__user-email { font-size: 12px; color: rgba(255,255,255,0.6); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* === Backdrop (mobile) === */
.sidebar-backdrop {
  display: none; position: fixed; inset: 0; z-index: 199;
  background: rgba(0,0,0,0.5);
}

/* === Main area === */
.main-area {
  flex: 1; min-width: 0;
  margin-left: var(--sb-w);
  display: flex; flex-direction: column;
  transition: margin-left var(--t-slow);
}

/* === Topbar === */
.topbar {
  height: var(--topbar-height); background: var(--topbar-bg);
  border-bottom: 1px solid var(--topbar-border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 var(--space-6); gap: var(--space-4);
  position: sticky; top: 0; z-index: 100; flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}
.topbar__left { display: flex; align-items: center; gap: var(--space-3); }
.topbar__title { font-size: 16px; font-weight: 700; color: var(--c-text); }
.topbar__right { display: flex; align-items: center; gap: var(--space-2); }
.topbar__hamburger { display: none; color: var(--c-text); padding: 6px; border-radius: var(--radius-sm); }
.topbar__icon-btn { color: var(--c-text-secondary); padding: 7px; border-radius: var(--radius-md); transition: background var(--t-fast); }
.topbar__icon-btn:hover { background: var(--c-border-subtle); }
.topbar__avatar-btn { padding: 3px; border-radius: 50%; cursor: pointer; }
.topbar__user-wrap { position: relative; }

.topbar__dropdown {
  position: absolute; right: 0; top: calc(100% + 8px);
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  min-width: 200px; overflow: hidden; z-index: 300;
}
.topbar__dropdown-header { display: flex; align-items: center; gap: 10px; padding: 14px 14px 12px; border-bottom: 1px solid var(--c-border); }
.topbar__dropdown-name { font-size: 13px; font-weight: 600; color: var(--c-text); }
.topbar__dropdown-role { font-size: 12px; color: var(--c-text-muted); }
.topbar__dropdown-divider { height: 1px; background: var(--c-border); }
.topbar__dropdown-item {
  display: flex; align-items: center; gap: 9px;
  padding: 10px 14px; font-size: 13px; color: var(--c-text-secondary);
  text-decoration: none; cursor: pointer; width: 100%;
  transition: background var(--t-fast);
  background: none; border: none;
}
.topbar__dropdown-item:hover { background: var(--c-border-subtle); color: var(--c-text); }
.topbar__dropdown-item--danger { color: var(--c-error); }
.topbar__dropdown-item--danger:hover { background: var(--c-error-subtle); }

/* === Page content === */
.page-content { flex: 1; padding: var(--space-6); overflow-y: auto; }

/* === Animations === */
.label-fade-enter-active, .label-fade-leave-active { transition: opacity var(--t-base), transform var(--t-base); }
.label-fade-enter-from, .label-fade-leave-to { opacity: 0; transform: translateX(-4px); }
.dropdown-enter-active, .dropdown-leave-active { transition: all 0.15s ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-6px) scale(0.98); }

/* === Mobile === */
@media (max-width: 767px) {
  .sidebar { transform: translateX(-100%); transition: transform var(--t-slow), width var(--t-slow); }
  .app-shell.sidebar-open .sidebar { transform: translateX(0); }
  .app-shell.sidebar-open .sidebar-backdrop { display: block; }
  .main-area { margin-left: 0 !important; }
  .topbar__hamburger { display: flex !important; }
  .page-content { padding: var(--space-4); }
}
</style>
