# Daffodil AI Club — Newcomer Quiz

A quiz site for AI Club orientation. A newcomer types their name, answers ten
questions against a per-question timer, and gets their score with a full answer
review. Questions are managed entirely from the Django admin panel.

Built to match the interactive feel of the reference site, in the club's own
colours — deep navy, violet and cyan, taken from the logo.

---

## Stack

| Layer     | Choice                                                    |
| --------- | --------------------------------------------------------- |
| Backend   | Django 6.1, SQLite                                         |
| Frontend  | Django templates, hand-written CSS, vanilla JS             |
| Serving   | Gunicorn + WhiteNoise                                      |
| Packaging | Docker (one image, one command)                            |
| Build     | None — no Node, no bundler, no `npm install`               |

There is deliberately no frontend build step. Everything renders from Django, so
the whole site is one process and one container.

---

## Running it (Docker)

This is the path to use on any machine. Docker Desktop is the only requirement.

```bash
git clone <this-repo>
cd Quiz-Websites
docker compose up --build
```

Then open **http://localhost:8080**.

The first start builds the image, creates the database, loads the ten starter
questions and creates the admin account. Later starts skip all of that.

| | |
| --- | --- |
| Quiz | http://localhost:8080 |
| Admin panel | http://localhost:8080/admin/ |
| Username | `admin` |
| Password | `aiclub-admin-2026` |

**Change that password before the event.** See below.

### Everyday commands

```bash
docker compose up -d        # start in the background
docker compose logs -f      # watch what it is doing
docker compose down         # stop, keeping every question and result
docker compose up --build   # rebuild after pulling new code
```

`docker compose down` keeps your data. Only `docker compose down -v` erases it —
the `-v` removes the volume holding the database.

### Why port 8080

Port 8000 is taken by a lot of local projects, so the default here is 8080. To
use a different one, put it in a `.env` file next to `docker-compose.yml`:

```
QUIZ_PORT=9000
```

### Letting other devices join

Participants on the same Wi-Fi can reach the site by your machine's IP address.
Find it:

```bash
ipconfig getifaddr en0        # macOS
```

Then share `http://<that-ip>:8080`. `DJANGO_ALLOWED_HOSTS` defaults to `*`, so
this works with no extra configuration. That default is fine on a club LAN;
narrow it to your domain if the site is ever put on the public internet.

### Changing the admin password

```bash
docker compose exec quiz python manage.py changepassword admin
```

The admin account is created on **first start only**. Editing
`DJANGO_SUPERUSER_PASSWORD` afterwards changes nothing, because an existing
account is never modified — a restart must never silently reset a password.

To start from a different username or password on a machine that has never run
the site, set them in `.env` before the first `docker compose up`:

```
DJANGO_SUPERUSER_USERNAME=organiser
DJANGO_SUPERUSER_PASSWORD=something-you-choose
```

### Backing up the results

The database is a single SQLite file inside the `quiz-data` volume:

```bash
docker compose cp quiz:/app/data/db.sqlite3 ./backup-$(date +%F).sqlite3
```

Worth doing right after an event, before anyone runs `down -v`.

---

## Running it without Docker

Not everyone has Docker. One command does the whole thing:

```bash
./run.sh
```

On Windows, double-click **`run.bat`** or run it from Command Prompt.

The script finds a suitable Python, creates the virtual environment, installs
dependencies, prepares the database, loads the questions, creates the admin
account and starts the server at **http://127.0.0.1:8000**. Running it again is
safe — it skips whatever is already done and never touches your questions.

The only requirement is **Python 3.12 or newer**. If it is missing, the script
says so and tells you where to get it.

**Your admin password is printed on first run**, in a banner like this:

```
  ==========================================================
   Generated admin password: AD7IHkBFvzZGK0aP5iuL
   Save it now — this is the only time it is shown.
  ==========================================================
```

Copy it. The username is `admin`. To choose your own instead, set them before
the first run:

```bash
DJANGO_SUPERUSER_PASSWORD='your-password' ./run.sh
```

Lost it? `.venv/bin/python manage.py changepassword admin` sets a new one.

This uses `db.sqlite3` in the project folder — a separate database from the
Docker one, which lives in its own volume.

