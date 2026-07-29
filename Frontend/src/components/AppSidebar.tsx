import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Home, ListMusic, Dumbbell, TrendingUp, Disc3,
  Settings, Sparkles, Upload, Waves, LogOut, User,
} from "lucide-react";
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent,
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/use-auth";
import { PlanBadge } from "@/components/PlanBadge";
import { useMonthlyUsage, usePlan, openUpgradeModal } from "@/lib/billing";
import { useLang } from "@/lib/i18n";
import { LanguageToggle } from "@/components/LanguageToggle";

const NAV_TEXTS = {
  de: { home: "Start", training: "Training", history: "Verlauf", library: "Library",
        progress: "Fortschritt", profile: "Profil", settings: "Einstellungen",
        upgrade: "Upgrade zu Pro", upload: "Set hochladen" },
  en: { home: "Home", training: "Training", history: "History", library: "Library",
        progress: "Progress", profile: "Profile", settings: "Settings",
        upgrade: "Upgrade to Pro", upload: "Upload Transition" },
} as const;

const primaryDefs = [
  { key: "home" as const,     url: "/app/dashboard", icon: Home },
  { key: "training" as const, url: "/app/training",  icon: Dumbbell },
  { key: "history" as const,  url: "/app/analyses",  icon: ListMusic },
  { key: "library" as const,  url: "/app/library",   icon: Disc3 },
  { key: "progress" as const, url: "/app/progress",  icon: TrendingUp },
];

const accountDefs = [
  { key: "profile" as const,  url: "/app/profile",  icon: User },
  { key: "settings" as const, url: "/app/settings", icon: Settings },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const { user } = useAuth();
  const navigate = useNavigate();
  const lang = useLang();
  const T = NAV_TEXTS[lang];
  const primaryItems = primaryDefs.map((d) => ({ ...d, title: T[d.key] }));
  const accountItems = accountDefs.map((d) => ({ ...d, title: T[d.key] }));
  const upgradeItem = { title: T.upgrade, url: "/app/premium", icon: Sparkles };

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate({ to: "/auth", replace: true });
  }


  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-3 py-4">
        <Link to="/app/dashboard" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-[image:var(--gradient-primary)] flex items-center justify-center glow-purple">
            <Waves className="h-4 w-4 text-white" />
          </div>
          {!collapsed && (
            <div className="font-display font-bold text-lg tracking-tight">
              MixCoach
            </div>
          )}
        </Link>
      </SidebarHeader>
      <SidebarContent className="gap-6">
        <SidebarGroup>
          <SidebarGroupContent>
            {!collapsed && (
              <div className="px-2 pb-3">
                <Button asChild size="sm" className="w-full bg-[image:var(--gradient-primary)] glow-purple hover:opacity-90 border-0">
                  <Link to="/app/upload">
                    <Upload className="h-4 w-4" /> {T.upload}
                  </Link>
                </Button>
              </div>
            )}
            <SidebarMenu>
              {primaryItems.map((item) => {
                const active = pathname === item.url || pathname.startsWith(item.url + "/");
                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton asChild isActive={active}>
                      <Link to={item.url} className="flex items-center gap-2">
                        <item.icon className="h-4 w-4" />
                        {!collapsed && <span>{item.title}</span>}
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {accountItems.map((item) => {
                const active = pathname === item.url || pathname.startsWith(item.url + "/");
                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton asChild isActive={active}>
                      <Link to={item.url} className="flex items-center gap-2">
                        <item.icon className="h-4 w-4" />
                        {!collapsed && <span>{item.title}</span>}
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={pathname === upgradeItem.url}>
                  <Link to={upgradeItem.url} className="flex items-center gap-2">
                    <upgradeItem.icon className="h-4 w-4" />
                    {!collapsed && <span>{upgradeItem.title}</span>}
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-2 space-y-1">
        <LanguageToggle collapsed={collapsed} />
        {!collapsed && <UsageCard />}
        {user && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSignOut}
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
            title={user.email ?? "Sign out"}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!collapsed && <span className="truncate">{user.email ?? "Sign out"}</span>}
          </Button>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}

function UsageCard() {
  const { isPro } = usePlan();
  const { used, cap, capped } = useMonthlyUsage();
  if (isPro) {
    return (
      <div className="rounded-lg border border-primary/40 bg-primary/10 px-3 py-2 text-xs">
        <div className="flex items-center justify-between">
          <PlanBadge asLink={false} />
          <span className="text-muted-foreground">Unlimited</span>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1">All features unlocked.</p>
      </div>
    );
  }
  const pct = typeof cap === "number" ? Math.min(100, (used / cap) * 100) : 0;
  return (
    <button
      type="button"
      onClick={() => openUpgradeModal()}
      className="w-full text-left rounded-lg border border-border bg-card/60 px-3 py-2 text-xs hover:border-primary/50 transition-colors"
    >
      <div className="flex items-center justify-between">
        <PlanBadge asLink={false} />
        <span className={`font-mono ${capped ? "text-primary" : "text-muted-foreground"}`}>{used}/{cap}</span>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-border overflow-hidden">
        <div className="h-full bg-[image:var(--gradient-primary)]" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[10px] text-muted-foreground mt-1">
        {capped ? "Upgrade for unlimited analyses" : "Analyses this month"}
      </p>
    </button>
  );
}
