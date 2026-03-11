import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({
    origin: [
      'http://localhost:1101',        // dev local
      'http://168.231.82.55',         // front servi en HTTP sur VPS
      'http://168.231.82.55:1101',    // si tu sers le front sur ce port en VPS
    ],
    credentials: true,
  });
  await app.listen(process.env.PORT ?? 1102);
}
bootstrap();
