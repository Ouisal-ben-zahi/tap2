import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({ origin: true }); // en dev accepte tout ; en prod préciser l’origine du frontend
  await app.listen(process.env.PORT ?? 3000);
}
bootstrap();
