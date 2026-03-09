import { Controller, Get, Param, Post, UploadedFile, UseInterceptors } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { DashboardService } from './dashboard.service';

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

  @Post('candidat/:userId/upload-cv')
  @UseInterceptors(FileInterceptor('file'))
  async uploadCandidateCv(
    @Param('userId') userId: string,
    @UploadedFile() file: any,
  ) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.uploadCandidateCv(id, file);
  }
}

