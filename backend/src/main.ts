import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({
    origin: 'http://localhost:1101',
    credentials: true,
  });
  await app.listen(process.env.PORT ?? 1102);
}
bootstrap();
