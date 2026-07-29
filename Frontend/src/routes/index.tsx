import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import {
  Waves, Upload, Brain, TrendingUp, Sparkles, Check, ChevronRight,
  Headphones, BarChart3, Trophy,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "MixCoach — Become a Better DJ" },
      { name: "description", content: "Upload your transitions, get professional feedback, improve every mix." },
    ],
  }),
  component: Landing,
});

function Nav() {
  return (
    <header className="sticky top-0 z-50">
      <div className="rk-bar-top" />
      <div className="glass">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md bg-[image:var(--gradient-primary)] flex items-center justify-center glow-purple">
              <Waves className="h-4 w-4 text-white" />
            </div>
            <span className="font-display font-bold text-lg tracking-tight">MixCoach</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-[13px] uppercase tracking-wider font-medium text-muted-foreground">
            <a href="#how" className="hover:text-foreground transition-colors">How it works</a>
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#pricing" className="hover:text-foreground transition-colors">Pricing</a>
            <a href="#faq" className="hover:text-foreground transition-colors">FAQ</a>
          </nav>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="uppercase tracking-wider text-xs"><Link to="/app/dashboard">Sign in</Link></Button>
            <Button asChild size="sm" className="bg-[image:var(--gradient-primary)] border-0 glow-purple hover:opacity-90 uppercase tracking-wider text-xs font-semibold">
              <Link to="/app/dashboard">Get Started</Link>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 grid-bg opacity-40 pointer-events-none" />
      <div className="absolute inset-0" style={{ background: "var(--gradient-hero)" }} />
      <div className="relative mx-auto max-w-7xl px-6 pt-24 pb-32 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-xs text-muted-foreground backdrop-blur animate-fade-in">
          <Sparkles className="h-3 w-3 text-accent" />
          Expert coaching for aspiring DJs
        </div>
        <h1 className="mt-6 font-display text-5xl md:text-7xl font-bold tracking-tight animate-fade-in">
          Become a Better DJ <br />
          <span className="gradient-text">Every Mix.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground animate-fade-in">
          Upload your transitions. Get professional feedback on beatmatching, EQ, timing and creativity.
          Improve every mix with personalized exercises.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-3 animate-fade-in">
          <Button asChild size="lg" className="bg-[image:var(--gradient-primary)] border-0 glow-purple hover:opacity-90">
            <Link to="/app/upload"><Upload className="h-4 w-4" /> Analyze My Mix</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <a href="#how">See how it works <ChevronRight className="h-4 w-4" /></a>
          </Button>
        </div>

        <div className="mx-auto mt-20 max-w-5xl">
          <div className="glass rounded-2xl p-2 glow-blue">
            <div className="rounded-xl bg-card p-6 md:p-10">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-left">
                {[
                  { label: "BPM", value: "126.2" },
                  { label: "Key", value: "A min" },
                  { label: "Beatmatch", value: "92" },
                  { label: "Overall", value: "88" },
                ].map((s) => (
                  <div key={s.label}>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">{s.label}</div>
                    <div className="mt-2 font-display text-3xl font-bold">{s.value}</div>
                  </div>
                ))}
              </div>
              <div className="mt-8 h-24 relative overflow-hidden rounded-lg bg-secondary/40">
                <div className="absolute inset-0 flex items-end gap-1 px-2 pb-2">
                  {Array.from({ length: 80 }).map((_, i) => (
                    <div key={i}
                      className="flex-1 rounded-sm bg-[image:var(--gradient-primary)] opacity-80"
                      style={{ height: `${20 + Math.sin(i / 4) * 30 + Math.random() * 30}%` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    { icon: Upload, title: "Upload your transition", desc: "Drop an mp3, wav or aiff. Up to 500MB." },
    { icon: Brain, title: "Deep transition analysis", desc: "BPM, beat grid, EQ, energy, phrasing — all in seconds." },
    { icon: TrendingUp, title: "Get personalized coaching", desc: "Concrete feedback and the next exercise to level up." },
  ];
  return (
    <section id="how" className="mx-auto max-w-7xl px-6 py-24">
      <div className="text-center">
        <h2 className="font-display text-4xl font-bold">How it works</h2>
        <p className="mt-3 text-muted-foreground">From upload to insight in under a minute.</p>
      </div>
      <div className="mt-16 grid md:grid-cols-3 gap-6">
        {steps.map((s, i) => (
          <div key={s.title} className="glass rounded-2xl p-8 hover:border-primary/40 transition-colors">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-secondary flex items-center justify-center">
                <s.icon className="h-5 w-5 text-accent" />
              </div>
              <span className="text-xs text-muted-foreground">Step {i + 1}</span>
            </div>
            <h3 className="mt-5 font-display text-xl font-semibold">{s.title}</h3>
            <p className="mt-2 text-muted-foreground text-sm">{s.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Features() {
  const features = [
    { icon: Headphones, title: "Multi-genre aware", desc: "House, Tech House, Melodic, Afro, Progressive, Techno, D&B." },
    { icon: BarChart3, title: "Deep technical metrics", desc: "Beat grid, EQ balance, phrase detection, energy curves." },
    { icon: Brain, title: "Coach-level feedback", desc: "Specific, actionable notes — never generic." },
    { icon: Trophy, title: "Progress & XP system", desc: "Level up from Bedroom DJ to Festival Ready." },
    { icon: TrendingUp, title: "Track improvement", desc: "See your scores climb with every mix." },
    { icon: Sparkles, title: "Personal training plan", desc: "Daily challenges tailored to your weaknesses." },
  ];
  return (
    <section id="features" className="border-t border-border bg-card/30">
      <div className="mx-auto max-w-7xl px-6 py-24">
        <div className="text-center">
          <h2 className="font-display text-4xl font-bold">Everything you need to improve</h2>
          <p className="mt-3 text-muted-foreground">Built by DJs, for DJs.</p>
        </div>
        <div className="mt-16 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div key={f.title} className="glass rounded-2xl p-6 hover:-translate-y-1 transition-transform">
              <f.icon className="h-6 w-6 text-primary" />
              <h3 className="mt-4 font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Testimonials() {
  const t = [
    { name: "Alex K.", role: "Bedroom DJ", quote: "Spotted a phrase mismatch I never would have caught. My mixes feel tighter after two weeks." },
    { name: "Maya R.", role: "Resident DJ", quote: "Like having a mentor on call. The exercises are spot on." },
    { name: "Tomás B.", role: "Beginner", quote: "The feedback is brutally specific. Exactly what I needed." },
  ];
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <div className="text-center">
        <h2 className="font-display text-4xl font-bold">Loved by DJs leveling up</h2>
      </div>
      <div className="mt-16 grid md:grid-cols-3 gap-6">
        {t.map((q) => (
          <div key={q.name} className="glass rounded-2xl p-6">
            <p className="text-sm leading-relaxed">"{q.quote}"</p>
            <div className="mt-6 text-sm">
              <div className="font-semibold">{q.name}</div>
              <div className="text-muted-foreground">{q.role}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Pricing() {
  const plans = [
    { name: "Free", price: "$0", desc: "Get started", features: ["3 analyses", "Basic reports", "Daily challenge"], cta: "Start free" },
    { name: "Premium", price: "$12", per: "/mo", desc: "Most popular", featured: true, features: ["Unlimited analyses", "Advanced reports", "Full history", "Training plans", "Personal Coach"], cta: "Go Premium" },
  ];
  return (
    <section id="pricing" className="border-t border-border bg-card/30">
      <div className="mx-auto max-w-5xl px-6 py-24">
        <div className="text-center">
          <h2 className="font-display text-4xl font-bold">Simple pricing</h2>
          <p className="mt-3 text-muted-foreground">Start free. Upgrade when you're hooked.</p>
        </div>
        <div className="mt-16 grid md:grid-cols-2 gap-6">
          {plans.map((p) => (
            <div key={p.name} className={`glass rounded-2xl p-8 ${p.featured ? "border-primary/50 glow-purple" : ""}`}>
              <div className="flex items-center justify-between">
                <h3 className="font-display text-2xl font-bold">{p.name}</h3>
                {p.featured && <span className="text-xs rounded-full bg-primary/20 text-primary px-2 py-1">Popular</span>}
              </div>
              <div className="mt-4 flex items-end gap-1">
                <span className="font-display text-5xl font-bold">{p.price}</span>
                {p.per && <span className="text-muted-foreground mb-2">{p.per}</span>}
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{p.desc}</p>
              <ul className="mt-6 space-y-3 text-sm">
                {p.features.map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-accent" /> {f}
                  </li>
                ))}
              </ul>
              <Button asChild className={`mt-8 w-full ${p.featured ? "bg-[image:var(--gradient-primary)] border-0 hover:opacity-90" : ""}`} variant={p.featured ? "default" : "outline"}>
                <Link to="/app/dashboard">{p.cta}</Link>
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FAQ() {
  const items = [
    { q: "What file formats are supported?", a: "MP3, WAV and AIFF up to 500MB." },
    { q: "Is this an auto-DJ?", a: "No. MixCoach is a coach — it analyzes mixes you make and gives feedback. It never mixes for you." },
    { q: "Which genres work best?", a: "House, Tech House, Melodic, Afro, Progressive, Techno and Drum & Bass." },
    { q: "Can I use it on my hardware?", a: "Yes. Record from any controller — Pioneer, Denon, Traktor, Rekordbox, Serato, VirtualDJ." },
  ];
  return (
    <section id="faq" className="mx-auto max-w-3xl px-6 py-24">
      <h2 className="text-center font-display text-4xl font-bold">Frequently asked</h2>
      <div className="mt-12 divide-y divide-border rounded-2xl glass">
        {items.map((i) => (
          <details key={i.q} className="group p-6">
            <summary className="flex cursor-pointer items-center justify-between font-medium">
              {i.q}
              <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" />
            </summary>
            <p className="mt-3 text-sm text-muted-foreground">{i.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-12 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <Waves className="h-4 w-4 text-primary" />
          <span>© {new Date().getFullYear()} MixCoach</span>
        </div>
        <div className="flex gap-6">
          <a href="#" className="hover:text-foreground">Privacy</a>
          <a href="#" className="hover:text-foreground">Terms</a>
          <a href="#" className="hover:text-foreground">Contact</a>
        </div>
      </div>
    </footer>
  );
}

function Landing() {
  return (
    <div className="min-h-screen">
      <Nav />
      <Hero />
      <HowItWorks />
      <Features />
      <Testimonials />
      <Pricing />
      <FAQ />
      <Footer />
    </div>
  );
}
