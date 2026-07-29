/**
 * VaultAlert — Centralized TypeScript Types
 * Mirrors all backend Pydantic schemas exactly.
 */

// ── Enums ───────────────────────────────────────────────────────────────────
export type UserRole =
  | 'Admin' | 'Owner' | 'Family' | 'Manager'
  | 'Employee' | 'Guard' | 'Auditor';

export type LockerStatus =
  | 'Locked' | 'Unlocked' | 'Tampered' | 'Offline' | 'Lockdown';

export type DoorState = 'Open' | 'Closed';

export type AlertSeverity = 'Critical' | 'Warning' | 'Info';

export type EventType =
  | 'DoorForced' | 'Tampering' | 'UnknownFace' | 'FingerprintFailed'
  | 'OTPFailed' | 'MotionDetected' | 'DoorLeftOpen' | 'CameraOffline'
  | 'BatteryLow' | 'InternetOffline' | 'PowerFailure'
  | 'AccessGranted' | 'AccessDenied' | 'EmergencyLockdown';

export type AuthMethod =
  | 'Fingerprint' | 'Face' | 'OTP' | 'AdminOverride' | 'MultiFactor';

export type AccessStatus = 'Granted' | 'Denied';

export type NotificationChannel =
  | 'Push' | 'SMS' | 'Email' | 'Telegram' | 'WhatsApp';

// ── Entity Interfaces ────────────────────────────────────────────────────────
export interface Organization {
  id: string;
  name: string;
  slug: string;
  subscription_tier: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  organization_id?: string;
  avatar_url?: string;
  created_at: string;
}

export interface Locker {
  id: string;
  organization_id: string;
  name: string;
  locker_number?: string;
  location?: string;
  gps_lat?: number;
  gps_lng?: number;
  status: LockerStatus;
  door_state: DoorState;
  battery_status: number;
  signal_strength: number;
  temperature?: number;
  humidity?: number;
  is_online: boolean;
  camera_online: boolean;
  tamper_detected: boolean;
  motion_detected: boolean;
  last_seen?: string;
  created_at: string;
}

export interface Device {
  id: string;
  locker_id: string;
  serial_number: string;
  firmware_version: string;
  device_type: string;
  last_ping?: string;
  created_at: string;
}

export interface SecurityEvent {
  id: string;
  locker_id: string;
  event_type: EventType;
  severity: AlertSeverity;
  threat_score: number;
  description?: string;
  ai_summary?: string;
  before_snapshot_url?: string;
  after_snapshot_url?: string;
  video_clip_url?: string;
  resolved: boolean;
  timestamp: string;
}

export interface AccessLog {
  id: string;
  locker_id: string;
  user_id?: string;
  auth_method: AuthMethod;
  status: AccessStatus;
  timestamp: string;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  channel: NotificationChannel;
  severity: AlertSeverity;
  is_read: boolean;
  timestamp: string;
}

export interface Permission {
  id: string;
  locker_id: string;
  user_id: string;
  can_unlock: boolean;
  can_view_live: boolean;
  can_view_logs: boolean;
  can_manage: boolean;
  valid_from?: string;
  valid_until?: string;
  created_at: string;
}

export interface DashboardMetrics {
  total_lockers: number;
  online_lockers: number;
  offline_lockers: number;
  today_access_count: number;
  unauthorized_attempts_today: number;
  active_alerts: number;
  avg_battery: number;
  threat_score_avg: number;
  camera_online_count: number;
  network_health_percent: number;
}

export interface AccessTrendPoint {
  date: string;
  granted: number;
  denied: number;
}

export interface ThreatTrendPoint {
  date: string;
  score: number;
  events: number;
}

// ── Generic Responses ────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface MessageResponse {
  message: string;
  success: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
