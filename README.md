# telegram-booking-bot

Telegram bot for booking appointments: barbershop, clinic, tutor, car wash, any service that works with time slots.
Clients pick a service, a day and a free time, get a confirmation and a reminder one hour before.
The owner manages services, working hours and bookings right from Telegram.

Built with [aiogram 3](https://docs.aiogram.dev/), SQLite and APScheduler. No external services required.

## Features

**For clients**
- `/start` menu with inline buttons, no commands to remember
- Choose service → day → time, only free slots are shown
- Confirmation screen before saving
- `/my` list of upcoming bookings with one-tap cancel
- Reminder one hour before the appointment

**For the owner (admin)**
- `/addservice Name | minutes | price`, `/hideservice id`, `/showservice id`
- `/hours mon 09:00-18:00`, `/hours sun off` to set the weekly schedule
- `/bookings [date]` to see the day's schedule with client names
- `/cancel id` cancels a booking and notifies the client

**Under the hood**
- Overlap check on write, so two clients can't take the same slot
- Slot length follows service duration, step is configurable
- Time zone aware, all times are stored with offsets
- Tests for slot math, repository and reminders; CI runs lint and tests

## Quick start

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Find your Telegram user id (for example via [@userinfobot](https://t.me/userinfobot)).
3. Configure:

```bash
cp .env.example .env
# edit BOT_TOKEN, ADMIN_IDS and TZ
```

4. Run with Docker:

```bash
docker compose up -d --build
```

or locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m bot
```

5. In Telegram, as admin, set up the schedule and services:

```
/hours mon 10:00-19:00
/hours tue 10:00-19:00
/hours sat 11:00-16:00
/addservice Haircut | 30 | 5000
/addservice Haircut + beard | 60 | 8000
```

Clients can now `/start` the bot and book.

## Configuration

| Variable        | Default            | Description                                   |
|-----------------|--------------------|-----------------------------------------------|
| `BOT_TOKEN`     | —                  | Token from BotFather                          |
| `ADMIN_IDS`     | —                  | Comma separated user ids with admin access    |
| `DB_PATH`       | `data/bookings.db` | SQLite file location                          |
| `TZ`            | `UTC`              | Time zone of the business, e.g. `Europe/Berlin` |
| `SLOT_STEP_MIN` | `30`               | Step between slot start times, minutes        |
| `DAYS_AHEAD`    | `7`                | How many days ahead clients can book          |

## Project layout

```
bot/
  __main__.py        entry point, wiring, scheduler
  config.py          settings from environment
  db.py              SQLite schema and connection
  repository.py      all database access
  keyboards.py       inline keyboards and callback data
  texts.py           user-facing strings
  handlers/          start menu, booking flow, my bookings, admin
  services/          slot calculation, reminders
tests/
```

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format .
pytest
```

## Ideas for extension

- Multiple staff members with separate calendars
- Payments through Telegram Payments or Stripe
- Export of bookings to Google Calendar
- Localisation (texts live in one file, so it's a small change)

## License

MIT
