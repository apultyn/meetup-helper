# Meetup Helper

Aplikacja do szukania wspólnego terminu wydarzenia lub wyjazdu.

## Uruchomienie

Przed startem utwórz lokalny plik `.env` na podstawie szablonu i uzupełnij dane bazy:

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

Po starcie:

- frontend: http://localhost:4200
- backend API: http://localhost:8000
- dokumentacja API: http://localhost:8000/docs

## Funkcje

- tworzenie wydarzeń z nazwą, opisem, zakresem dat i długością w dniach,
- unikalny kod wydarzenia,
- dołączanie do wydarzenia po kodzie i loginie,
- ponowne wejście tym samym loginem pozwala edytować swoje deklaracje,
- dodawanie i usuwanie dni albo całych zakresów dni, w których użytkownik jest zajęty,
- wyliczanie wybranej liczby najbliższych terminów dostępnych dla wszystkich (domyślnie 10, maksymalnie 1000),
- szukanie wariantów kompromisowych: najpierw krótszy czas wydarzenia, potem pominięcie jednej, dwóch i kolejnych osób,
- logowanie operacji użytkowników w bazie.

Backend używa FastAPI i PostgreSQL uruchamianego w osobnym kontenerze. Frontend jest aplikacją Angular serwowaną przez nginx, który przekazuje żądania `/api` do backendu.

## Publikacja obrazów

Workflow GitHub Actions buduje i wysyła obrazy zdefiniowane w `docker-compose.yml` po każdym pushu do `main`:

- `msj102/meetup-helper-backend`
- `msj102/meetup-helper-frontend`

W repozytorium GitHub trzeba ustawić zmienne i sekrety używane przez workflow oraz `docker-compose.yml`.

Variables (`Settings` -> `Secrets and variables` -> `Actions` -> `Variables`):

- `POSTGRES_DB`
- `POSTGRES_USER`

Secrets (`Settings` -> `Secrets and variables` -> `Actions` -> `Secrets`):

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `POSTGRES_PASSWORD`
