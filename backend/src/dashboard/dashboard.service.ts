import { Injectable, BadRequestException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { SupabaseClient, createClient } from '@supabase/supabase-js';

export interface CandidateDashboardStats {
  candidateId: number | null;
  firstProfileDate: string | null;
  applications: number;
  interviews: number;
  savedOffers: number;
  notifications: number;
  statusPending: number;
  statusAccepted: number;
  statusRefused: number;
}

@Injectable()
export class DashboardService {
  private supabase: SupabaseClient;

  constructor(private config: ConfigService) {
    const url = this.config.get<string>('SUPABASE_URL');
    const key = this.config.get<string>('SUPABASE_SERVICE_ROLE_KEY');

    if (!url || !key) {
      throw new Error(
        'SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis',
      );
    }

    this.supabase = createClient(url, key);
  }

  async getCandidateStats(userId: number): Promise<CandidateDashboardStats> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: true })
      .limit(1)
      .maybeSingle();

    if (candidateError) {
      throw new BadRequestException(
        candidateError.message || 'Erreur lors du chargement du candidat',
      );
    }

    if (!candidate) {
      return {
        candidateId: null,
        firstProfileDate: null,
        applications: 0,
        interviews: 0,
        savedOffers: 0,
        notifications: 0,
        statusPending: 0,
        statusAccepted: 0,
        statusRefused: 0,
      };
    }

    const candidateId = candidate.id as number;

    const [
      { count: applications = 0 },
      { count: interviews = 0 },
      { count: statusPending = 0 },
      { count: statusAccepted = 0 },
      { count: statusRefused = 0 },
    ] = await Promise.all([
      this.supabase
        .from('candidate_postule')
        .select('id', { count: 'exact', head: true })
        .eq('candidate_id', candidateId),
      this.supabase
        .from('candidate_postule')
        .select('id', { count: 'exact', head: true })
        .eq('candidate_id', candidateId)
        .eq('validate', true),
      this.supabase
        .from('candidate_postule')
        .select('id', { count: 'exact', head: true })
        .eq('candidate_id', candidateId)
        .eq('status', 'EN_COURS'),
      this.supabase
        .from('candidate_postule')
        .select('id', { count: 'exact', head: true })
        .eq('candidate_id', candidateId)
        .eq('status', 'ACCEPTEE'),
      this.supabase
        .from('candidate_postule')
        .select('id', { count: 'exact', head: true })
        .eq('candidate_id', candidateId)
        .eq('status', 'REFUSEE'),
    ]);

    return {
      candidateId,
      firstProfileDate: candidate.created_at as string,
      applications: applications ?? 0,
      interviews: interviews ?? 0,
      savedOffers: 0,
      notifications: 0,
      statusPending: statusPending ?? 0,
      statusAccepted: statusAccepted ?? 0,
      statusRefused: statusRefused ?? 0,
    };
  }
}

