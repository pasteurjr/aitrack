export interface AuthSession {
  schema_version: 'auth-session.v1';
  user: { public_id: string; display_name: string; email: string };
  tenant: { public_id: string; slug: string };
  roles: string[];
  permissions: string[];
  expires_at: string;
}
