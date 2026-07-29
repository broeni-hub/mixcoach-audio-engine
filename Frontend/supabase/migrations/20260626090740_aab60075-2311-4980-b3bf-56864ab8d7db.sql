ALTER TABLE public.coach_feedback
  ADD CONSTRAINT coach_feedback_analysis_user_unique UNIQUE (analysis_id, user_id);