
-- 1. invite_codes: remove public read; lookups go through service role server-side
DROP POLICY IF EXISTS "public can check invite codes" ON public.invite_codes;
REVOKE SELECT ON public.invite_codes FROM anon, authenticated;

-- 2. waitlist: explicit no-read policy to make intent clear
CREATE POLICY "no one can read waitlist" ON public.waitlist
  FOR SELECT TO anon, authenticated USING (false);

-- 3. user_rule_override_history: scope to authenticated role explicitly
DROP POLICY IF EXISTS "Users read own override history" ON public.user_rule_override_history;
CREATE POLICY "Users read own override history" ON public.user_rule_override_history
  FOR SELECT TO authenticated USING (auth.uid() = user_id);
