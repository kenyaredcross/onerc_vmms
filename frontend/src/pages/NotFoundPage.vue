<template>
  <div class="nf-wrap">
    <div class="nf-card">
      <div class="nf-code">404</div>
      <h1 class="nf-title">Page not found</h1>
      <p class="nf-msg">The page you're looking for doesn't exist or you don't have permission to view it.</p>
      <router-link to="/dashboard" class="nf-btn">Back to Dashboard</router-link>
    </div>
  </div>
</template>

<script setup></script>

<style scoped>
.nf-wrap {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  padding: 24px; background: var(--c-bg);
}
.nf-card { text-align: center; max-width: 420px; }
.nf-code {
  font-size: 96px; font-weight: 900; color: var(--c-primary);
  line-height: 1; margin-bottom: 16px; letter-spacing: -4px;
}
.nf-title { font-size: 28px; font-weight: 800; color: var(--c-text); margin-bottom: 12px; }
.nf-msg   { font-size: 15px; color: var(--c-text-muted); line-height: 1.6; margin-bottom: 28px; }
.nf-btn {
  display: inline-block; background: var(--c-primary); color: #fff;
  padding: 12px 28px; border-radius: var(--radius-md); font-size: 14px;
  font-weight: 700; text-decoration: none; transition: background var(--t-base);
}
.nf-btn:hover { background: var(--c-primary-hover); }
</style>
