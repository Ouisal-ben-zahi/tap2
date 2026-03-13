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
  avatarUrl?: string | null;
}

export interface CandidatePortfolioItem {
  id: number;
  title: string;
  shortDescription: string | null;
  longDescription: string | null;
  tags: string[];
  createdAt: string | null;
}

export interface CandidateApplicationItem {
  id: number;
  jobId: number | null;
  jobTitle: string | null;
  company: string | null;
  status: string | null;
  validate: boolean;
  validatedAt: string | null;
}

export interface CandidateCvFileItem {
  name: string;
  path: string;
  publicUrl: string;
  updatedAt: string | null;
  size: number | null;
}

export interface RecruiterJobPayload {
  title: string;
  categorie_profil?: string | null;
  niveau_attendu?: string | null;
  experience_min?: string | null;
  presence_sur_site?: string | null;
  reason?: string | null;
  main_mission?: string | null;
  tasks_other?: string | null;
  disponibilite?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  urgent?: boolean;
  contrat?: string | null;
  niveau_seniorite?: string | null;
  entreprise?: string | null;
}

export interface CandidatePortfolioPdfFiles {
  portfolioShort: CandidateCvFileItem[];
  portfolioLong: CandidateCvFileItem[];
}

export interface RecruiterOverviewStats {
  totalJobs: number;
  totalApplications: number;
  totalCandidates: number;
  urgentJobs: number;
  lastJobDate: string | null;
  jobsPerCategory: { label: string; value: number }[];
  applicationsPerJob: { jobId: number; title: string; value: number }[];
  recentApplications: {
    id: number;
    candidateName: string | null;
    jobTitle: string | null;
    status: string | null;
    validatedAt: string | null;
  }[];
  alerts: { type: string; message: string }[];
}

export interface PublicJobItem {
  id: number;
  title: string | null;
  categorie_profil: string | null;
  created_at: string | null;
  urgent: boolean;
  location_type: any | null;
}

export interface CandidateScoreFromJson {
  candidateId: number | null;
  scoreGlobal: number | null;
  decision: string | null;
  familleDominante: string | null;
  metadataTimestamp: string | null;
  metadataSector: string | null;
  metadataModule: string | null;
  commentaire: string | null;
  dimensions: { id: string; label: string; score: number }[];
  skills: { name: string; score: number; status: string; scope: string }[];
  softSkills: { nom: string; niveau: string }[];
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

  private async getCandidateIdForUser(userId: number): Promise<{ id: number; created_at: string } | null> {
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
      return null;
    }

