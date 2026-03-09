import { Body, Controller, Post } from '@nestjs/common';
import {
  AuthService,
  type RegisterDto,
  type SendVerificationDto,
  type VerifyAndRegisterDto,
  type LoginDto,
} from './auth.service';

@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Post('send-verification')
  async sendVerification(@Body() dto: SendVerificationDto) {
    return this.authService.sendVerificationEmail(dto);
  }

  @Post('verify-and-register')
  async verifyAndRegister(@Body() dto: VerifyAndRegisterDto) {
    return this.authService.verifyAndRegister(dto);
  }

  @Post('login')
  async login(@Body() dto: LoginDto) {
    return this.authService.login(dto);
  }

  @Post('register')
  async register(@Body() dto: RegisterDto) {
    return this.authService.register(dto);
  }
}
