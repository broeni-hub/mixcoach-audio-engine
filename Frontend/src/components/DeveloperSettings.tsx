import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle, Plug } from "lucide-react";
import { audioEngineClient, subscribeEngineStatus, type ConnectionState } from "@/services/audioEngineClient";
import { toast } from "sonner";

export function DeveloperSettings() {
  const [url, setUrl] = useState<string>(() => audioEngineClient.getUrl() ?? "");
  const [status, setStatus] = useState<ConnectionState>(() => audioEngineClient.getLastStatus());
  const [testing, setTesting] = useState(false);

  useEffect(() => subscribeEngineStatus(() => setStatus(audioEngineClient.getLastStatus())), []);

  const save = () => {
    audioEngineClient.setUrl(url.trim() || null);
    toast.success(url.trim() ? "Backend URL saved" : "Backend URL cleared");
  };

  const test = async () => {
    setTesting(true);
    const next = await audioEngineClient.testConnection();
    setTesting(false);
    if (next.status === "ok") toast.success("Backend reachable");
    else toast.error(`Connection failed: ${next.error ?? "unknown"}`);
  };

  return (
    <Card className="glass border-accent/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plug className="h-4 w-4 text-accent" /> Developer
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Connect MixCoach to a separate audio engine. Leave empty to use the built-in demo analysis.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label htmlFor="engine-url">Audio Engine URL</Label>
          <div className="mt-1 flex gap-2">
            <Input
              id="engine-url"
              placeholder="https://your-engine.example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              spellCheck={false}
              autoCapitalize="off"
            />
            <Button variant="outline" onClick={save}>Save</Button>
            <Button onClick={test} disabled={testing || !url.trim()}>
              {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : "Test"}
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-border/60 bg-secondary/30 p-3 text-sm space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Last connection:</span>
            {status.status === "ok" && (
              <Badge variant="secondary" className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30">
                <CheckCircle2 className="h-3 w-3 mr-1" /> OK
              </Badge>
            )}
            {status.status === "error" && (
              <Badge variant="destructive">
                <XCircle className="h-3 w-3 mr-1" /> Error
              </Badge>
            )}
            {status.status === "unknown" && (
              <Badge variant="outline">Not tested yet</Badge>
            )}
            {status.checkedAt && (
              <span className="text-xs text-muted-foreground ml-auto">
                {new Date(status.checkedAt).toLocaleString()}
              </span>
            )}
          </div>
          {status.url && (
            <div className="text-xs text-muted-foreground truncate">URL: {status.url}</div>
          )}
          {status.error && (
            <div className="text-xs text-destructive break-words">Error: {status.error}</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