---

## Putting it online for free

Everything above runs on one machine. To give participants a link that works
from anywhere, without paying:

### The short version

**Render** (free web service) + **Neon** (free Postgres). Neither needs a credit
card, and the repository already contains the configuration.

1. Push this repo to GitHub.
2. Create a free Postgres at **https://neon.com** and copy the connection
   string it gives you.
3. In Render: **New → Blueprint**, pick the repo. Render reads `render.yaml`
   and asks for two values:
   - `DATABASE_URL` — the Neon connection string.
   - `DJANGO_SUPERUSER_PASSWORD` — your admin password. Leave it blank and one
     is generated and printed in the build log.
4. You get `https://aiclub-quiz.onrender.com`. Share that link.

### The catch you need to know about

**A free Render service sleeps after 15 minutes with no traffic, and takes
about a minute to wake up.** The first person to open the link after a quiet
period sits on a loading screen.

Before an event, open the link yourself a couple of minutes early. Once it is
awake it stays awake as long as people keep using it.

### Why Postgres and not SQLite

Render's free filesystem is wiped on every restart, redeploy and sleep. A
SQLite file there would silently lose every result. The app refuses to start on
Render without a `DATABASE_URL` rather than let that happen quietly.

Render's own free Postgres works too, but it **expires 30 days after creation**.
Neon's free plan is permanent, which is why it is the recommendation.

### Other options

| Option | Free? | Sleeps? | Data survives? | Notes |
| --- | --- | --- | --- | --- |
| **Render + Neon** | Yes, no card | After 15 min idle, ~1 min wake | Yes, in Neon | Recommended. Config is in this repo. |
| **PythonAnywhere** | Yes, no card | Never sleeps | Yes, real disk — SQLite is fine | 100 CPU-seconds/day and 512 MB. Fine for a quiz, but manual setup — no Docker, no blueprint. |
| **Oracle Cloud Always Free** | Yes, card for ID check | Never sleeps | Yes, real disk | A full VM. Most capable and most setup. Docker works, so `docker compose up` runs as-is. |
| **Your own laptop on club Wi-Fi** | Yes | Never | Yes | No account at all. Only reachable on that network. |

If the quiz is only ever run at in-person club events, the last row is honestly
the simplest thing that works — it is what the Docker and `run.sh` paths above
already give you.

---

## Setting up the questions

Everything happens at `/admin/`.

### The quiz itself

**Quizzes → AI Club Newcomer Quiz** controls:

| Field                  | What it does                                                    |
| ---------------------- | --------------------------------------------------------------- |
| `title`                | Shown on the start card and the quiz page                        |
| `intro`                | One line under the hero headline                                 |
| `seconds_per_question` | Countdown per question. **Set to `0` to remove the timer.**      |
| `pass_percentage`      | At or above this counts as a pass on the result screen           |
| `show_answer_review`   | Untick to show only the score, with no answer breakdown          |
| `is_active`            | The quiz newcomers see. Ticking one automatically unticks others |

### Adding and editing questions

**Questions → Add question**:

1. Pick the quiz, set `order` (lower numbers come first).
2. Write the question text.
3. Fill in the options at the bottom and tick **exactly one** as correct.
4. Optionally write an `explanation` — it appears in the answer review after
   someone finishes, under the correct answer.

The admin refuses to save a question with zero or two correct options, so a
broken question can't reach a participant.

The quiz page lists every question with a green tick when its options are valid
and a red warning when they are not, so you can see at a glance what still needs
work.

### Replacing the whole question set

Prepare a second quiz with new questions, then tick `is_active` on it. The old
one deactivates itself and its past results stay intact.

To reload the starter questions from scratch:

```bash
docker compose exec quiz python manage.py seed_quiz --reset
```

(Drop the `docker compose exec quiz` prefix when running without Docker.)

---

## Seeing the results

**Attempts** in the admin lists every participant: name, score, percentage, how
long they took, and when they finished. Open one to see their answer to each
question.

Attempts are read-only on purpose — they are a record of what happened, not
something to edit.

---

## How it fits together

