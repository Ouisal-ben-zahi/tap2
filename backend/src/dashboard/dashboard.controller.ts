import { Body, Controller, Delete, Get, Param, Post, Query, Req, UploadedFile, UseGuards, UseInterceptors } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { FileInterceptor } from '@nestjs/platform-express';
import { DashboardService, type RecruiterJobPayload } from './dashboard.service';

@Controller('dashboard')
export class DashboardController {
  constructor(private readonly dashboardService: DashboardService) {}


  // === JWT-based routes (no userId in URL) ===

  @Get('candidat/stats')
  @UseGuards(AuthGuard('jwt'))
  async getCandidateStatsByJwt(@Req() req: any) {
    return this.dashboardService.getCandidateStats(req.user.sub);
  }

  @Get('candidat/portfolio')
  @UseGuards(AuthGuard('jwt'))
  async getCandidatePortfolioByJwt(@Req() req: any) {
    return this.dashboardService.getCandidatePortfolio(req.user.sub);
  }

  @Get('candidat/applications')
  @UseGuards(AuthGuard('jwt'))
  async getCandidateApplicationsByJwt(@Req() req: any) {
    return this.dashboardService.getCandidateApplications(req.user.sub);
  }

  @Get('candidat/cv-files')
  @UseGuards(AuthGuard('jwt'))
  async getCandidateCvFilesByJwt(@Req() req: any) {
    return this.dashboardService.getCandidateCvFiles(req.user.sub);
  }

  @Get('candidat/talentcard-files')
  @UseGuards(AuthGuard('jwt'))
  async getCandidateTalentcardFilesByJwt(@Req() req: any) {
    return this.dashboardService.getCandidateTalentcardFiles(req.user.sub);
  }

  @Get('candidat/portfolio-pdf-files')
  @UseGuards(AuthGuard('jwt'))
  async getCandidatePortfolioPdfFilesByJwt(@Req() req: any) {
    return this.dashboardService.getCandidatePortfolioPdfFiles(req.user.sub);
  }

  @Post('candidat/upload-cv')
  @UseGuards(AuthGuard('jwt'))
  @UseInterceptors(FileInterceptor('file'))
  async uploadCandidateCvByJwt(@Req() req: any, @UploadedFile() file: any) {
    return this.dashboardService.uploadCandidateCv(req.user.sub, file);
  }

  @Delete("candidat/cv-file")
  @UseGuards(AuthGuard("jwt"))
  async deleteCandidateCvFileByJwt(@Req() req: any, @Query("path") path: string) {
    await this.dashboardService.deleteCandidateCvFile(req.user.sub, path);
    return { success: true };
  
  }


  @Get('recruteur/jobs')
  @UseGuards(AuthGuard('jwt'))
  async getRecruiterJobsByJwt(@Req() req: any) {
    return this.dashboardService.getRecruiterJobsWithCounts(req.user.sub);
  }

  @Post('recruteur/jobs')
  @UseGuards(AuthGuard('jwt'))
  async createRecruiterJobByJwt(@Req() req: any, @Body() body: RecruiterJobPayload) {
    return this.dashboardService.createRecruiterJob(req.user.sub, body);
  }

  @Get('recruteur/overview')
  @UseGuards(AuthGuard('jwt'))
  async getRecruiterOverviewByJwt(@Req() req: any) {
    return this.dashboardService.getRecruiterOverview(req.user.sub);
  }

  // === Legacy routes with userId in URL ===

  @Get('candidat/:userId')
  async getCandidateDashboard(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getCandidateStats(id);
  }

  @Get('candidat/:userId/portfolio')
  async getCandidatePortfolio(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getCandidatePortfolio(id);
  }

  @Get('candidat/:userId/applications')
  async getCandidateApplications(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getCandidateApplications(id);
  }

  @Get('candidat/:userId/cv-files')
  async getCandidateCvFiles(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getCandidateCvFiles(id);
  }

  @Get('candidat/:userId/talentcard-files')
  async getCandidateTalentcardFiles(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getCandidateTalentcardFiles(id);
  }

  @Get('candidat/:userId/portfolio-pdf-files')
  async getCandidatePortfolioPdfFiles(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getCandidatePortfolioPdfFiles(id);
  }

  // === Versions basées sur candidateId directement ===

  @Get('candidat-id/:candidateId/cv-files')
  async getCandidateCvFilesByCandidateId(
    @Param('candidateId') candidateId: string,
  ) {
    const id = Number.parseInt(candidateId, 10);
    return this.dashboardService.getCandidateCvFilesByCandidateId(id);
  }

  @Get('candidat-id/:candidateId/talentcard-files')
  async getCandidateTalentcardFilesByCandidateId(
    @Param('candidateId') candidateId: string,
  ) {
    const id = Number.parseInt(candidateId, 10);
    return this.dashboardService.getCandidateTalentcardFilesByCandidateId(id);
  }

  @Get('candidat-id/:candidateId/score-json')
  async getCandidateScoreFromJson(@Param('candidateId') candidateId: string) {
    const id = Number.parseInt(candidateId, 10);
    return this.dashboardService.getCandidateScoreFromJson(id);
  }

  @Get('candidat-id/:candidateId/portfolio-pdf-files')
  async getCandidatePortfolioPdfFilesByCandidateId(
    @Param('candidateId') candidateId: string,
  ) {
    const id = Number.parseInt(candidateId, 10);
    return this.dashboardService.getCandidatePortfolioPdfFilesByCandidateId(id);
  }

  @Post('candidat/:userId/upload-cv')
  @UseInterceptors(FileInterceptor('file'))
  async uploadCandidateCv(
    @Param('userId') userId: string,
    @UploadedFile() file: any,
  ) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.uploadCandidateCv(id, file);
  }

  @Post('recruteur/:userId/jobs')
  async createRecruiterJob(
    @Param('userId') userId: string,
    @Body() body: RecruiterJobPayload,
  ) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.createRecruiterJob(id, body);
  }

  @Get('recruteur/:userId/jobs')
  async getRecruiterJobs(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getRecruiterJobsWithCounts(id);
  }

  @Get('recruteur/:userId/overview')
  async getRecruiterOverview(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getRecruiterOverview(id);
  }

  // Offres visibles côté candidat (liste globale des jobs)
  @Get('jobs')
  async getAllJobsForCandidates() {
    return this.dashboardService.getAllJobsForCandidates();
  }
}

