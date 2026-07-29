
-- 1) Extend analyses with optional 2-track + transition metrics
ALTER TABLE public.analyses
  ADD COLUMN IF NOT EXISTS track_b_filename text,
  ADD COLUMN IF NOT EXISTS track_b_bpm numeric,
  ADD COLUMN IF NOT EXISTS track_b_key text,
  ADD COLUMN IF NOT EXISTS cue_point_sec numeric,
  ADD COLUMN IF NOT EXISTS transition_metrics jsonb NOT NULL DEFAULT '{}'::jsonb;

-- 2) coach_feedback — personalised LLM coaching per analysis
CREATE TABLE IF NOT EXISTS public.coach_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id uuid NOT NULL REFERENCES public.analyses(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  model text NOT NULL,
  summary text NOT NULL,
  items jsonb NOT NULL DEFAULT '[]'::jsonb,
  prompt_meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coach_feedback_analysis ON public.coach_feedback(analysis_id);
CREATE INDEX IF NOT EXISTS idx_coach_feedback_user ON public.coach_feedback(user_id, created_at DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.coach_feedback TO authenticated;
GRANT ALL ON public.coach_feedback TO service_role;

ALTER TABLE public.coach_feedback ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own coach feedback" ON public.coach_feedback
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TRIGGER trg_coach_feedback_updated_at
  BEFORE UPDATE ON public.coach_feedback
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- 3) feedback_ratings — 👍/👎 per finding or coach item
CREATE TABLE IF NOT EXISTS public.feedback_ratings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  analysis_id uuid NOT NULL REFERENCES public.analyses(id) ON DELETE CASCADE,
  target_kind text NOT NULL CHECK (target_kind IN ('rule','coach_item')),
  target_ref text NOT NULL,
  rating smallint NOT NULL CHECK (rating IN (-1, 1)),
  comment text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  UNIQUE (user_id, analysis_id, target_kind, target_ref)
);
CREATE INDEX IF NOT EXISTS idx_feedback_ratings_user ON public.feedback_ratings(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_ratings_target ON public.feedback_ratings(target_kind, target_ref);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.feedback_ratings TO authenticated;
GRANT ALL ON public.feedback_ratings TO service_role;

ALTER TABLE public.feedback_ratings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own ratings" ON public.feedback_ratings
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TRIGGER trg_feedback_ratings_updated_at
  BEFORE UPDATE ON public.feedback_ratings
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
