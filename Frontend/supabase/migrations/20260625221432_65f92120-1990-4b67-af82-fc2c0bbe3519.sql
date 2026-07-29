CREATE TABLE public.user_rule_overrides (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  rule_id uuid NOT NULL REFERENCES public.coaching_rules(id) ON DELETE CASCADE,
  custom_diagnosis text,
  custom_fix text,
  note text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  UNIQUE (user_id, rule_id)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_rule_overrides TO authenticated;
GRANT ALL ON public.user_rule_overrides TO service_role;

ALTER TABLE public.user_rule_overrides ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own rule overrides"
  ON public.user_rule_overrides
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TRIGGER set_user_rule_overrides_updated_at
  BEFORE UPDATE ON public.user_rule_overrides
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();