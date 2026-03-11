import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // CORS très permissif : accepte toutes les origines (pratique pour dev local + VPS)
  app.enableCors({
    origin: true,          // reflète automatiquement l'origine de la requête
    credentials: true,
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
    allowedHeaders: 'Content-Type, Accept, Authorization',
  });
  await app.listen(process.env.PORT ?? 1102);
}
bootstrap();
