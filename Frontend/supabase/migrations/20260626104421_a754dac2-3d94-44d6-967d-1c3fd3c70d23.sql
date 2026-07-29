CREATE TABLE public.analysis_hash_cache (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  hash text NOT NULL,
  analysis_id uuid NOT NULL REFERENCES public.analyses(id) ON DELETE CASCADE,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  UNIQUE (user_id, hash)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.analysis_hash_cache TO authenticated;
GRANT ALL ON public.analysis_hash_cache TO service_role;

ALTER TABLE public.analysis_hash_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own hash cache"
  ON public.analysis_hash_cache
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_analysis_hash_cache_user_hash ON public.analysis_hash_cache(user_id, hash);

CREATE TRIGGER trg_analysis_hash_cache_updated_at
  BEFORE UPDATE ON public.analysis_hash_cache
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();