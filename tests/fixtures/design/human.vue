<template>
  <article class="menu-card">
    <h2>Tonight's pasta</h2>
    <p class="price">{{ price }}</p>
    <button type="button" class="order" @click="$emit('order')">Order for pickup</button>
  </article>
</template>

<style scoped>
.menu-card { padding: 1.25rem 1rem 1.75rem; border-top: 1px solid var(--ink); }
.price { font-variant-numeric: tabular-nums; }
.order { min-height: 44px; }
</style>
