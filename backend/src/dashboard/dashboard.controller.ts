import { Controller, Get, Param } from '@nestjs/common';
import { DashboardService } from './dashboard.service';

@Controller('dashboard')
export class DashboardController {
  constructor(private readonly dashboardService: DashboardService) {}

  @Get('candidat/:userId')
  async getCandidateDashboard(@Param('userId') userId: string) {
    const id = Number.parseInt(userId, 10);
    return this.dashboardService.getCandidateStats(id);
  }
}

