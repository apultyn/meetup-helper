# Meetup helper

Aplikacja mająca pomagać w znalezieniu terminu na wspólne wydarzenie/wyjazd.

## Założenia

- użytkownik może stworzyć nowe wydarzenie, podając:
    - nazwę wydarzenia
    - krótki opis
    - zakres dni w których ma się odbyć dane wydarzenie
    - długość wydarzenia w dniach
- wydarzenie posiada unikalny kod
- użytkownicy mogą dołączać do wydarzenia, podając unikalny kod
    - po podaniu kodu użytkownik jest proszony o podanie loginu
    - jeżeli taki użytkownik już istnieje w wydarzeniu to system pozwala na zmiany deklaracji tego użytkownika (bez haseł, zakładamy że nikomu nie zależy na zepsuciu wydarzenia)
    - jeżeli użytkownika o podanym loginie nie ma to jest dodawany do wydarzenia
- każdy użytkownik (łącznie z autorem wydarzenia) może dodawać do wspólnego kalendarza dni, w których jest zajęty
    - fajnie by było aby użytkownik miał gdzieś panel z listą swoich blokerów, które mógłby jednym przyciskiem usuwać
- po naciśnięciu przycisku "wylicz", system podaje np. top 10 dostępnych terminów
    - jeżeli nie ma możliwego terminu, to system skraca czas wydarzenia o 1 i próbuje do skutku (propozycja musi być oznaczona, że jest krótsza)

## Szczegóły techniczne

- backend - FastAPI
- frontend - Angular
- baza danych dowolna
- wszystko wdrażane w kontenerach Docker
- operacje użytkowników powinny być logowane