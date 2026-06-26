# Meetup Helper

Aplikacja do szukania wspólnego terminu wydarzenia lub wyjazdu.

## Uruchomienie

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
- wyliczanie do 10 najbliższych terminów dostępnych dla wszystkich,
- uzupełnianie listy krótszymi propozycjami, gdy pełna długość nie daje 10 opcji,
- logowanie operacji użytkowników w bazie.

Backend używa FastAPI i PostgreSQL uruchamianego w osobnym kontenerze. Frontend jest aplikacją Angular serwowaną przez nginx, który przekazuje żądania `/api` do backendu.
