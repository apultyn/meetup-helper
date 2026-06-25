import { CommonModule } from '@angular/common';
import { Component, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

import { ApiService } from './api.service';
import { Blocker, BlockerRangeCreate, EventRead, Participant, SuggestionResponse } from './models';

interface CalendarDay {
  date: string | null;
  label: string;
  isInRange: boolean;
}

interface CalendarMonth {
  label: string;
  days: CalendarDay[];
}

interface PendingJoin {
  code: string;
  login: string;
  isExistingParticipant: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnDestroy {
  createForm = {
    name: '',
    description: '',
    start_date: '',
    end_date: '',
    duration_days: 1,
    author_login: ''
  };

  joinForm = {
    code: '',
    login: ''
  };

  event: EventRead | null = null;
  currentLogin = '';
  calendarMonths: CalendarMonth[] = [];
  weekdayLabels = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'];
  newBlockerDate = '';
  newBlockerRange = {
    start_date: '',
    end_date: ''
  };
  suggestions: SuggestionResponse | null = null;
  loading = false;
  error = '';
  notice = '';
  pendingJoin: PendingJoin | null = null;
  joinConfirmationSeconds = 0;
  private joinConfirmationTimerId: number | null = null;

  constructor(private readonly api: ApiService) {}

  ngOnDestroy(): void {
    this.clearJoinCountdown();
  }

  get currentParticipant(): Participant | null {
    if (!this.event || !this.currentLogin) {
      return null;
    }
    const loginKey = this.currentLogin.trim().toLocaleLowerCase('pl-PL');
    return this.event.participants.find((participant) => participant.login.toLocaleLowerCase('pl-PL') === loginKey) ?? null;
  }

  get myBlockers(): Blocker[] {
    return this.currentParticipant?.blockers ?? [];
  }

  isCalendarDayBlocked(day: CalendarDay): boolean {
    return day.date ? this.isMyBlocked(day.date) : false;
  }

  calendarDayLabel(day: CalendarDay): string | null {
    if (!day.date) {
      return null;
    }

    const state = this.isMyBlocked(day.date) ? 'zajęty' : 'wolny';
    return `${this.formatDate(day.date)}, ${state}`;
  }

  createEvent(): void {
    this.runRequest(() => {
      const payload = {
        ...this.createForm,
        duration_days: Number(this.createForm.duration_days)
      };

      this.api.createEvent(payload).subscribe({
        next: (event) => {
          this.setActiveEvent(event, this.createForm.author_login);
          this.notice = `Utworzono wydarzenie. Kod: ${event.code}`;
          this.createForm = {
            name: '',
            description: '',
            start_date: '',
            end_date: '',
            duration_days: 1,
            author_login: ''
          };
          this.loading = false;
        },
        error: (error: HttpErrorResponse) => this.handleError(error)
      });
    });
  }

  prepareJoinEvent(): void {
    const code = this.joinForm.code.trim().toUpperCase();
    const login = this.joinForm.login.trim();

    if (!code || !login) {
      this.error = 'Podaj kod wydarzenia i login.';
      return;
    }

    this.closeJoinConfirmation();

    this.runRequest(() => {
      this.api.getEvent(code).subscribe({
        next: (event) => {
          const loginKey = login.toLocaleLowerCase('pl-PL');
          this.pendingJoin = {
            code,
            login,
            isExistingParticipant: event.participants.some(
              (participant) => participant.login.toLocaleLowerCase('pl-PL') === loginKey
            )
          };
          this.startJoinCountdown();
          this.loading = false;
        },
        error: (error: HttpErrorResponse) => this.handleError(error)
      });
    });
  }

  confirmJoinEvent(): void {
    if (!this.pendingJoin || this.joinConfirmationSeconds > 0) {
      return;
    }

    const pendingJoin = this.pendingJoin;
    this.clearJoinCountdown();

    this.runRequest(() => {
      this.api.joinEvent(pendingJoin.code, { login: pendingJoin.login }).subscribe({
        next: (event) => {
          this.pendingJoin = null;
          this.setActiveEvent(event, pendingJoin.login);
          this.notice = pendingJoin.isExistingParticipant
            ? `Zalogowano jako ${pendingJoin.login}.`
            : `Dołączono do wydarzenia jako ${pendingJoin.login}.`;
          this.loading = false;
        },
        error: (error: HttpErrorResponse) => this.handleError(error)
      });
    });
  }

  cancelJoinConfirmation(): void {
    this.closeJoinConfirmation();
    this.loading = false;
  }

  logout(): void {
    this.event = null;
    this.currentLogin = '';
    this.calendarMonths = [];
    this.closeJoinConfirmation();
    this.newBlockerDate = '';
    this.newBlockerRange = {
      start_date: '',
      end_date: ''
    };
    this.suggestions = null;
    this.error = '';
    this.notice = 'Wylogowano z wydarzenia.';
    this.loading = false;
  }

  refreshEvent(): void {
    if (!this.event) {
      return;
    }

    this.runRequest(() => {
      this.api.getEvent(this.event?.code ?? '').subscribe({
        next: (event) => {
          this.setActiveEvent(event, this.currentLogin);
          this.notice = 'Odświeżono dane wydarzenia.';
          this.loading = false;
        },
        error: (error: HttpErrorResponse) => this.handleError(error)
      });
    });
  }

  addBlockerFromInput(): void {
    if (!this.newBlockerDate) {
      this.error = 'Wybierz datę blokera.';
      return;
    }
    this.addBlockers([this.newBlockerDate]);
  }

  addBlockerRangeFromInput(): void {
    const startDate = this.newBlockerRange.start_date;
    const endDate = this.newBlockerRange.end_date;

    if (!startDate || !endDate) {
      this.error = 'Wybierz początek i koniec zakresu.';
      return;
    }

    if (this.parseIsoDate(endDate) < this.parseIsoDate(startDate)) {
      this.error = 'Koniec zakresu nie może być wcześniejszy niż początek.';
      return;
    }

    this.addBlockers([], [{ start_date: startDate, end_date: endDate }]);
  }

  toggleCalendarDay(day: CalendarDay): void {
    if (!day.date || !day.isInRange) {
      return;
    }

    this.toggleBlocker(day.date);
  }

  toggleBlocker(day: string): void {
    const blocker = this.myBlockers.find((item) => item.date === day);
    if (blocker) {
      this.deleteBlocker(blocker.id);
      return;
    }
    this.addBlockers([day]);
  }

  deleteBlocker(blockerId: number): void {
    if (!this.event || !this.currentLogin) {
      return;
    }

    this.runRequest(() => {
      this.api.deleteBlocker(this.event?.code ?? '', blockerId, this.currentLogin).subscribe({
        next: (event) => {
          this.setActiveEvent(event, this.currentLogin);
          this.notice = 'Usunięto bloker.';
          this.loading = false;
        },
        error: (error: HttpErrorResponse) => this.handleError(error)
      });
    });
  }

  calculate(): void {
    if (!this.event) {
      return;
    }

    this.runRequest(() => {
      this.api.calculateSuggestions(this.event?.code ?? '').subscribe({
        next: (suggestions) => {
          this.suggestions = suggestions;
          this.notice = suggestions.suggestions.length > 0
            ? 'Wyliczono dostępne terminy.'
            : 'Brak dostępnych terminów nawet po skróceniu wydarzenia.';
          this.loading = false;
        },
        error: (error: HttpErrorResponse) => this.handleError(error)
      });
    });
  }

  isMyBlocked(day: string): boolean {
    return this.myBlockers.some((blocker) => blocker.date === day);
  }

  formatDate(value: string): string {
    const date = this.parseIsoDate(value);
    return new Intl.DateTimeFormat('pl-PL', {
      weekday: 'short',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(date);
  }

  private addBlockers(dates: string[], ranges: BlockerRangeCreate[] = []): void {
    if (!this.event || !this.currentLogin) {
      return;
    }

    this.runRequest(() => {
      this.api.addBlockers(this.event?.code ?? '', { login: this.currentLogin, dates, ranges }).subscribe({
        next: (event) => {
          this.setActiveEvent(event, this.currentLogin);
          this.newBlockerDate = '';
          this.newBlockerRange = {
            start_date: '',
            end_date: ''
          };
          this.notice = 'Zapisano bloker.';
          this.loading = false;
        },
        error: (error: HttpErrorResponse) => this.handleError(error)
      });
    });
  }

  private setActiveEvent(event: EventRead, login: string): void {
    this.event = event;
    this.currentLogin = login;
    this.calendarMonths = this.buildCalendarMonths(event.start_date, event.end_date);
    this.suggestions = null;
    this.error = '';
  }

  private runRequest(start: () => void): void {
    this.loading = true;
    this.error = '';
    this.notice = '';
    start();
  }

  private startJoinCountdown(): void {
    this.clearJoinCountdown();
    this.joinConfirmationSeconds = 5;
    this.joinConfirmationTimerId = window.setInterval(() => {
      if (this.joinConfirmationSeconds <= 1) {
        this.clearJoinCountdown();
        return;
      }

      this.joinConfirmationSeconds -= 1;
    }, 1000);
  }

  private clearJoinCountdown(): void {
    if (this.joinConfirmationTimerId !== null) {
      window.clearInterval(this.joinConfirmationTimerId);
      this.joinConfirmationTimerId = null;
    }

    this.joinConfirmationSeconds = 0;
  }

  private closeJoinConfirmation(): void {
    this.pendingJoin = null;
    this.clearJoinCountdown();
  }

  private handleError(error: HttpErrorResponse): void {
    const detail: unknown = error.error?.detail;

    if (Array.isArray(detail)) {
      this.error = detail.map((item) => item.msg ?? String(item)).join(' ');
    } else if (typeof detail === 'string') {
      this.error = detail;
    } else {
      this.error = 'Operacja nie powiodła się.';
    }

    this.loading = false;
  }

  private buildCalendarMonths(startValue: string, endValue: string): CalendarMonth[] {
    const start = this.parseIsoDate(startValue);
    const end = this.parseIsoDate(endValue);
    const monthCursor = new Date(start.getFullYear(), start.getMonth(), 1);
    const lastMonth = new Date(end.getFullYear(), end.getMonth(), 1);
    const months: CalendarMonth[] = [];

    while (monthCursor <= lastMonth) {
      months.push(this.buildCalendarMonth(monthCursor, start, end));
      monthCursor.setMonth(monthCursor.getMonth() + 1);
    }

    return months;
  }

  private buildCalendarMonth(monthValue: Date, rangeStart: Date, rangeEnd: Date): CalendarMonth {
    const year = monthValue.getFullYear();
    const month = monthValue.getMonth();
    const firstDay = new Date(year, month, 1);
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const leadingEmptyDays = (firstDay.getDay() + 6) % 7;
    const days: CalendarDay[] = [];

    for (let index = 0; index < leadingEmptyDays; index += 1) {
      days.push({ date: null, label: '', isInRange: false });
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const current = new Date(year, month, day);
      days.push({
        date: this.toIsoDate(current),
        label: String(day),
        isInRange: current >= rangeStart && current <= rangeEnd
      });
    }

    while (days.length % 7 !== 0) {
      days.push({ date: null, label: '', isInRange: false });
    }

    return {
      label: new Intl.DateTimeFormat('pl-PL', { month: 'long', year: 'numeric' }).format(firstDay),
      days
    };
  }

  private parseIsoDate(value: string): Date {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  private toIsoDate(value: Date): string {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
}
