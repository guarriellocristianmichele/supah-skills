<script>
  import Card from "$lib/Card.svelte";
  let { data } = $props();
</script>

<Card title={data.title} />
