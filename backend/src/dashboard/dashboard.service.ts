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

export interface CandidatePortfolioPdfFiles {
  portfolioShort: CandidateCvFileItem[];
  portfolioLong: CandidateCvFileItem[];
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

  async getCandidateStats(userId: number): Promise<CandidateDashboardStats> {
    if (!userId || Number.isNaN(userId)) {
      throw new BadRequestException('userId invalide');
    }

    const candidate = await this.getCandidateIdForUser(userId);

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
        name.endsWith('_long_fr.pdf') || name.endsWith('_long_en.pdf');

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
        name.endsWith('_long_fr.pdf') || name.endsWith('_long_en.pdf');

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
      throw new BadRequestException(
        "Aucun profil candidat associé à cet utilisateur",
      );
    }

    const category =
      (candidate.categorie_profil as string | null) || 'Autres';
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

    return {
      name: safeName,
      path,
      publicUrl: signed.signedUrl,
      updatedAt: new Date().toISOString(),
      size,
    };
  }
}

