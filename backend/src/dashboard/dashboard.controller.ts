import { Body, Controller, Get, Param, Post, UploadedFile, UseInterceptors } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { DashboardService, type RecruiterJobPayload } from './dashboard.service';

@Controller('dashboard')
export class DashboardController {
  constructor(private readonly dashboardService: DashboardService) {}

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
}

