export type AutonomyLevel = 'observe' | 'recommend' | 'approval' | 'execute';
export type AutonomousRisk = 'none' | 'low' | 'medium';

export interface AgentDefinition {
  id: number; agent_key: string; display_name: string; monitor_id: number | null;
  lifecycle_status: 'active' | 'inactive'; version_count: number; active_config_id: number | null;
}

export interface AgentConfiguration {
  id: number; agent_key: string; display_name: string; version_number: number;
  objective: string; instructions: string; provider_code: string; model_code: string;
  status: 'draft' | 'active' | 'superseded' | 'retired'; created_by: string;
  change_reason: string; created_at: string;
  limits: { timeout_seconds: number; max_context_events: number; max_actions_per_run: number };
  tool_policies: Array<{ id: number; tool_name: string; constraints: Record<string, unknown> }>;
  autonomy_policy: null | { id: number; autonomy_level: AutonomyLevel; execution_mode: 'simulation'|'live'; max_autonomous_risk: AutonomousRisk; allowed_autonomous_actions: string[] };
}

export interface AgentDefinitionsResponse { schema_version: string; count: number; agents: AgentDefinition[] }
export interface AgentConfigurationsResponse { schema_version: string; count: number; configurations: AgentConfiguration[] }
