import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const features = [
  { icon: "🚀", title: "Lightning fast", body: "Ship in minutes." },
  { icon: "🔒", title: "Secure by default", body: "Your data stays yours." },
  { icon: "⚡", title: "Scales with you", body: "From one user to a million." },
];

export default function Landing() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="hero h-screen flex flex-col items-center justify-center text-center">
        <span className="text-xs uppercase tracking-widest text-indigo-400">Introducing Acme AI</span>
        <h1 className="text-6xl font-bold">Build faster with <span className="bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">AI</span></h1>
        <a href="#" className="mt-8 rounded-full bg-indigo-600 px-6 py-3 transition-all hover:scale-105">Get started →</a>
        <p className="text-sm text-slate-400">No credit card · Free forever · Cancel anytime</p>
      </section>
      <motion.section initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((f) => (
          <div key={f.title} className={cn("rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6", "shadow-[0_0_30px_rgba(139,92,246,0.5)] hover:scale-105")}>
            <div className="w-12 h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center">{f.icon}</div>
            <h3 className="text-xl font-semibold">{f.title}</h3>
            <p className="text-slate-400">{f.body}</p>
          </div>
        ))}
      </motion.section>
      <motion.section initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} className="grid grid-cols-3 text-center">
        <div><p className="text-4xl font-bold">10,000+</p><p>Developers</p></div>
        <div><p className="text-4xl font-bold">99.9%</p><p>Uptime</p></div>
        <div><p className="text-4xl font-bold">5x</p><p>Faster</p></div>
      </motion.section>
      <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} className="rounded-xl border border-white/10">
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500" />
          <span className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="w-3 h-3 rounded-full bg-green-500" />
        </div>
      </motion.div>
      <motion.blockquote initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} className="rounded-lg border-l-4 border-indigo-500 bg-white/5 p-4 hover:scale-105">
        "It changed everything." Jane Doe
      </motion.blockquote>
      <span className="relative flex h-2 w-2"><span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400" /></span>
      <p className="font-mono text-xs uppercase tracking-wider">v2.0 · build 1432</p>
      <ol><li>01</li><li>02</li><li>03</li></ol>
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">Card</div>
      <p>Call us at (555) 123-4567</p>
      <p>FAST — ship today</p>
      <div className="w-[1200px] mx-auto">Wide</div>
      <div className="group"><span className="opacity-0 group-hover:opacity-100">Edit</span></div>
      <p className="text-[10px] w-screen">Legal</p>
      <p className="bg-slate-900 text-gray-500">Built for teams of every size</p>
    </main>
  );
}
