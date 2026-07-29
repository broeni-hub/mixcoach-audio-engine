
-- Enums
CREATE TYPE public.experience_level AS ENUM ('beginner', 'intermediate', 'advanced');
CREATE TYPE public.plan_tier AS ENUM ('free', 'pro', 'studio');
CREATE TYPE public.event_severity AS ENUM ('info', 'warning', 'critical');

-- Shared updated_at trigger
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- profiles
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT,
  experience public.experience_level NOT NULL DEFAULT 'beginner',
  preferred_genres TEXT[] NOT NULL DEFAULT '{}',
  equipment TEXT,
  xp INTEGER NOT NULL DEFAULT 0,
  level INTEGER NOT NULL DEFAULT 1,
  streak INTEGER NOT NULL DEFAULT 0,
  plan public.plan_tier NOT NULL DEFAULT 'free',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles TO authenticated;
GRANT ALL ON public.profiles TO service_role;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY "Users insert own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)));
  RETURN NEW;
END;
$$;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- analyses
CREATE TABLE public.analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  duration_seconds NUMERIC,
  genre TEXT,
  bpm NUMERIC,
  bpm_confidence NUMERIC,
  key_name TEXT,
  key_confidence NUMERIC,
  bass_pct NUMERIC,
  mid_pct NUMERIC,
  high_pct NUMERIC,
  bass_stability NUMERIC,
  dynamic_range_db NUMERIC,
  loudness_dbfs NUMERIC,
  peak_count INTEGER,
  scores JSONB NOT NULL DEFAULT '{}'::jsonb,
  curves JSONB NOT NULL DEFAULT '{}'::jsonb,
  coach_summary TEXT,
  archived BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_analyses_user_created ON public.analyses(user_id, created_at DESC);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.analyses TO authenticated;
GRANT ALL ON public.analyses TO service_role;
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own analyses" ON public.analyses FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE TRIGGER trg_analyses_updated_at BEFORE UPDATE ON public.analyses FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- analysis_events
CREATE TABLE public.analysis_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID NOT NULL REFERENCES public.analyses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  at_seconds NUMERIC NOT NULL,
  event_type TEXT NOT NULL,
  severity public.event_severity NOT NULL DEFAULT 'info',
  value NUMERIC,
  message TEXT,
  rule_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_events_analysis ON public.analysis_events(analysis_id);
CREATE INDEX idx_events_user_type ON public.analysis_events(user_id, event_type);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.analysis_events TO authenticated;
GRANT ALL ON public.analysis_events TO service_role;
ALTER TABLE public.analysis_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own events" ON public.analysis_events FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- coaching_rules (shared knowledge base)
CREATE TABLE public.coaching_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  condition JSONB NOT NULL,
  diagnosis TEXT NOT NULL,
  fix TEXT NOT NULL,
  severity public.event_severity NOT NULL DEFAULT 'warning',
  exercise_id UUID,
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT ON public.coaching_rules TO authenticated;
GRANT ALL ON public.coaching_rules TO service_role;
ALTER TABLE public.coaching_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated read rules" ON public.coaching_rules FOR SELECT TO authenticated USING (enabled = true);
CREATE TRIGGER trg_rules_updated_at BEFORE UPDATE ON public.coaching_rules FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- exercises
CREATE TABLE public.exercises (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  target_metric TEXT,
  target_delta NUMERIC,
  difficulty INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
  video_url TEXT,
  prerequisite_ids UUID[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT ON public.exercises TO authenticated;
GRANT ALL ON public.exercises TO service_role;
ALTER TABLE public.exercises ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated read exercises" ON public.exercises FOR SELECT TO authenticated USING (true);
CREATE TRIGGER trg_exercises_updated_at BEFORE UPDATE ON public.exercises FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

ALTER TABLE public.coaching_rules
  ADD CONSTRAINT coaching_rules_exercise_fk FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE SET NULL;