```
run.sh / run.bat   One-command local run, no Docker needed
Dockerfile         The image: deps, static build, non-root user, gunicorn
docker-compose.yml One-command run, with the data volume
docker/
  entrypoint.sh    Migrate → seed if empty → ensure admin → start server
render.yaml        Free hosting blueprint (Render + Neon Postgres)
render-build.sh    What Render runs on each deploy
requirements.txt         Django, WhiteNoise, Gunicorn — that is all
requirements-deploy.txt  The above plus Postgres drivers, for hosting
config/            Django project (settings, root urls)
quiz/
  models.py        Quiz, Question, Choice, Attempt, Answer
  views.py         home → start → play → submit → result
  admin.py         The question-authoring panel
  forms.py         The name field and its validation
  tests.py         22 tests covering the flow, scoring and admin
  management/commands/
    seed_quiz.py     Loads the starter questions (--reset, --if-empty)
    ensure_admin.py  Creates the admin account if absent, never overwrites
templates/
  base.html        Shell: nav, preloader, footer
  quiz/home.html   Landing page
  quiz/play.html   The quiz runner
  quiz/result.html Score + answer review
static/
  css/base.css     Design tokens, nav, footer, buttons, animations
  css/home.css     Landing page
  css/quiz.css     Quiz runner and result screen
  js/site.js       Preloader, scroll reveal, counters, starfield
  js/quiz.js       The quiz runner
  js/result.js     Score ring, confetti, answer review
  img/             Club, CSE and university logos
Logo/              Original logo files, untouched
```

### The request flow

1. `GET /` — landing page with the name field.
2. `POST /start/` — creates an `Attempt`, stores its token in the session,
   redirects to the quiz.
3. `GET /q/<token>/` — the quiz page. **Questions and options are sent to the
   browser without the answer key.**
4. `POST /q/<token>/submit/` — the browser posts `{question_id: choice_id}`.
   The server scores it.
5. `GET /q/<token>/result/` — score, congratulations, answer review.

### Why scoring is on the server

The page never receives which option is correct, so opening developer tools
doesn't reveal the answers. A participant also can't post a choice belonging to
a different question, and re-posting a finished attempt won't change its score.
Results are tied to the browser session, so one participant can't read another's
result from the URL alone.

---

## Interaction details worth knowing

- **Keyboard**: `A`–`D` or `1`–`4` selects an option, `Enter` moves on.
- **Timer**: when it hits zero the quiz advances on its own; an unanswered
  question is recorded as skipped and shows as such in the review.
- **Tab switching**: the timer resyncs against the wall clock, so backgrounding
  the tab doesn't pause it.
- **Reduced motion**: every animation is disabled for anyone with
  `prefers-reduced-motion` set.
- **Mobile**: tested at 375px. Options go full width and the footer controls
  stack.

---

## Tests

```bash
docker compose exec quiz python manage.py test quiz
```

22 tests cover scoring, skipped questions, cross-question answer injection,
double submission, session privacy, the answer review toggle, and the admin's
"exactly one correct option" rule.

---

## Hosting it on your own server

If you have a VM or a university server rather than a free platform, run the
Docker image there and put a TLS-terminating reverse proxy in front of it.
Configure it through `.env`:

```
DJANGO_SECRET_KEY=<a long random string>
DJANGO_ALLOWED_HOSTS=quiz.yourdomain.edu
DJANGO_CSRF_TRUSTED_ORIGINS=https://quiz.yourdomain.edu
DJANGO_SECURE_HTTPS=1
```

Generate a key with:

```bash
docker compose exec quiz python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

`DJANGO_SECURE_HTTPS=1` turns on the HTTPS redirect, secure cookies and HSTS.
Only set it once TLS actually works — secure cookies break logins over plain
HTTP. The HSTS subdomain and preload flags are deliberately left off, since
both are painful to undo on a university domain.

WhiteNoise serves the static files, so no nginx static config is needed. On a
server with a real disk, SQLite in the volume is fine; set `DATABASE_URL` to
use Postgres instead.

---

## Before an event

1. Change the admin password.
2. Add your questions and tick `is_active` on the quiz you want live.
3. Take the quiz once yourself, end to end.
4. If you are on free hosting, open the link a few minutes early so the
   service is awake before the first participant arrives.