    return candidate as { id: number; created_at: string };
  }


  private async getOrCreateCandidate(userId: number): Promise<{ id: number; categorie_profil: string | null }> {
    const { data: existing } = await this.supabase
      .from("candidates")
      .select("id, categorie_profil")
      .eq("user_id", userId)
      .order("created_at", { ascending: true })
      .limit(1)
      .maybeSingle();

    if (existing) return existing;

    // Fetch user email for the new candidate profile
    const { data: user } = await this.supabase
      .from("users")
      .select("email")
      .eq("id", userId)
      .single();

    const idAgent = 'A1-' + Math.random().toString(16).slice(2, 8).toUpperCase();
    const emailPrefix = (user?.email || 'candidat').split('@')[0];
    const { data: created, error } = await this.supabase
      .from("candidates")
      .insert({
        user_id: userId,
        email: user?.email || null,
        nom: emailPrefix,
        prenom: '',
        categorie_profil: 'Autres',
        id_agent: idAgent,
      })
      .select("id, categorie_profil")
      .single();

    if (error || !created) {
      throw new BadRequestException(error?.message || "Impossible de creer le profil candidat");
    }
    return created;
  }
  async getCandidateStats(userId: number): Promise<CandidateDashboardStats> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const {
      data: candidateRow,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, created_at, image_minio_url')
      .eq('user_id', userId)
      .order('created_at', { ascending: true })
      .limit(1)
      .maybeSingle();

    if (candidateError) {
      throw new BadRequestException(
        candidateError.message || 'Erreur lors du chargement du candidat',
      );
    }

    if (!candidateRow) {
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

    const candidateId = candidateRow.id as number;

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

    let avatarUrl: string | null = null;
    const rawImagePath =
      (candidateRow.image_minio_url as string | null) ?? null;

    if (rawImagePath) {
      const { data: signed, error: signedError } = await this.supabase.storage
        .from('tap_files')
        .createSignedUrl(rawImagePath, 60 * 60);

      if (!signedError && signed) {
        // debug backend: image trouvée
        // eslint-disable-next-line no-console
        console.log(
          '[avatar] image trouvée pour candidat',
          candidateId,
          'path =',
          rawImagePath,
        );
        avatarUrl = signed.signedUrl;
      } else {
        // eslint-disable-next-line no-console
        console.log(
          '[avatar] image introuvable ou erreur pour candidat',
          candidateId,
          'path =',
          rawImagePath,
          'error =',
          signedError?.message ?? null,
        );
      }
    } else {
      // eslint-disable-next-line no-console
      console.log(
        '[avatar] aucune image_minio_url pour candidat',
        candidateId,
      );
    }

    return {
      candidateId,
      firstProfileDate: candidateRow.created_at as string,
      applications: applications ?? 0,
      interviews: interviews ?? 0,
      savedOffers: 0,
      notifications: 0,
      statusPending: statusPending ?? 0,
      statusAccepted: statusAccepted ?? 0,
      statusRefused: statusRefused ?? 0,
      avatarUrl,
    };
  }

  async getCandidatePortfolio(userId: number): Promise<{ projects: CandidatePortfolioItem[] }> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const candidate = await this.getCandidateIdForUser(userId);

    if (!candidate) {
      return { projects: [] };
    }

    const { data, error } = await this.supabase
      .from('candidate_projects')
      .select('id, project_name, project_description, detailed_description, technologies, created_at')
      .eq('candidate_id', candidate.id)
      .order('created_at', { ascending: false });

    if (error) {
      throw new BadRequestException(
        error.message || 'Erreur lors du chargement du portfolio',
      );
    }

    const projects: CandidatePortfolioItem[] =
      (data ?? []).map((row: any) => {
        const tech = Array.isArray(row.technologies) ? row.technologies : [];
        const tags = tech
          .map((t: any) =>
            typeof t === 'string'
              ? t
              : t?.name ?? t?.label ?? '',
          )
          .filter((x: string) => !!x)
          .slice(0, 5);

        return {
          id: row.id as number,
          title: row.project_name as string,
          shortDescription: (row.project_description as string) ?? null,
          longDescription:
            (row.detailed_description as string) ??
            (row.project_description as string) ??
            null,
          tags,
          createdAt: (row.created_at as string) ?? null,
        };
      });

    return { projects };
  }

  async getCandidateApplications(
    userId: number,
  ): Promise<{ applications: CandidateApplicationItem[] }> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const candidate = await this.getCandidateIdForUser(userId);

    if (!candidate) {
      return { applications: [] };
    }

    const { data, error } = await this.supabase
      .from('candidate_postule')
      .select(
        'id, job_id, validated_at, status, validate, jobs ( id, title, entreprise )',
      )
      .eq('candidate_id', candidate.id)
      .order('validated_at', { ascending: false });

    if (error) {
      throw new BadRequestException(
        error.message || 'Erreur lors du chargement des candidatures',
      );
    }

    const applications: CandidateApplicationItem[] = (data ?? []).map(
      (row: any) => {
        const job = row.jobs || row.job || null;
        return {
          id: row.id as number,
          jobId: (row.job_id as number) ?? (job?.id ?? null),
          jobTitle: (job?.title as string) ?? null,
          company: (job?.entreprise as string) ?? null,
          status: (row.status as string) ?? null,
          validate: Boolean(row.validate),
          validatedAt: (row.validated_at as string) ?? null,
        };
      },
    );

    return { applications };
  }

  async getCandidateCvFiles(
    userId: number,
  ): Promise<{ cvFiles: CandidateCvFileItem[] }> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
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
      return { cvFiles: [] };
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';
    const candidateId = candidate.id as number;

    // Exemple de structure dans le bucket:
    // tap_files / candidates / <categorie_profil> / <candidateId> / ...
    const basePath = `candidates/${category}/${candidateId}`;

    const { data: listed, error: listError } = await this.supabase
      .storage
      .from('tap_files')
      .list(basePath, {
        limit: 100,
      });

    if (listError) {
      throw new BadRequestException(
        listError.message || 'Erreur lors du listing des fichiers CV',
      );
    }

    const files = (listed ?? []).filter((f: any) => {
      if (typeof f.name !== 'string') return false;
      const name = f.name.toLowerCase();
      return name.startsWith('cv') && name.endsWith('.pdf');
    });

    const cvFiles: CandidateCvFileItem[] = [];

    for (const file of files) {
      const path = `${basePath}/${file.name}`;
      const { data: signed, error: signedError } = await this.supabase.storage
        .from('tap_files')
        .createSignedUrl(path, 60 * 60); // URL valable 1h

      if (signedError || !signed) {
        // on ignore juste ce fichier si la signature échoue
        // eslint-disable-next-line no-continue
        continue;
      }

      const size =
        typeof file.metadata?.size === 'number'
          ? (file.metadata.size as number)
          : null;

      cvFiles.push({
        name: file.name as string,
        path,
        publicUrl: signed.signedUrl,
        updatedAt: (file.updated_at as string) ?? null,
        size,
      });
    }

    return { cvFiles };
  }

  async getCandidateCvFilesByCandidateId(
    candidateId: number,
  ): Promise<{ cvFiles: CandidateCvFileItem[] }> {
    if (!candidateId || Number.isNaN(candidateId)) {
      throw new BadRequestException('candidateId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
      .eq('id', candidateId)
      .maybeSingle();

    if (candidateError) {
      throw new BadRequestException(
        candidateError.message || 'Erreur lors du chargement du candidat',
      );
    }

    if (!candidate) {
      return { cvFiles: [] };
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';

    const basePath = `candidates/${category}/${candidateId}`;

    const { data: listed, error: listError } = await this.supabase.storage
      .from('tap_files')
      .list(basePath, {
        limit: 100,
      });

    if (listError) {
      throw new BadRequestException(
        listError.message || 'Erreur lors du listing des fichiers CV',
      );
    }

    const files = (listed ?? []).filter((f: any) => {
      if (typeof f.name !== 'string') return false;
      const name = f.name.toLowerCase();
      return name.startsWith('cv') && name.endsWith('.pdf');
    });

    const cvFiles: CandidateCvFileItem[] = [];

    for (const file of files) {
      const path = `${basePath}/${file.name}`;
      const { data: signed, error: signedError } = await this.supabase.storage
        .from('tap_files')
        .createSignedUrl(path, 60 * 60);

      if (signedError || !signed) {
        // on ignore juste ce fichier si la signature échoue
        // eslint-disable-next-line no-continue
        continue;
      }

      const size =
        typeof file.metadata?.size === 'number'
          ? (file.metadata.size as number)
          : null;

      cvFiles.push({
        name: file.name as string,
        path,
        publicUrl: signed.signedUrl,
        updatedAt: (file.updated_at as string) ?? null,
        size,
      });
    }

    return { cvFiles };
  }

  async getCandidateTalentcardFiles(
    userId: number,
  ): Promise<{ talentcardFiles: CandidateCvFileItem[] }> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
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
      return { talentcardFiles: [] };
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';
    const candidateId = candidate.id as number;

    const basePath = `candidates/${category}/${candidateId}`;

    const { data: listed, error: listError } = await this.supabase.storage
      .from('tap_files')
      .list(basePath, {
        limit: 100,
      });

    if (listError) {
      throw new BadRequestException(
        listError.message ||
          'Erreur lors du listing des fichiers Talent Card',
      );
    }

    const files = (listed ?? []).filter((f: any) => {
      if (typeof f.name !== 'string') return false;
      const name = f.name.toLowerCase();
      return name.startsWith('talentcard') && name.endsWith('.pdf');
    });

    const talentcardFiles: CandidateCvFileItem[] = [];

    for (const file of files) {
      const path = `${basePath}/${file.name}`;
      const { data: signed, error: signedError } = await this.supabase.storage
        .from('tap_files')
        .createSignedUrl(path, 60 * 60);

      if (signedError || !signed) {
        // on ignore ce fichier si la signature échoue
        // eslint-disable-next-line no-continue
        continue;
      }

      const size =
        typeof file.metadata?.size === 'number'
          ? (file.metadata.size as number)
          : null;

      talentcardFiles.push({
        name: file.name as string,
        path,
        publicUrl: signed.signedUrl,
        updatedAt: (file.updated_at as string) ?? null,
        size,
      });
    }

    return { talentcardFiles };
  }

  async getCandidateTalentcardFilesByCandidateId(
    candidateId: number,
  ): Promise<{ talentcardFiles: CandidateCvFileItem[] }> {
    if (!candidateId || Number.isNaN(candidateId)) {
      throw new BadRequestException('candidateId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
      .eq('id', candidateId)
      .maybeSingle();

    if (candidateError) {
      throw new BadRequestException(
        candidateError.message || 'Erreur lors du chargement du candidat',
      );
    }

    if (!candidate) {
      return { talentcardFiles: [] };
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';

    const basePath = `candidates/${category}/${candidateId}`;

    const { data: listed, error: listError } = await this.supabase.storage
      .from('tap_files')
      .list(basePath, {
        limit: 100,
      });

    if (listError) {
      throw new BadRequestException(
        listError.message ||
          'Erreur lors du listing des fichiers Talent Card',
      );
    }

    const files = (listed ?? []).filter((f: any) => {
      if (typeof f.name !== 'string') return false;
      const name = f.name.toLowerCase();
      return name.startsWith('talentcard') && name.endsWith('.pdf');
    });

    const talentcardFiles: CandidateCvFileItem[] = [];

    for (const file of files) {
      const path = `${basePath}/${file.name}`;
      const { data: signed, error: signedError } = await this.supabase.storage
        .from('tap_files')
        .createSignedUrl(path, 60 * 60);

      if (signedError || !signed) {
        // on ignore ce fichier si la signature échoue
        // eslint-disable-next-line no-continue
        continue;
      }

      const size =
        typeof file.metadata?.size === 'number'
          ? (file.metadata.size as number)
          : null;

      talentcardFiles.push({
        name: file.name as string,
        path,
        publicUrl: signed.signedUrl,
        updatedAt: (file.updated_at as string) ?? null,
        size,
      });
    }

    return { talentcardFiles };
  }

  async getCandidatePortfolioPdfFiles(
    userId: number,
  ): Promise<CandidatePortfolioPdfFiles> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
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
      return { portfolioShort: [], portfolioLong: [] };
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';
    const candidateId = candidate.id as number;

    const basePath = `candidates/${category}/${candidateId}`;

    const { data: listed, error: listError } = await this.supabase.storage
      .from('tap_files')
      .list(basePath, {
        limit: 100,
      });

    if (listError) {
      throw new BadRequestException(
        listError.message ||
          'Erreur lors du listing des fichiers de portfolio',
      );
    }

    const portfolioShort: CandidateCvFileItem[] = [];
    const portfolioLong: CandidateCvFileItem[] = [];

    const files = (listed ?? []).filter((f: any) => {
      if (typeof f.name !== 'string') return false;
      const name = f.name.toLowerCase();
      const isPdf = name.endsWith('.pdf');
      const startsWithPortfolio = name.startsWith('portfolio');
      if (!isPdf || !startsWithPortfolio) return false;

      // on supporte les 2 variantes : "one-page" et "one_page"
      const isShort =
        name.endsWith('_one-page_fr.pdf') ||
        name.endsWith('_one-page_en.pdf') ||
        name.endsWith('_one_page_fr.pdf') ||
        name.endsWith('_one_page_en.pdf');
      const isLong =
        name.endsWith('_long_fr.pdf') || name.endsWith('_long_en.pdf') ||
        (name.endsWith('_fr.pdf') && !isShort) ||
        (name.endsWith('_en.pdf') && !isShort);

      return isShort || isLong;
    });

    for (const file of files) {
      const name = (file.name as string).toLowerCase();
      const path = `${basePath}/${file.name}`;

      const { data: signed, error: signedError } = await this.supabase.storage
        .from('tap_files')
        .createSignedUrl(path, 60 * 60);

      if (signedError || !signed) {
        // on ignore ce fichier si la signature échoue
        // eslint-disable-next-line no-continue
        continue;
      }

      const size =
        typeof file.metadata?.size === 'number'
          ? (file.metadata.size as number)
          : null;

      const item: CandidateCvFileItem = {
        name: file.name as string,
        path,
        publicUrl: signed.signedUrl,
        updatedAt: (file.updated_at as string) ?? null,
        size,
      };

      const isShort =
        name.endsWith('_one-page_fr.pdf') ||
        name.endsWith('_one-page_en.pdf') ||
        name.endsWith('_one_page_fr.pdf') ||
        name.endsWith('_one_page_en.pdf');
      const isLong =
        name.endsWith('_long_fr.pdf') || name.endsWith('_long_en.pdf') ||
        (name.endsWith('_fr.pdf') && !isShort) ||
        (name.endsWith('_en.pdf') && !isShort);

      if (isShort) {
        portfolioShort.push(item);
      } else if (isLong) {
        portfolioLong.push(item);
      }
    }

    return { portfolioShort, portfolioLong };
  }

  async getCandidatePortfolioPdfFilesByCandidateId(
    candidateId: number,
  ): Promise<CandidatePortfolioPdfFiles> {
    if (!candidateId || Number.isNaN(candidateId)) {
      throw new BadRequestException('candidateId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
      .eq('id', candidateId)
      .maybeSingle();

    if (candidateError) {
      throw new BadRequestException(
        candidateError.message || 'Erreur lors du chargement du candidat',
      );
    }

    if (!candidate) {
      return { portfolioShort: [], portfolioLong: [] };
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';

    const basePath = `candidates/${category}/${candidateId}`;

    const { data: listed, error: listError } = await this.supabase.storage
      .from('tap_files')
      .list(basePath, {
        limit: 100,
      });

    if (listError) {
      throw new BadRequestException(
        listError.message ||
          'Erreur lors du listing des fichiers de portfolio',
      );
    }

    const portfolioShort: CandidateCvFileItem[] = [];
    const portfolioLong: CandidateCvFileItem[] = [];

    const files = (listed ?? []).filter((f: any) => {
      if (typeof f.name !== 'string') return false;
      const name = f.name.toLowerCase();
      const isPdf = name.endsWith('.pdf');
      const startsWithPortfolio = name.startsWith('portfolio');
      if (!isPdf || !startsWithPortfolio) return false;

      const isShort =
        name.endsWith('_one-page_fr.pdf') ||
        name.endsWith('_one-page_en.pdf') ||
        name.endsWith('_one_page_fr.pdf') ||
        name.endsWith('_one_page_en.pdf');
      const isLong =
        name.endsWith('_long_fr.pdf') || name.endsWith('_long_en.pdf') ||
        (name.endsWith('_fr.pdf') && !isShort) ||
        (name.endsWith('_en.pdf') && !isShort);

      return isShort || isLong;
    });

    for (const file of files) {
      const name = (file.name as string).toLowerCase();
      const path = `${basePath}/${file.name}`;

      const { data: signed, error: signedError } = await this.supabase.storage
        .from('tap_files')
        .createSignedUrl(path, 60 * 60);

      if (signedError || !signed) {
        // on ignore ce fichier si la signature échoue
        // eslint-disable-next-line no-continue
        continue;
      }

      const size =
        typeof file.metadata?.size === 'number'
          ? (file.metadata.size as number)
          : null;

      const item: CandidateCvFileItem = {
        name: file.name as string,
        path,
        publicUrl: signed.signedUrl,
        updatedAt: (file.updated_at as string) ?? null,
        size,
      };

      const isShort =
        name.endsWith('_one-page_fr.pdf') ||
        name.endsWith('_one-page_en.pdf') ||
        name.endsWith('_one_page_fr.pdf') ||
        name.endsWith('_one_page_en.pdf');
      const isLong =
        name.endsWith('_long_fr.pdf') || name.endsWith('_long_en.pdf') ||
        (name.endsWith('_fr.pdf') && !isShort) ||
        (name.endsWith('_en.pdf') && !isShort);

      if (isShort) {
        portfolioShort.push(item);
      } else if (isLong) {
        portfolioLong.push(item);
      }
    }

    return { portfolioShort, portfolioLong };
  }

  async uploadCandidateCv(
    userId: number,
    file: any,
  ): Promise<CandidateCvFileItem> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }
    if (!file || !file.buffer) {
      throw new BadRequestException('Fichier CV manquant');
    }
    const mime = (file.mimetype as string | undefined) ?? '';
    if (!mime.includes('pdf')) {
      throw new BadRequestException('Seuls les fichiers PDF sont acceptés');
    }

    const candidate = await this.getOrCreateCandidate(userId);
    const category = (candidate.categorie_profil as string | null) || 'Autres';
    const candidateId = candidate.id as number;
    const basePath = `candidates/${category}/${candidateId}`;

    const safeName = `cv_${Date.now()}.pdf`;
    const path = `${basePath}/${safeName}`;

    const { error: uploadError } = await this.supabase.storage
      .from('tap_files')
      .upload(path, file.buffer, {
        upsert: true,
        contentType: 'application/pdf',
      });

    if (uploadError) {
      throw new BadRequestException(
        uploadError.message || "Erreur lors de l'upload du CV",
      );
    }

    // Optionnel : garder le dernier CV dans la table candidates
    await this.supabase
      .from('candidates')
      .update({ cv_minio_url: path })
      .eq('id', candidateId);

    const { data: signed, error: signedError } = await this.supabase.storage
      .from('tap_files')
      .createSignedUrl(path, 60 * 60);

    if (signedError || !signed) {
      throw new BadRequestException(
        signedError?.message || "Erreur lors de la génération du lien de téléchargement",
      );
    }

    const size =
      typeof file.size === 'number' ? (file.size as number) : null;

    // Fire-and-forget: trigger Flask AI analysis
    const flaskUrl = this.config.get<string>('FLASK_AI_URL');
    if (flaskUrl) {
      try {
        const FormData = require('form-data');
        const http = require('http');
        const https = require('https');
        const { URL } = require('url');

        const form = new FormData();
        form.append('cv_file', file.buffer, { filename: safeName, contentType: 'application/pdf' });
        form.append("existing_candidate_id", String(candidateId));
        form.append('storage_prefix', basePath);

        const parsed = new URL(flaskUrl + '/process');
        const transport = parsed.protocol === 'https:' ? https : http;
        const req = transport.request(
          {
            hostname: parsed.hostname,
            port: parsed.port,
            path: parsed.pathname,
            method: 'POST',
            headers: form.getHeaders(),
            timeout: 300000,
          },
          (res) => {
            let body = '';
            res.on('data', (chunk) => (body += chunk));
            res.on('end', () => {
              if (res.statusCode >= 200 && res.statusCode < 300) {
                console.log('[AI] Analyse lancee pour candidat ' + candidateId);
              } else {
                console.error('[AI] Erreur ' + res.statusCode + ' pour candidat ' + candidateId + ': ' + body);
              }
            });
          },
        );
        req.on('error', (err) => console.error('[AI] Connexion echouee pour candidat ' + candidateId + ':', err.message));
        form.pipe(req);
      } catch (triggerErr) {
        console.error('[AI] Exception trigger:', triggerErr.message);
      }
    }

    return {
      name: safeName,
      path,
      publicUrl: signed.signedUrl,
      updatedAt: new Date().toISOString(),
      size,
    };
  }

  async createRecruiterJob(
    userId: number,
    payload: RecruiterJobPayload,
  ): Promise<{ job: any }> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const title = payload.title?.trim();
    if (!title) {
      throw new BadRequestException('Le titre du poste est obligatoire');
    }

    const bodyToInsert: any = {
      title,
      categorie_profil: payload.categorie_profil ?? null,
      niveau_attendu: payload.niveau_attendu ?? null,
      experience_min: payload.experience_min ?? null,
      presence_sur_site: payload.presence_sur_site ?? null,
      reason: payload.reason ?? null,
      main_mission: payload.main_mission ?? null,
      tasks_other: payload.tasks_other ?? null,
      disponibilite: payload.disponibilite ?? null,
      salary_min: payload.salary_min ?? null,
      salary_max: payload.salary_max ?? null,
      urgent: Boolean(payload.urgent),
      contrat: payload.contrat ?? 'stage',
      niveau_seniorite: payload.niveau_seniorite ?? null,
      entreprise: payload.entreprise ?? null,
      user_id: userId,
    };

    const { data, error } = await this.supabase
      .from('jobs')
      .insert(bodyToInsert)
      .select('*')
      .single();

    if (error || !data) {
      throw new BadRequestException(
        error?.message || 'Erreur lors de la création de l’offre',
      );
    }

    return { job: data };
  }

  async getRecruiterJobsWithCounts(
    userId: number,
  ): Promise<{ jobs: any[] }> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const { data, error } = await this.supabase
      .from('jobs')
      .select(
        `
        id,
        title,
        categorie_profil,
        niveau_attendu,
        experience_min,
        salary_min,
        salary_max,
        urgent,
        entreprise,
        contrat,
        created_at,
        candidate_postule ( id )
      `,
      )
      .eq('user_id', userId)
      .order('created_at', { ascending: false });

    if (error) {
      throw new BadRequestException(
        error.message || 'Erreur lors du chargement des offres',
      );
    }

    const jobs =
      (data ?? []).map((row: any) => ({
        ...row,
        applications_count: Array.isArray(row.candidate_postule)
          ? row.candidate_postule.length
          : 0,
      })) ?? [];

    return { jobs };
  }

  async getRecruiterOverview(
    userId: number,
  ): Promise<RecruiterOverviewStats> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const { data: jobs, error } = await this.supabase
      .from('jobs')
      .select(
        `
        id,
        title,
        categorie_profil,
        urgent,
        created_at,
        candidate_postule ( id, candidate_id, validated_at, status )
      `,
      )
      .eq('user_id', userId);

    if (error) {
      throw new BadRequestException(
        error.message || 'Erreur lors du chargement du dashboard recruteur',
      );
    }

    const safeJobs = (jobs ?? []) as any[];

    const totalJobs = safeJobs.length;

    let totalApplications = 0;
    const candidateIds = new Set<number>();
    let urgentJobs = 0;
    let lastJobDate: string | null = null;

    const categoryCount = new Map<string, number>();
    const applicationsPerJob: { jobId: number; title: string; value: number }[] = [];
    const allApplications: {
      id: number;
      jobId: number;
      validatedAt: string | null;
      status: string | null;
      candidateId: number | null;
    }[] = [];

    for (const job of safeJobs) {
      const apps = Array.isArray(job.candidate_postule)
        ? job.candidate_postule
        : [];

      const count = apps.length;
      totalApplications += count;

      for (const app of apps) {
        const cId =
          typeof app.candidate_id === 'number' ? (app.candidate_id as number) : null;
        if (cId !== null) candidateIds.add(cId);
        allApplications.push({
          id: app.id as number,
          jobId: job.id as number,
          validatedAt: (app.validated_at as string) ?? null,
          status: (app.status as string) ?? null,
          candidateId: cId,
        });
      }

      if (job.urgent) {
        urgentJobs += 1;
      }

      if (job.created_at) {
        const d = new Date(job.created_at as string);
        if (!Number.isNaN(d.getTime())) {
          if (!lastJobDate || d > new Date(lastJobDate)) {
            lastJobDate = d.toISOString();
          }
        }
      }

      const cat = (job.categorie_profil as string | null) || 'Autres';
      categoryCount.set(cat, (categoryCount.get(cat) ?? 0) + 1);

      applicationsPerJob.push({
        jobId: job.id as number,
        title: (job.title as string) ?? 'Offre',
        value: count,
      });
    }

    const jobsPerCategory = Array.from(categoryCount.entries()).map(
      ([label, value]) => ({ label, value }),
    );

    // Trier les candidatures récentes (par validatedAt décroissant)
    const recentSorted = allApplications
      .filter((a) => !!a.validatedAt)
      .sort((a, b) => {
        const da = new Date(a.validatedAt as string).getTime();
        const db = new Date(b.validatedAt as string).getTime();
        return db - da;
      })
      .slice(0, 10);

    let recentApplications: RecruiterOverviewStats['recentApplications'] = [];

    if (recentSorted.length > 0) {
      const candidateIdsArr = Array.from(
        new Set(
          recentSorted
            .map((a) => a.candidateId)
            .filter((id): id is number => typeof id === 'number'),
        ),
      );

      let candidatesMap = new Map<number, { nom: string | null; prenom: string | null }>();
      if (candidateIdsArr.length > 0) {
        const { data: candidatesRows } = await this.supabase
          .from('candidates')
          .select('id, nom, prenom')
          .in('id', candidateIdsArr);

        (candidatesRows ?? []).forEach((row: any) => {
          candidatesMap.set(row.id as number, {
            nom: (row.nom as string) ?? null,
            prenom: (row.prenom as string) ?? null,
          });
        });
      }

      const jobTitleMap = new Map<number, string>();
      safeJobs.forEach((job: any) => {
        jobTitleMap.set(job.id as number, (job.title as string) ?? 'Offre');
      });

      recentApplications = recentSorted.map((a) => {
        const c = a.candidateId ? candidatesMap.get(a.candidateId) : undefined;
        const name =
          c && (c.nom || c.prenom)
            ? [c.prenom, c.nom].filter(Boolean).join(' ')
            : null;
        return {
          id: a.id,
          candidateName: name,
          jobTitle: jobTitleMap.get(a.jobId) ?? 'Offre',
          status: a.status ?? null,
          validatedAt: a.validatedAt,
        };
      });
    }

    // Alertes recruteur simples
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    const offersNoApps7d = safeJobs.filter((job: any) => {
      const createdAt = job.created_at ? new Date(job.created_at as string) : null;
      const apps = Array.isArray(job.candidate_postule)
        ? job.candidate_postule
        : [];
      return (
        createdAt &&
        createdAt < sevenDaysAgo &&
        apps.length === 0
      );
    });

    const urgentNoApps = safeJobs.filter((job: any) => {
      const apps = Array.isArray(job.candidate_postule)
        ? job.candidate_postule
        : [];
      return Boolean(job.urgent) && apps.length === 0;
    });

    const fortyEightHoursAgo = new Date(now.getTime() - 48 * 60 * 60 * 1000);
    const newAppsCount = allApplications.filter((a) => {
      if (!a.validatedAt) return false;
      const d = new Date(a.validatedAt);
      return d > fortyEightHoursAgo;
    }).length;

    const alerts: RecruiterOverviewStats['alerts'] = [];

    if (offersNoApps7d.length > 0) {
      alerts.push({
        type: 'no_apps_7d',
        message: `${offersNoApps7d.length} offre(s) n'ont reçu aucune candidature depuis 7 jours.`,
      });
    }

    if (urgentNoApps.length > 0) {
      alerts.push({
        type: 'urgent_no_apps',
        message: `${urgentNoApps.length} offre(s) urgentes sans candidature.`,
      });
    }

    if (newAppsCount > 0) {
      alerts.push({
        type: 'new_apps',
        message: `${newAppsCount} nouvelle(s) candidature(s) reçue(s) ces dernières 48h.`,
      });
    }

    return {
      totalJobs,
      totalApplications,
      totalCandidates: candidateIds.size,
      urgentJobs,
      lastJobDate,
      jobsPerCategory,
      applicationsPerJob,
      recentApplications,
      alerts,
    };
  }

  async getAllJobsForCandidates(): Promise<{ jobs: PublicJobItem[] }> {
    const { data, error } = await this.supabase
      .from('jobs')
      .select(
        'id, title, categorie_profil, created_at, urgent, location_type',
      )
      .order('created_at', { ascending: false });

    if (error) {
      throw new BadRequestException(
        error.message || 'Erreur lors du chargement des offres',
      );
    }

    const jobs: PublicJobItem[] = (data ?? []).map((row: any) => ({
      id: row.id as number,
      title: (row.title as string) ?? null,
      categorie_profil: (row.categorie_profil as string) ?? null,
      created_at: (row.created_at as string) ?? null,
      urgent: Boolean(row.urgent),
      location_type: row.location_type ?? null,
    }));

    return { jobs };
  }

  async getCandidateScoreFromJson(
    candidateId: number,
  ): Promise<CandidateScoreFromJson> {
    if (!candidateId || Number.isNaN(candidateId)) {
      throw new BadRequestException('candidateId invalide');
    }

    const {
      data: candidate,
      error: candidateError,
    } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
      .eq('id', candidateId)
      .maybeSingle();

    if (candidateError) {
      throw new BadRequestException(
        candidateError.message || 'Erreur lors du chargement du candidat',
      );
    }

    if (!candidate) {
      return {
        candidateId: null,
        scoreGlobal: null,
        decision: null,
        familleDominante: null,
        metadataTimestamp: null,
        metadataSector: null,
        metadataModule: null,
        commentaire: null,
        dimensions: [],
        skills: [],
        softSkills: [],
      };
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';
    const basePath = `candidates/${category}/${candidateId}`;

    const { data: listed, error: listError } = await this.supabase.storage
      .from('tap_files')
      .list(basePath, {
        limit: 100,
      });

    if (listError) {
      throw new BadRequestException(
        listError.message ||
          'Erreur lors du listing des fichiers de scoring',
      );
    }

    const analysisFiles =
      (listed ?? []).filter((f: any) => {
        if (typeof f.name !== 'string') return false;
        const name = f.name.toLowerCase();
        return name.endsWith('_analyse.json') || name.endsWith('a2_analyse.json');
      }) ?? [];

    if (analysisFiles.length === 0) {
      return {
        candidateId,
        scoreGlobal: null,
        decision: null,
        familleDominante: null,
        metadataTimestamp: null,
        metadataSector: null,
        metadataModule: null,
        commentaire: null,
        dimensions: [],
        skills: [],
        softSkills: [],
      };
    }

    const latestFile = analysisFiles
      .slice()
      .sort((a: any, b: any) => {
        const da = a.updated_at ? new Date(a.updated_at as string).getTime() : 0;
        const db = b.updated_at ? new Date(b.updated_at as string).getTime() : 0;
        return db - da;
      })[0];

    const path = `${basePath}/${latestFile.name as string}`;

    const { data: fileData, error: downloadError } = await this.supabase
      .storage
      .from('tap_files')
      .download(path);

    if (downloadError || !fileData) {
      throw new BadRequestException(
        downloadError?.message ||
          'Erreur lors du téléchargement du fichier de scoring',
      );
    }

    const text = await (fileData as any).text();
    let parsed: any;
    try {
      parsed = JSON.parse(text);
    } catch {
      throw new BadRequestException('Fichier de scoring JSON invalide');
    }

    const scoreGlobal =
      typeof parsed?.scores?.score_global === 'number'
        ? (parsed.scores.score_global as number)
        : null;
    const decision =
      typeof parsed?.decision === 'string' ? (parsed.decision as string) : null;
    const familleDominante =
      typeof parsed?.metadata?.famille_dominante === 'string'
        ? (parsed.metadata.famille_dominante as string)
        : null;

    const metadataTimestamp =
      typeof parsed?.metadata?.timestamp === 'string'
        ? (parsed.metadata.timestamp as string)
        : null;
    const metadataSector =
      typeof parsed?.metadata?.sector_detected === 'string'
        ? (parsed.metadata.sector_detected as string)
        : null;
    const metadataModule =
      typeof parsed?.metadata?.module_used === 'string'
        ? (parsed.metadata.module_used as string)
        : null;

    const commentaire =
      typeof parsed?.commentaire_recruteur === 'string'
        ? (parsed.commentaire_recruteur as string)
        : null;

    const dims: { id: string; label: string; score: number }[] = [];
    const dimSrc = parsed?.scores?.dimensions ?? {};

    const pushDim = (id: string, label: string) => {
      const d = dimSrc[id];
      if (!d || typeof d.score !== 'number') return;
      dims.push({
        id,
        label,
        score: d.score as number,
      });
    };

    pushDim('hard_skills_fit', 'Hard skills fit');
    pushDim('preuves_impact', 'Preuves d’impact');
    pushDim('rarete_marche', 'Rareté marché');
    pushDim('coherence_parcours', 'Cohérence parcours');
    pushDim('stabilite_risque', 'Stabilité / risque');
    pushDim('communication_clarte', 'Clarté de communication');

    const skills: {
      name: string;
      score: number;
      status: string;
      scope: string;
    }[] = Array.isArray(parsed?.skills)
      ? parsed.skills.map((s: any) => ({
          name: (s?.name as string) ?? '',
          score:
            typeof s?.score === 'number' ? (s.score as number) : 0,
          status: (s?.status as string) ?? '',
          scope: (s?.scope as string) ?? '',
        }))
      : [];

    const softSkills: { nom: string; niveau: string }[] =
      Array.isArray(parsed?.evaluation_soft_skills_declares)
        ? parsed.evaluation_soft_skills_declares.map((s: any) => ({
            nom: (s?.nom as string) ?? '',
            niveau: (s?.niveau as string) ?? '',
          }))
        : [];

    return {
      candidateId,
      scoreGlobal,
      decision,
      familleDominante,
      metadataTimestamp,
      metadataSector,
      metadataModule,
      commentaire,
      dimensions: dims,
      skills,
      softSkills,
    };
  }

  async deleteCandidateCvFile(userId: number, filePath: string): Promise<void> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }
    if (!filePath) {
      throw new BadRequestException('Chemin du fichier manquant');
    }

    const { data: candidate } = await this.supabase
      .from('candidates')
      .select('id, categorie_profil')
      .eq('user_id', userId)
      .order('created_at', { ascending: true })
      .limit(1)
      .maybeSingle();

    if (!candidate) {
      throw new BadRequestException('Aucun profil candidat associe');
    }

    const category = (candidate.categorie_profil as string | null) || 'Autres';
    const candidateId = candidate.id as number;
    const expectedPrefix = 'candidates/' + category + '/' + candidateId + '/';

    if (!filePath.startsWith(expectedPrefix)) {
      throw new BadRequestException('Acces non autorise a ce fichier');
    }

    const { error } = await this.supabase.storage
      .from('tap_files')
      .remove([filePath]);

    if (error) {
      throw new BadRequestException(error.message || 'Erreur lors de la suppression');
    }
  }
}
