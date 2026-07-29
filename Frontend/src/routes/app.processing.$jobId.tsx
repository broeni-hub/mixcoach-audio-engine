// Legacy route — redirects to the new premium processing page.
import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/app/processing/$jobId")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/analysis/processing/$jobId", params: { jobId: params.jobId } });
  },
});
