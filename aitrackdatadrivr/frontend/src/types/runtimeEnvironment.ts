export type RuntimeMode = 'production' | 'simulation' | 'replay' | 'mixed' | 'unknown';

export interface RuntimeSourceMode {
  source: 'tracker' | 'dirijabem';
  label: string;
  mode: Exclude<RuntimeMode, 'mixed'>;
  configured: boolean;
}

export interface RuntimeEnvironment {
  schema_version: 'runtime-environment.v1';
  generated_at: string;
  mode: RuntimeMode;
  authority: string;
  safe_for_real_actions: boolean;
  sources: RuntimeSourceMode[];
  issues: string[];
}
