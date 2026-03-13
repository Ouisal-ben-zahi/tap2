import {
  Injectable,
  ConflictException,
  BadRequestException,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import * as bcrypt from 'bcrypt';
import * as nodemailer from 'nodemailer';

const SALT_ROUNDS = 12;
const CODE_LENGTH = 6;
const CODE_EXPIRY_MINUTES = 15;

export type ProfileRole = 'candidat' | 'recruteur';

export interface RegisterDto {
  email: string;
  password: string;
  role: ProfileRole;
}

export interface SendVerificationDto {
  email: string;
  password: string;
  role: ProfileRole;
}

export interface VerifyAndRegisterDto {
  email: string;
  code: string;
}

export interface LoginDto {
  email: string;
  password: string;
}

export interface RequestPasswordResetDto {
  email: string;
}

export interface RefreshDto {
  refreshToken: string;
}

export interface ResetPasswordDto {
  email: string;
  code: string;
  newPassword: string;
}

@Injectable()
export class AuthService {
  private supabase: SupabaseClient;
  private mailer: nodemailer.Transporter | null = null;

  constructor(
    private config: ConfigService,
    private jwtService: JwtService,
  ) {
    const url = this.config.get<string>('SUPABASE_URL');
    const key = this.config.get<string>('SUPABASE_SERVICE_ROLE_KEY');
    if (!url || !key) {
      throw new Error(
        'SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis',
      );
    }
    this.supabase = createClient(url, key);

    const user = this.config.get<string>('MAILER_USER');
    const pass = this.config.get<string>('MAILER_PASS');
    if (user && pass) {
      this.mailer = nodemailer.createTransport({
        service: 'gmail',
        auth: { user, pass },
      });
    }
  }

  private createAccessToken(payload: {
    id: number;
    email: string;
    role: ProfileRole;
  }): string {
    return this.jwtService.sign({
      sub: payload.id,
      email: payload.email,
      role: payload.role,
    });
  }

  private randomCode(): string {
    let code = '';
    for (let i = 0; i < CODE_LENGTH; i++) {
      code += Math.floor(Math.random() * 10).toString();
    }
    return code;
  }


  private createRefreshToken(payload: {
    id: number;
    email: string;
    role: ProfileRole;
  }): string {
    const secret = this.config.get<string>("JWT_SECRET") ?? "change-me-in-env";
    const expiresRaw = this.config.get<string>("JWT_REFRESH_EXPIRATION") ?? "7d";
    return this.jwtService.sign(
      { sub: payload.id, email: payload.email, role: payload.role, type: "refresh" },
      { secret, expiresIn: expiresRaw as any },
    );
  }

  private buildAuthResponse(user: { id: number; email: string; role: ProfileRole }) {
    const accessToken = this.createAccessToken(user);
    const refreshToken = this.createRefreshToken(user);
    return {
      user: { id: user.id, email: user.email, role: user.role },
      accessToken,
      refreshToken,
    };
  }

  async refresh(rt) {
    if (!rt) throw new (require("@nestjs/common").UnauthorizedException)("Refresh token requis");
    const secret = this.config.get("JWT_SECRET") ?? "change-me-in-env";
    let payload;
    try {
      payload = this.jwtService.verify(rt, { secret });
    } catch {
      throw new (require("@nestjs/common").UnauthorizedException)("Refresh token invalide ou expiré");
    }
    if (payload.type !== "refresh") throw new (require("@nestjs/common").UnauthorizedException)("Token invalide");
    const { data: users, error } = await this.supabase
      .from("users").select("id, email, role").eq("id", payload.sub).limit(1);
    if (error || !users || users.length === 0) throw new (require("@nestjs/common").UnauthorizedException)("Utilisateur introuvable");
    const user = users[0];
    return this.buildAuthResponse(user);
  }

  async sendVerificationEmail(
    dto: SendVerificationDto,
  ): Promise<{ email: string; message: string }> {
    const email = dto.email?.trim().toLowerCase();
    if (!email || !dto.password || !dto.role) {
      throw new BadRequestException(
        'Email, mot de passe et type de profil sont requis',
      );
    }
    if (!['candidat', 'recruteur'].includes(dto.role)) {
      throw new BadRequestException(
        'Type de profil doit être "candidat" ou "recruteur"',
      );
    }
    if (dto.password.length < 8) {
      throw new BadRequestException(
        'Le mot de passe doit contenir au moins 8 caractères',
      );
    }
    const password_hash = await bcrypt.hash(dto.password, SALT_ROUNDS);
    const code = this.randomCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + CODE_EXPIRY_MINUTES);

    const {
      data: existingUsers,
      error: existingError,
    } = await this.supabase
      .from('users')
      .select('id, is_verified')
      .eq('email', email)
      .limit(1);

    if (existingError) {
      throw new BadRequestException(
        existingError.message || 'Erreur lors de la vérification de l’utilisateur',
      );
    }

    let userId: number;

    if (existingUsers && existingUsers.length > 0) {
      const existing = existingUsers[0] as { id: number; is_verified: boolean };
      if (existing.is_verified) {
        throw new ConflictException('Un compte vérifié existe déjà avec cet email');
      }

      const { error: updateError } = await this.supabase
        .from('users')
        .update({ password_hash, role: dto.role })
        .eq('id', existing.id);

      if (updateError) {
        throw new BadRequestException(
          updateError.message || 'Erreur lors de la mise à jour de l’utilisateur',
        );
      }

      userId = existing.id;
    } else {
      const { data: newUser, error: insertUserError } = await this.supabase
        .from('users')
        .insert({
          email,
          password_hash,
          role: dto.role,
          is_verified: false,
        })
        .select('id')
        .single();

      if (insertUserError || !newUser) {
        if (insertUserError?.code === '23505') {
          throw new ConflictException('Un compte existe déjà avec cet email');
        }
        throw new BadRequestException(
          insertUserError?.message || 'Erreur lors de la création du compte',
        );
      }

      userId = newUser.id as number;
    }

    await this.supabase
      .from('email_verification_tokens')
      .update({ used: true })
      .eq('user_id', userId)
      .eq('used', false);

    const { error: tokenError } = await this.supabase
      .from('email_verification_tokens')
      .insert({
        user_id: userId,
        code,
        expires_at: expiresAt.toISOString(),
        used: false,
      });

    if (tokenError) {
      throw new BadRequestException(
        tokenError.message || 'Erreur lors de la génération du code de vérification',
      );
    }

    if (this.mailer) {
      const from =
        this.config.get<string>('MAILER_FROM') ||
        this.config.get<string>('MAILER_USER') ||
        'noreply@tap.com';
      await this.mailer.sendMail({
        from: `"TAP" <${from}>`,
        to: email,
        subject: 'Vérification de votre adresse email - TAP',
        text: `Votre code de vérification TAP : ${code}\n\nCe code expire dans ${CODE_EXPIRY_MINUTES} minutes. Si vous n'avez pas demandé cet email, ignorez-le.`,
        html: `<p>Votre code de vérification TAP : <strong>${code}</strong></p><p>Ce code expire dans ${CODE_EXPIRY_MINUTES} minutes.</p><p>Si vous n'avez pas demandé cet email, ignorez-le.</p>`,
      });
    }

    return {
      email,
      message: this.mailer
        ? `Un email a été envoyé à ${email}. Entrez le code reçu pour créer votre compte.`
        : `Code de vérification (mode dev) : ${code}. Entrez ce code pour créer votre compte.`,
    };
  }

  async verifyAndRegister(
    dto: VerifyAndRegisterDto,
  ): Promise<{ user: { id: number; email: string; role: ProfileRole }; accessToken: string; refreshToken: string }> {
    const email = dto.email?.trim().toLowerCase();
    const code = dto.code?.trim().replace(/\s/g, '');
    if (!email || !code) {
      throw new BadRequestException('Email et code sont requis');
    }

    const { data: users, error: userError } = await this.supabase
      .from('users')
      .select('id, email, role, is_verified')
      .eq('email', email)
      .limit(1);

    if (userError) {
      throw new BadRequestException(
        userError.message || 'Erreur lors de la vérification de l’utilisateur',
      );
    }

    if (!users || users.length === 0) {
      throw new BadRequestException(
        "Aucun compte en attente de vérification pour cet email",
      );
    }

    const user = users[0] as {
      id: number;
      email: string;
      role: ProfileRole;
      is_verified: boolean;
    };

    const {
      data: tokens,
      error: tokenError,
    } = await this.supabase
      .from('email_verification_tokens')
      .select('id, code, expires_at, used')
      .eq('user_id', user.id)
      .eq('code', code)
      .eq('used', false)
      .order('created_at', { ascending: false })
      .limit(1);

    if (tokenError) {
      throw new BadRequestException(
        tokenError.message || 'Erreur lors de la vérification du code',
      );
    }

    if (!tokens || tokens.length === 0) {
      throw new BadRequestException('Code invalide ou expiré');
    }

    const token = tokens[0] as {
      id: number;
      expires_at: string;
      used: boolean;
    };

    const expiresAt = new Date(token.expires_at);
    if (expiresAt < new Date()) {
      await this.supabase
        .from('email_verification_tokens')
        .update({ used: true })
        .eq('id', token.id);
      throw new BadRequestException('Code expiré. Demandez un nouveau code.');
    }

    const { error: updateUserError } = await this.supabase
      .from('users')
      .update({ is_verified: true })
      .eq('id', user.id);

    if (updateUserError) {
      throw new BadRequestException(
        updateUserError.message || 'Erreur lors de la validation du compte',
      );
    }

    await this.supabase
      .from('email_verification_tokens')
      .update({ used: true })
      .eq('id', token.id);

    return this.buildAuthResponse({ id: user.id, email: user.email, role: user.role as ProfileRole });
  }

  async register(dto: RegisterDto): Promise<{
    id: number;
    email: string;
    role: ProfileRole;
  }> {
    const email = dto.email?.trim().toLowerCase();
    if (!email || !dto.password || !dto.role) {
      throw new BadRequestException(
        'Email, mot de passe et type de profil sont requis',
      );
    }
    if (!['candidat', 'recruteur'].includes(dto.role)) {
      throw new BadRequestException(
        'Type de profil doit être "candidat" ou "recruteur"',
      );
    }
    if (dto.password.length < 8) {
      throw new BadRequestException(
        'Le mot de passe doit contenir au moins 8 caractères',
      );
    }

    const password_hash = await bcrypt.hash(dto.password, SALT_ROUNDS);

    const { data, error } = await this.supabase
      .from('users')
      .insert({
        email,
        password_hash,
        role: dto.role,
        is_verified: false,
      })
      .select('id, email, role')
      .single();

    if (error) {
      if (error.code === '23505') {
        throw new ConflictException('Un compte existe déjà avec cet email');
      }
      throw new BadRequestException(
        error.message || 'Erreur lors de la création du compte',
      );
    }

    return {
      id: data.id,
      email: data.email,
      role: data.role as ProfileRole,
    };
  }

  async login(dto: LoginDto): Promise<{
    user: { id: number; email: string; role: ProfileRole };
    accessToken: string;
    refreshToken: string;
  }> {
    const email = dto.email?.trim().toLowerCase();
    if (!email || !dto.password) {
      throw new BadRequestException('Email et mot de passe sont requis');
    }

    const { data: users, error } = await this.supabase
      .from('users')
      .select('id, email, role, password_hash, is_verified')
      .eq('email', email)
      .limit(1);

    if (error) {
      throw new BadRequestException(
        error.message || 'Erreur lors de la vérification des identifiants',
      );
    }

    if (!users || users.length === 0) {
      throw new UnauthorizedException('Identifiants invalides');
    }

    const user = users[0] as {
      id: number;
      email: string;
      role: ProfileRole;
      password_hash: string;
      is_verified: boolean;
    };

    const match = await bcrypt.compare(dto.password, user.password_hash);
    if (!match) {
      throw new UnauthorizedException('Identifiants invalides');
    }

    if (!user.is_verified) {
      throw new UnauthorizedException(
        'Votre adresse email n’est pas encore vérifiée',
      );
    }

    return this.buildAuthResponse({ id: user.id, email: user.email, role: user.role });
  }

  async requestPasswordReset(
    dto: RequestPasswordResetDto,
  ): Promise<{ email: string; message: string }> {
    const email = dto.email?.trim().toLowerCase();
    if (!email) {
      throw new BadRequestException('Email est requis');
    }

    const {
      data: users,
      error: userError,
    } = await this.supabase
      .from('users')
      .select('id, email, is_verified')
      .eq('email', email)
      .limit(1);

    if (userError) {
      throw new BadRequestException(
        userError.message || "Erreur lors de la recherche de l'utilisateur",
      );
    }

    if (!users || users.length === 0) {
      // On renvoie un message générique pour ne pas révéler si l'email existe
      return {
        email,
        message:
          "Si un compte existe pour cet email, un code de réinitialisation a été envoyé.",
      };
    }

    const user = users[0] as { id: number; email: string; is_verified: boolean };

    const code = this.randomCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + CODE_EXPIRY_MINUTES);

    await this.supabase
      .from('password_reset_tokens')
      .update({ is_used: true })
      .eq('user_id', user.id)
      .eq('is_used', false);

    const { error: tokenError } = await this.supabase
      .from('password_reset_tokens')
      .insert({
        user_id: user.id,
        token: code,
        expires_at: expiresAt.toISOString(),
        is_used: false,
      });

    if (tokenError) {
      throw new BadRequestException(
        tokenError.message ||
          'Erreur lors de la génération du code de réinitialisation',
      );
    }

    if (this.mailer) {
      const from =
        this.config.get<string>('MAILER_FROM') ||
        this.config.get<string>('MAILER_USER') ||
        'noreply@tap.com';
      await this.mailer.sendMail({
        from: `"TAP" <${from}>`,
        to: email,
        subject: 'Réinitialisation de votre mot de passe TAP',
        text: `Votre code de réinitialisation TAP : ${code}\n\nCe code expire dans ${CODE_EXPIRY_MINUTES} minutes. Si vous n'avez pas demandé cet email, ignorez-le.`,
        html: `<p>Vous avez demandé à réinitialiser votre mot de passe TAP.</p><p>Votre code : <strong>${code}</strong></p><p>Ce code expire dans ${CODE_EXPIRY_MINUTES} minutes.</p><p>Si vous n'êtes pas à l'origine de cette demande, ignorez simplement cet email.</p>`,
      });
    }

    return {
      email,
      message:
        "Si un compte existe pour cet email, un code de réinitialisation a été envoyé.",
    };
  }

  async resetPassword(
    dto: ResetPasswordDto,
  ): Promise<{ email: string; message: string }> {
    const email = dto.email?.trim().toLowerCase();
    const code = dto.code?.trim().replace(/\s/g, '');
    const newPassword = dto.newPassword;

    if (!email || !code || !newPassword) {
      throw new BadRequestException(
        'Email, code et nouveau mot de passe sont requis',
      );
    }

    if (newPassword.length < 8) {
      throw new BadRequestException(
        'Le mot de passe doit contenir au moins 8 caractères',
      );
    }

    const {
      data: users,
      error: userError,
    } = await this.supabase
      .from('users')
      .select('id, email')
      .eq('email', email)
      .limit(1);

    if (userError) {
      throw new BadRequestException(
        userError.message ||
          "Erreur lors de la vérification de l'utilisateur pour la réinitialisation",
      );
    }

    if (!users || users.length === 0) {
      throw new BadRequestException(
        'Code invalide ou expiré pour cet email',
      );
    }

    const user = users[0] as { id: number; email: string };

    const {
      data: tokens,
      error: tokenError,
    } = await this.supabase
      .from('password_reset_tokens')
      .select('id, token, expires_at, is_used')
      .eq('user_id', user.id)
      .eq('token', code)
      .eq('is_used', false)
      .order('created_at', { ascending: false })
      .limit(1);

    if (tokenError) {
      throw new BadRequestException(
        tokenError.message || 'Erreur lors de la vérification du code',
      );
    }

    if (!tokens || tokens.length === 0) {
      throw new BadRequestException('Code invalide ou expiré');
    }

    const token = tokens[0] as {
      id: number;
      token: string;
      expires_at: string;
      is_used: boolean;
    };

    const expiresAt = new Date(token.expires_at);
    if (expiresAt < new Date()) {
      await this.supabase
        .from('password_reset_tokens')
        .update({ is_used: true })
        .eq('id', token.id);
      throw new BadRequestException('Code expiré. Demandez un nouveau code.');
    }

    const password_hash = await bcrypt.hash(newPassword, SALT_ROUNDS);

    const { error: updateError } = await this.supabase
      .from('users')
      .update({ password_hash })
      .eq('id', user.id);

    if (updateError) {
      throw new BadRequestException(
        updateError.message || 'Erreur lors de la mise à jour du mot de passe',
      );
    }

    await this.supabase
      .from('password_reset_tokens')
      .update({ is_used: true })
      .eq('id', token.id);

    return {
      email: user.email,
      message: 'Votre mot de passe a été réinitialisé avec succès.',
    };
  }
}
