export function Shell({ steps }: { steps: string[] }) {
  return (
    <div>
      <a href="#main" className="sr-only focus:not-sr-only">Skip to content</a>
      <nav className="sticky top-0 z-10 backdrop-blur bg-white/80 border-b border-stone-200">Menu</nav>
      <main id="main" className="grid grid-cols-[1fr_2fr] gap-8">
        <span className="inline-block h-2 w-2 rounded-full bg-green-600" aria-label="online" />
        <div className="h-6 w-6 animate-spin rounded-full border-b-2 border-brand-600 motion-reduce:animate-none" />
        <aside className="border-l border-stone-200 pl-4">Notes</aside>
        <ol className="space-y-4">
          <li><span>01</span> Measure the frame</li>
          <li><span>02</span> Cut the tube</li>
          <li><span>03</span> Braze the joint</li>
        </ol>
        <button className="bg-brand-600 text-white transition-colors">Book a fitting</button>
      </main>
    </div>
  );
}
