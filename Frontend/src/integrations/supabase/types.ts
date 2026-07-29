export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      analyses: {
        Row: {
          analysis_goal: string | null
          analysis_status: string
          archived: boolean
          bass_pct: number | null
          bass_stability: number | null
          bpm: number | null
          bpm_confidence: number | null
          coach_summary: string | null
          created_at: string
          cue_point_sec: number | null
          curves: Json
          duration_seconds: number | null
          dynamic_range_db: number | null
          file_url: string | null
          filename: string
          genre: string | null
          high_pct: number | null
          id: string
          key_confidence: number | null
          key_name: string | null
          loudness_dbfs: number | null
          mid_pct: number | null
          payload: Json
          peak_count: number | null
          provider: string
          scores: Json
          track_b_bpm: number | null
          track_b_filename: string | null
          track_b_key: string | null
          transition_metrics: Json
          type: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          analysis_goal?: string | null
          analysis_status?: string
          archived?: boolean
          bass_pct?: number | null
          bass_stability?: number | null
          bpm?: number | null
          bpm_confidence?: number | null
          coach_summary?: string | null
          created_at?: string
          cue_point_sec?: number | null
          curves?: Json
          duration_seconds?: number | null
          dynamic_range_db?: number | null
          file_url?: string | null
          filename: string
          genre?: string | null
          high_pct?: number | null
          id?: string
          key_confidence?: number | null
          key_name?: string | null
          loudness_dbfs?: number | null
          mid_pct?: number | null
          payload?: Json
          peak_count?: number | null
          provider?: string
          scores?: Json
          track_b_bpm?: number | null
          track_b_filename?: string | null
          track_b_key?: string | null
          transition_metrics?: Json
          type?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          analysis_goal?: string | null
          analysis_status?: string
          archived?: boolean
          bass_pct?: number | null
          bass_stability?: number | null
          bpm?: number | null
          bpm_confidence?: number | null
          coach_summary?: string | null
          created_at?: string
          cue_point_sec?: number | null
          curves?: Json
          duration_seconds?: number | null
          dynamic_range_db?: number | null
          file_url?: string | null
          filename?: string
          genre?: string | null
          high_pct?: number | null
          id?: string
          key_confidence?: number | null
          key_name?: string | null
          loudness_dbfs?: number | null
          mid_pct?: number | null
          payload?: Json
          peak_count?: number | null
          provider?: string
          scores?: Json
          track_b_bpm?: number | null
          track_b_filename?: string | null
          track_b_key?: string | null
          transition_metrics?: Json
          type?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      analysis_events: {
        Row: {
          analysis_id: string
          at_seconds: number
          created_at: string
          event_type: string
          id: string
          message: string | null
          rule_id: string | null
          severity: Database["public"]["Enums"]["event_severity"]
          user_id: string
          value: number | null
        }
        Insert: {
          analysis_id: string
          at_seconds: number
          created_at?: string
          event_type: string
          id?: string
          message?: string | null
          rule_id?: string | null
          severity?: Database["public"]["Enums"]["event_severity"]
          user_id: string
          value?: number | null
        }
        Update: {
          analysis_id?: string
          at_seconds?: number
          created_at?: string
          event_type?: string
          id?: string
          message?: string | null
          rule_id?: string | null
          severity?: Database["public"]["Enums"]["event_severity"]
          user_id?: string
          value?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "analysis_events_analysis_id_fkey"
            columns: ["analysis_id"]
            isOneToOne: false
            referencedRelation: "analyses"
            referencedColumns: ["id"]
          },
        ]
      }
      analysis_feedback: {
        Row: {
          analysis_id: string
          comment: string | null
          created_at: string
          id: string
          updated_at: string
          usefulness: string
          user_id: string
        }
        Insert: {
          analysis_id: string
          comment?: string | null
          created_at?: string
          id?: string
          updated_at?: string
          usefulness: string
          user_id: string
        }
        Update: {
          analysis_id?: string
          comment?: string | null
          created_at?: string
          id?: string
          updated_at?: string
          usefulness?: string
          user_id?: string
        }
        Relationships: []
      }
      analysis_hash_cache: {
        Row: {
          analysis_id: string
          created_at: string
          hash: string
          id: string
          updated_at: string
          user_id: string
        }
        Insert: {
          analysis_id: string
          created_at?: string
          hash: string
          id?: string
          updated_at?: string
          user_id: string
        }
        Update: {
          analysis_id?: string
          created_at?: string
          hash?: string
          id?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "analysis_hash_cache_analysis_id_fkey"
            columns: ["analysis_id"]
            isOneToOne: false
            referencedRelation: "analyses"
            referencedColumns: ["id"]
          },
        ]
      }
      analysis_results: {
        Row: {
          analysis_id: string
          created_at: string
          id: string
          provider: string
          raw_result_json: Json
          user_id: string
        }
        Insert: {
          analysis_id: string
          created_at?: string
          id?: string
          provider: string
          raw_result_json: Json
          user_id: string
        }
        Update: {
          analysis_id?: string
          created_at?: string
          id?: string
          provider?: string
          raw_result_json?: Json
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "analysis_results_analysis_id_fkey"
            columns: ["analysis_id"]
            isOneToOne: false
            referencedRelation: "analyses"
            referencedColumns: ["id"]
          },
        ]
      }
      beta_feedback: {
        Row: {
          created_at: string
          id: string
          kind: string
          message: string
          subject: string | null
          url: string | null
          user_agent: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string
          id?: string
          kind: string
          message: string
          subject?: string | null
          url?: string | null
          user_agent?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string
          id?: string
          kind?: string
          message?: string
          subject?: string | null
          url?: string | null
          user_agent?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      coach_feedback: {
        Row: {
          analysis_id: string
          created_at: string
          id: string
          items: Json
          model: string
          prompt_meta: Json
          summary: string
          updated_at: string
          user_id: string
        }
        Insert: {
          analysis_id: string
          created_at?: string
          id?: string
          items?: Json
          model: string
          prompt_meta?: Json
          summary: string
          updated_at?: string
          user_id: string
        }
        Update: {
          analysis_id?: string
          created_at?: string
          id?: string
          items?: Json
          model?: string
          prompt_meta?: Json
          summary?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "coach_feedback_analysis_id_fkey"
            columns: ["analysis_id"]
            isOneToOne: false
            referencedRelation: "analyses"
            referencedColumns: ["id"]
          },
        ]
      }
      coach_feedback_failures: {
        Row: {
          analysis_id: string | null
          created_at: string
          error_message: string | null
          error_name: string | null
          error_stack: string | null
          finish_reason: string | null
          id: string
          model: string | null
          prompt_meta: Json | null
          raw_object: Json | null
          raw_text: string | null
          raw_text_length: number | null
          settings: Json | null
          user_id: string | null
          zod_issues: Json | null
        }
        Insert: {
          analysis_id?: string | null
          created_at?: string
          error_message?: string | null
          error_name?: string | null
          error_stack?: string | null
          finish_reason?: string | null
          id?: string
          model?: string | null
          prompt_meta?: Json | null
          raw_object?: Json | null
          raw_text?: string | null
          raw_text_length?: number | null
          settings?: Json | null
          user_id?: string | null
          zod_issues?: Json | null
        }
        Update: {
          analysis_id?: string | null
          created_at?: string
          error_message?: string | null
          error_name?: string | null
          error_stack?: string | null
          finish_reason?: string | null
          id?: string
          model?: string | null
          prompt_meta?: Json | null
          raw_object?: Json | null
          raw_text?: string | null
          raw_text_length?: number | null
          settings?: Json | null
          user_id?: string | null
          zod_issues?: Json | null
        }
        Relationships: []
      }
      coaching_rules: {
        Row: {
          condition: Json
          created_at: string
          diagnosis: string
          enabled: boolean
          exercise_id: string | null
          fix: string
          id: string
          severity: Database["public"]["Enums"]["event_severity"]
          slug: string
          title: string
          updated_at: string
        }
        Insert: {
          condition: Json
          created_at?: string
          diagnosis: string
          enabled?: boolean
          exercise_id?: string | null
          fix: string
          id?: string
          severity?: Database["public"]["Enums"]["event_severity"]
          slug: string
          title: string
          updated_at?: string
        }
        Update: {
          condition?: Json
          created_at?: string
          diagnosis?: string
          enabled?: boolean
          exercise_id?: string | null
          fix?: string
          id?: string
          severity?: Database["public"]["Enums"]["event_severity"]
          slug?: string
          title?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "coaching_rules_exercise_fk"
            columns: ["exercise_id"]
            isOneToOne: false
            referencedRelation: "exercises"
            referencedColumns: ["id"]
          },
        ]
      }
      exercises: {
        Row: {
          created_at: string
          description: string
          difficulty: number
          id: string
          prerequisite_ids: string[]
          slug: string
          target_delta: number | null
          target_metric: string | null
          title: string
          updated_at: string
          video_url: string | null
        }
        Insert: {
          created_at?: string
          description: string
          difficulty?: number
          id?: string
          prerequisite_ids?: string[]
          slug: string
          target_delta?: number | null
          target_metric?: string | null
          title: string
          updated_at?: string
          video_url?: string | null
        }
        Update: {
          created_at?: string
          description?: string
          difficulty?: number
          id?: string
          prerequisite_ids?: string[]
          slug?: string
          target_delta?: number | null
          target_metric?: string | null
          title?: string
          updated_at?: string
          video_url?: string | null
        }
        Relationships: []
      }
      feedback_ratings: {
        Row: {
          analysis_id: string
          comment: string | null
          created_at: string
          id: string
          rating: number
          target_kind: string
          target_ref: string
          updated_at: string
          user_id: string
        }
        Insert: {
          analysis_id: string
          comment?: string | null
          created_at?: string
          id?: string
          rating: number
          target_kind: string
          target_ref: string
          updated_at?: string
          user_id: string
        }
        Update: {
          analysis_id?: string
          comment?: string | null
          created_at?: string
          id?: string
          rating?: number
          target_kind?: string
          target_ref?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "feedback_ratings_analysis_id_fkey"
            columns: ["analysis_id"]
            isOneToOne: false
            referencedRelation: "analyses"
            referencedColumns: ["id"]
          },
        ]
      }
      invite_codes: {
        Row: {
          code: string
          created_at: string
          max_uses: number
          note: string | null
          used_count: number
        }
        Insert: {
          code: string
          created_at?: string
          max_uses?: number
          note?: string | null
          used_count?: number
        }
        Update: {
          code?: string
          created_at?: string
          max_uses?: number
          note?: string | null
          used_count?: number
        }
        Relationships: []
      }
      profiles: {
        Row: {
          created_at: string
          display_name: string | null
          equipment: string | null
          experience: Database["public"]["Enums"]["experience_level"]
          id: string
          level: number
          plan: Database["public"]["Enums"]["plan_tier"]
          preferred_genres: string[]
          streak: number
          updated_at: string
          xp: number
        }
        Insert: {
          created_at?: string
          display_name?: string | null
          equipment?: string | null
          experience?: Database["public"]["Enums"]["experience_level"]
          id: string
          level?: number
          plan?: Database["public"]["Enums"]["plan_tier"]
          preferred_genres?: string[]
          streak?: number
          updated_at?: string
          xp?: number
        }
        Update: {
          created_at?: string
          display_name?: string | null
          equipment?: string | null
          experience?: Database["public"]["Enums"]["experience_level"]
          id?: string
          level?: number
          plan?: Database["public"]["Enums"]["plan_tier"]
          preferred_genres?: string[]
          streak?: number
          updated_at?: string
          xp?: number
        }
        Relationships: []
      }
      transitions: {
        Row: {
          ai_feedback: string | null
          analysis_id: string
          confidence: number | null
          created_at: string
          duration: number
          end_time: number
          id: string
          main_issue: string | null
          raw_transition_json: Json | null
          score: number | null
          start_time: number
          suggested_exercise: string | null
          type: string | null
          user_id: string
        }
        Insert: {
          ai_feedback?: string | null
          analysis_id: string
          confidence?: number | null
          created_at?: string
          duration: number
          end_time: number
          id: string
          main_issue?: string | null
          raw_transition_json?: Json | null
          score?: number | null
          start_time: number
          suggested_exercise?: string | null
          type?: string | null
          user_id: string
        }
        Update: {
          ai_feedback?: string | null
          analysis_id?: string
          confidence?: number | null
          created_at?: string
          duration?: number
          end_time?: number
          id?: string
          main_issue?: string | null
          raw_transition_json?: Json | null
          score?: number | null
          start_time?: number
          suggested_exercise?: string | null
          type?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "transitions_analysis_id_fkey"
            columns: ["analysis_id"]
            isOneToOne: false
            referencedRelation: "analyses"
            referencedColumns: ["id"]
          },
        ]
      }
      user_rule_override_history: {
        Row: {
          action: string
          changed_at: string
          changed_by: string
          changed_by_email: string | null
          id: string
          new_diagnosis: string | null
          new_fix: string | null
          new_note: string | null
          override_id: string | null
          prev_diagnosis: string | null
          prev_fix: string | null
          prev_note: string | null
          rule_id: string
          user_id: string
        }
        Insert: {
          action: string
          changed_at?: string
          changed_by: string
          changed_by_email?: string | null
          id?: string
          new_diagnosis?: string | null
          new_fix?: string | null
          new_note?: string | null
          override_id?: string | null
          prev_diagnosis?: string | null
          prev_fix?: string | null
          prev_note?: string | null
          rule_id: string
          user_id: string
        }
        Update: {
          action?: string
          changed_at?: string
          changed_by?: string
          changed_by_email?: string | null
          id?: string
          new_diagnosis?: string | null
          new_fix?: string | null
          new_note?: string | null
          override_id?: string | null
          prev_diagnosis?: string | null
          prev_fix?: string | null
          prev_note?: string | null
          rule_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_rule_override_history_override_id_fkey"
            columns: ["override_id"]
            isOneToOne: false
            referencedRelation: "user_rule_overrides"
            referencedColumns: ["id"]
          },
        ]
      }
      user_rule_overrides: {
        Row: {
          created_at: string
          custom_diagnosis: string | null
          custom_fix: string | null
          id: string
          note: string | null
          rule_id: string
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          custom_diagnosis?: string | null
          custom_fix?: string | null
          id?: string
          note?: string | null
          rule_id: string
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          custom_diagnosis?: string | null
          custom_fix?: string | null
          id?: string
          note?: string | null
          rule_id?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_rule_overrides_rule_id_fkey"
            columns: ["rule_id"]
            isOneToOne: false
            referencedRelation: "coaching_rules"
            referencedColumns: ["id"]
          },
        ]
      }
      user_subscriptions: {
        Row: {
          created_at: string
          current_period_end: string | null
          plan: string
          status: string
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          current_period_end?: string | null
          plan?: string
          status?: string
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          current_period_end?: string | null
          plan?: string
          status?: string
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      waitlist: {
        Row: {
          created_at: string
          email: string
          id: string
          name: string | null
          source: string | null
        }
        Insert: {
          created_at?: string
          email: string
          id?: string
          name?: string | null
          source?: string | null
        }
        Update: {
          created_at?: string
          email?: string
          id?: string
          name?: string | null
          source?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      event_severity: "info" | "warning" | "critical"
      experience_level: "beginner" | "intermediate" | "advanced"
      plan_tier: "free" | "pro" | "studio"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      event_severity: ["info", "warning", "critical"],
      experience_level: ["beginner", "intermediate", "advanced"],
      plan_tier: ["free", "pro", "studio"],
    },
  },
} as const
