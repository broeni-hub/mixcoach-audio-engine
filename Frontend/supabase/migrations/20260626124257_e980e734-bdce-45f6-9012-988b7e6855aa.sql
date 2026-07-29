
DROP POLICY IF EXISTS "anyone can join waitlist" ON public.waitlist;
CREATE POLICY "anyone can join waitlist" ON public.waitlist
  FOR INSERT TO anon, authenticated
  WITH CHECK (email IS NOT NULL AND char_length(email) BETWEEN 3 AND 320);
