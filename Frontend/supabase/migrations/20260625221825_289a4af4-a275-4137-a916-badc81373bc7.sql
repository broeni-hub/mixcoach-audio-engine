
CREATE TABLE public.user_rule_override_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  override_id uuid REFERENCES public.user_rule_overrides(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  rule_id uuid NOT NULL,
  changed_by uuid NOT NULL,
  changed_by_email text,
  action text NOT NULL CHECK (action IN ('create','update','delete')),
  prev_diagnosis text,
  new_diagnosis text,
  prev_fix text,
  new_fix text,
  prev_note text,
  new_note text,
  changed_at timestamptz NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT ON public.user_rule_override_history TO authenticated;
GRANT ALL ON public.user_rule_override_history TO service_role;

ALTER TABLE public.user_rule_override_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own override history"
  ON public.user_rule_override_history FOR SELECT
  USING (auth.uid() = user_id);

CREATE INDEX idx_uroh_user_rule ON public.user_rule_override_history(user_id, rule_id, changed_at DESC);

CREATE OR REPLACE FUNCTION public.log_user_rule_override_change()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  actor uuid := auth.uid();
  actor_email text;
BEGIN
  SELECT email INTO actor_email FROM auth.users WHERE id = actor;
  IF TG_OP = 'INSERT' THEN
    INSERT INTO public.user_rule_override_history(override_id,user_id,rule_id,changed_by,changed_by_email,action,new_diagnosis,new_fix,new_note)
    VALUES (NEW.id,NEW.user_id,NEW.rule_id,COALESCE(actor,NEW.user_id),actor_email,'create',NEW.custom_diagnosis,NEW.custom_fix,NEW.note);
    RETURN NEW;
  ELSIF TG_OP = 'UPDATE' THEN
    IF NEW.custom_diagnosis IS DISTINCT FROM OLD.custom_diagnosis
       OR NEW.custom_fix IS DISTINCT FROM OLD.custom_fix
       OR NEW.note IS DISTINCT FROM OLD.note THEN
      INSERT INTO public.user_rule_override_history(override_id,user_id,rule_id,changed_by,changed_by_email,action,prev_diagnosis,new_diagnosis,prev_fix,new_fix,prev_note,new_note)
      VALUES (NEW.id,NEW.user_id,NEW.rule_id,COALESCE(actor,NEW.user_id),actor_email,'update',OLD.custom_diagnosis,NEW.custom_diagnosis,OLD.custom_fix,NEW.custom_fix,OLD.note,NEW.note);
    END IF;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO public.user_rule_override_history(override_id,user_id,rule_id,changed_by,changed_by_email,action,prev_diagnosis,prev_fix,prev_note)
    VALUES (OLD.id,OLD.user_id,OLD.rule_id,COALESCE(actor,OLD.user_id),actor_email,'delete',OLD.custom_diagnosis,OLD.custom_fix,OLD.note);
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$;

CREATE TRIGGER trg_log_user_rule_override_change
AFTER INSERT OR UPDATE OR DELETE ON public.user_rule_overrides
FOR EACH ROW EXECUTE FUNCTION public.log_user_rule_override_change();
