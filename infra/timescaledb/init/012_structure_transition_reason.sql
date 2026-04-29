ALTER TABLE structure_state
  ADD COLUMN IF NOT EXISTS last_transition_reason TEXT NOT NULL DEFAULT 'initialization';
