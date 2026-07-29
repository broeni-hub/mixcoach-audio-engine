import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Share2, Music2, Sparkles, TrendingUp, TrendingDown, Wand2, Target, Headphones, Crown } from "lucide-react";
import { useAppState } from "@/lib/store";
import { computeDjDna } from "@/lib/retention";
import { toast } from "sonner";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/dna")({
  head: () => ({ meta: [{ title: "DJ DNA — MixCoach" }] }),
  component: DnaPage,
});

export function DnaPage() {
  const [state] = useAppState();
  const dna = computeDjDna(state);
  const currentFocus = dna.weaknesses[0]?.label ?? "Keep uploading";

  function share() {
    const text = `🎧 My DJ DNA on MixCoach\nArchetype: ${dna.archetype}\nGenre: ${dna.mainGenre}\nStyle: ${dna.mixStyle}\nSignature: ${dna.signatureTransition}`;
    if (navigator.share) {
      navigator.share({ title: "My DJ DNA", text }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text);
      toast.success("DJ DNA copied to clipboard");
    }
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow text-xs text-accent uppercase tracking-wider">Profile</p>
          <h1 className="font-display text-3xl font-bold mt-1">DJ DNA</h1>
          <p className="text-muted-foreground mt-1">Your mixing personality, decoded.</p>
        </div>
        <Button onClick={share} variant="outline"><Share2 className="h-4 w-4" /> Share</Button>
      </div>

      {/* Large Archetype Card */}
      <Card className="glass overflow-hidden border-primary/30">
        <div className="bg-[image:var(--gradient-hero)] p-8 md:p-10">
          <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="space-y-3">
              <div className="text-xs uppercase tracking-[0.25em] text-primary/80">Your archetype</div>
              <div className="font-display text-4xl md:text-6xl font-bold">{dna.archetype}</div>
              <p className="text-foreground/80 max-w-2xl text-lg leading-relaxed">{dna.archetypeDescription}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge className="bg-primary/15 text-primary border-primary/30 hover:bg-primary/20 gap-1"><Music2 className="h-3 w-3" /> {dna.mainGenre}</Badge>
                <Badge className="bg-primary/15 text-primary border-primary/30 hover:bg-primary/20 gap-1"><Wand2 className="h-3 w-3" /> {dna.mixStyle}</Badge>
                <Badge className="bg-accent/15 text-accent border-accent/30 hover:bg-accent/20 gap-1"><Sparkles className="h-3 w-3" /> {dna.signatureTransition}</Badge>
              </div>
            </div>
            <div className="hidden md:flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl bg-[image:var(--gradient-primary)] ring-2 ring-primary/30">
              <Crown className="h-10 w-10 text-primary-foreground" />
            </div>
          </div>
        </div>
      </Card>

      {/* Who you are */}
      <section className="max-w-3xl">
        <h2 className="font-display text-2xl font-bold mb-3">Who you are</h2>
        <p className="text-lg text-foreground/90 leading-relaxed">{dna.archetypeStory}</p>
      </section>

      {/* Profile traits */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="glass">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-emerald-400">
              <TrendingUp className="h-5 w-5" />
              <h3 className="font-display text-lg font-semibold">Strengths</h3>
            </div>
            <div className="space-y-2">
              {dna.strengths.map((s) => (
                <div key={s.key} className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
                  <div className="font-medium">{s.label}</div>
                  <div className="font-display text-xl font-bold">{s.value}</div>
                </div>
              ))}
              {!dna.strengths[0]?.value && <div className="text-sm text-muted-foreground">Upload a few sessions to reveal your strengths.</div>}
            </div>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-amber-400">
              <TrendingDown className="h-5 w-5" />
              <h3 className="font-display text-lg font-semibold">Weaknesses</h3>
            </div>
            <div className="space-y-2">
              {dna.weaknesses.map((s) => (
                <div key={s.key} className="flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                  <div className="font-medium">{s.label}</div>
                  <div className="font-display text-xl font-bold">{s.value}</div>
                </div>
              ))}
              {!dna.weaknesses[0]?.value && <div className="text-sm text-muted-foreground">More data needed.</div>}
            </div>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center gap-2 text-primary">
              <Target className="h-5 w-5" />
              <h3 className="font-display text-lg font-semibold">Current focus</h3>
            </div>
            <p className="text-foreground/80">Your next growth area is <span className="font-semibold text-foreground">{currentFocus}</span>. Focused practice here will unlock the next stage of your DJ career.</p>
            <Button asChild variant="outline" className="w-full">
              <a href="/app/training">Train this skill</a>
            </Button>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-primary">
              <Music2 className="h-5 w-5" />
              <h3 className="font-display text-lg font-semibold">Favorite genre</h3>
            </div>
            <div className="font-display text-3xl font-bold">{dna.mainGenre}</div>
            <p className="text-sm text-muted-foreground">The genre you upload most often.</p>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-accent">
              <Sparkles className="h-5 w-5" />
              <h3 className="font-display text-lg font-semibold">Signature transition</h3>
            </div>
            <div className="font-display text-2xl font-bold">{dna.signatureTransition}</div>
            <p className="text-sm text-muted-foreground">Your most common blend style across all analyses.</p>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-primary">
              <Headphones className="h-5 w-5" />
              <h3 className="font-display text-lg font-semibold">Mix style</h3>
            </div>
            <div className="font-display text-2xl font-bold">{dna.mixStyle}</div>
            <p className="text-sm text-muted-foreground">How your transitions tend to feel overall.</p>
          </CardContent>
        </Card>
      </div>

      {/* Share card preview */}
      <section className="space-y-4">
        <h2 className="font-display text-2xl font-bold">Share card preview</h2>
        <div className="mx-auto max-w-md overflow-hidden rounded-2xl border border-primary/30 bg-[image:var(--gradient-primary)] p-8 shadow-2xl">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-primary-foreground/70">MixCoach</div>
            <Crown className="h-5 w-5 text-primary-foreground/80" />
          </div>
          <div className="mt-6 space-y-1">
            <div className="text-xs uppercase tracking-widest text-primary-foreground/70">DJ Archetype</div>
            <div className="font-display text-3xl font-bold text-primary-foreground">{dna.archetype}</div>
          </div>
          <p className="mt-2 text-sm text-primary-foreground/80 leading-relaxed">{dna.archetypeDescription}</p>
          <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-primary-foreground/10 p-3 backdrop-blur-sm">
              <div className="text-primary-foreground/60 text-xs uppercase tracking-wider">Genre</div>
              <div className="font-semibold text-primary-foreground mt-0.5">{dna.mainGenre}</div>
            </div>
            <div className="rounded-lg bg-primary-foreground/10 p-3 backdrop-blur-sm">
              <div className="text-primary-foreground/60 text-xs uppercase tracking-wider">Signature</div>
              <div className="font-semibold text-primary-foreground mt-0.5">{dna.signatureTransition}</div>
            </div>
          </div>
          <div className="mt-6 text-center text-xs text-primary-foreground/60">mixcoach.ai · my DJ DNA</div>
        </div>
        <div className="text-center">
          <Button onClick={share} className="bg-[image:var(--gradient-primary)] text-primary-foreground hover:opacity-90">
            <Share2 className="h-4 w-4" /> Share my DJ DNA
          </Button>
        </div>
      </section>

      <NextActionBar
        title="Sharpen the skill that defines your sound."
        subtitle="A focused drill on your weakest area shifts your archetype fastest."
        cta="Improve This Skill"
        to="/app/training"
      />
    </div>
  );
}
