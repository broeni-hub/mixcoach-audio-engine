import { createFileRoute, Outlet, Link, useNavigate } from "@tanstack/react-router";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { Button } from "@/components/ui/button";
import { Upload, Loader2 } from "lucide-react";
import { useActiveJobs } from "@/lib/use-jobs";
import { useAuth } from "@/lib/use-auth";
import { useEffect } from "react";
import { UpgradeModal } from "@/components/UpgradeModal";
import { BetaMenu } from "@/components/BetaMenu";
import { PlanBadge } from "@/components/PlanBadge";

export const Route = createFileRoute("/app")({
  ssr: false,
  component: AppLayout,
});

function ActiveJobPill() {
  const jobs = useActiveJobs();
  if (jobs.length === 0) return null;
  const j = jobs[0];
  return (
    <Link
      to="/app/upload"
      className="hidden sm:flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-3 py-1 text-xs hover:bg-primary/15 transition-colors max-w-[280px]"
    >
      <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
      <span className="truncate text-foreground">{j.fileName}</span>
      <span className="font-mono font-semibold text-primary">{j.overall}%</span>
      {jobs.length > 1 && (
        <span className="rounded-full bg-primary/20 px-1.5 text-[10px] text-primary">+{jobs.length - 1}</span>
      )}
    </Link>
  );
}

function AppLayout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const DEV_BYPASS_AUTH = true;

  useEffect(() => {
    if (DEV_BYPASS_AUTH) return;

    if (!loading && !user) {
      navigate({ to: "/auth", replace: true });
    }
  }, [loading, user, navigate]);

  useEffect(() => {
    if (DEV_BYPASS_AUTH) return;

    if (!user) return;

    void import("@/lib/sync").then((m) => m.syncAnalysesWithDb(user.id));
  }, [user]);

  if (!DEV_BYPASS_AUTH && (loading || !user)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-background">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <div className="rk-bar-top sticky top-0 z-40" />
          <header className="h-14 flex items-center justify-between border-b border-border px-4 glass sticky top-[3px] z-30">
            <div className="flex items-center gap-2">
              <SidebarTrigger />
            </div>
            <div className="flex items-center gap-3">
              <ActiveJobPill />
              <PlanBadge />
              <Button asChild size="sm" className="bg-[image:var(--gradient-primary)] border-0 hover:opacity-90 uppercase tracking-wider text-xs font-semibold">
                <Link to="/app/upload"><Upload className="h-4 w-4" /> Upload</Link>
              </Button>
            </div>
          </header>
          <main className="flex-1 p-6 md:p-8">
            <Outlet />
          </main>
        </div>
        <UpgradeModal />
        <BetaMenu />
      </div>
    </SidebarProvider>
  );
}
