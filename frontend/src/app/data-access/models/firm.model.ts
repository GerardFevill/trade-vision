export interface Firm {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Profile {
  id: number;
  name: string;
  firm_id: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface FirmWithProfiles extends Firm {
  profiles: Profile[];
}

export interface CreateFirmRequest {
  name: string;
}

export interface CreateProfileRequest {
  name: string;
  firm_id: number;
  is_default?: boolean;
}
