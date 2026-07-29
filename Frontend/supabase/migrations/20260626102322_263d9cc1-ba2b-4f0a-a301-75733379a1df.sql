CREATE TABLE public.coach_feedback_failures (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id uuid,
  user_id uuid,
  model text,
  settings jsonb,
  prompt_meta jsonb,
  raw_text text,
  raw_text_length integer,
  raw_object jsonb,
  finish_reason text,
  error_name text,
  error_message text,
  error_stack text,
  zod_issues jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

GRANT SELECT ON public.coach_feedback_failures TO authenticated;
GRANT ALL ON public.coach_feedback_failures TO service_role;

ALTER TABLE public.coach_feedback_failures ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own coach failures"
  ON public.coach_feedback_failures
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE INDEX coach_feedback_failures_user_created_idx
  ON public.coach_feedback_failures (user_id, created_at DESC);
CREATE INDEX coach_feedback_failures_analysis_idx
  ON public.coach_feedback_failures (analysis_id);