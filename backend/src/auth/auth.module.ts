import { Module } from '@nestjs/common';
import { JwtModule, type JwtModuleOptions } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';

@Module({
  imports: [
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService): JwtModuleOptions => {
        const secret = config.get<string>('JWT_SECRET') ?? 'change-me-in-env';
        const expiresRaw =
          config.get<string>('JWT_EXPIRES_IN') ?? '900'; // 900s = 15min

        // On force ici le typage attendu (number | StringValue)
        const expiresIn = Number.isNaN(Number(expiresRaw))
          ? (expiresRaw as any)
          : Number(expiresRaw);

        return {
          secret,
          signOptions: {
            expiresIn,
          },
        };
      },
    }),
  ],
  controllers: [AuthController],
  providers: [AuthService],
})
export class AuthModule {}
