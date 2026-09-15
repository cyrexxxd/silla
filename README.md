# Зачётка — дашборд для Canvas

Личный дашборд курсов: прогресс по силлабусу, ближайшие дедлайны и файлы всех твоих
дисциплин на одной странице, с автоматической синхронизацией из Canvas LMS.

Каждый ставит себе **свою собственную** копию — со своим Canvas-токеном и своим приватным
дашбордом. Никто не видит чужие оценки: у каждого пользователя отдельный Artifact и
отдельная база данных.

Работает через [Claude Code](https://claude.com/claude-code): Python-скрипт тянет данные
из Canvas на твой компьютер, а Claude публикует и обновляет твою личную веб-страницу
(Artifact) с этими данными.

## Что нужно

- macOS (скрипты рассчитаны на launchd/zsh; на Linux всё кроме автоматизации через launchd
  тоже заработает)
- Python 3.10+
- [Claude Code](https://claude.com/claude-code)
- Личный access token Canvas (см. шаг 1)

## Установка

### 1. Получи Canvas API token

В Canvas: **Account → Settings → New Access Token**. Дай ему любое название (например
"Зачётка"), сохрани — Canvas покажет токен только один раз.

Также посмотри домен своего Canvas — адрес, на который ты заходишь в браузере (например
`myuni.instructure.com` или, как у Narxoz, свой собственный домен вида `canvas.myuni.kz`).

### 2. Склонируй репозиторий

```bash
git clone <URL этого репозитория> ~/PycharmProjects/canvas-dashboard
cd ~/PycharmProjects/canvas-dashboard
```

### 3. Настрой окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Открой `.env` и заполни:
```
CANVAS_API_TOKEN=<твой токен из шага 1>
CANVAS_BASE_URL=https://<твой домен Canvas>
```

`.env` никогда не попадает в git (он в `.gitignore`) — токен остаётся только на твоём
компьютере.

### 4. Проверь подключение и сделай первый синк

```bash
./scripts/run_sync.sh
```

Это найдёт твои активные курсы, скачает файлы в `~/Documents/canvas files/<курс>/_synced/`
и запишет `artifact_payload/latest.json`. Первый запуск может занять несколько минут в
зависимости от скорости твоего Canvas.

### 5. Опубликуй свой дашборд

Открой Claude Code в папке проекта и попроси:

> Опубликуй artifact/dashboard.html как Artifact с capability `db`, и запушь в него данные
> из artifact_payload/latest.json (courses/{id}, sync/calendar, files/{course_id},
> sync/meta — см. .claude/skills/canvas-sync/SKILL.md).

Claude опубликует страницу и даст тебе ссылку вида `https://claude.ai/code/artifact/...`.
Сохрани эту ссылку в `.env`:
```
DASHBOARD_URL=https://claude.ai/code/artifact/твой-id
```

Открой ссылку — там уже должны быть твои реальные курсы, оценки и файлы.

### 6. Настрой автообновление (опционально)

Попроси Claude Code создать ежедневную scheduled-задачу (`mcp__scheduled-tasks`), которая
каждое утро запускает `./scripts/run_sync.sh` и пушит результат в твой `DASHBOARD_URL` по
инструкции `.claude/skills/canvas-sync/SKILL.md`. Ручной запуск в любой момент — та же
команда `./scripts/run_sync.sh`, затем попросить Claude запушить результат.

## Как это устроено

- **`src/`** — Python-синк: авторизация в Canvas, расчёт процентов по силлабусу (веса
  групп заданий), скачивание файлов, локальная SQLite-база (`state/canvas.sqlite3`) как
  источник правды, экспорт в `artifact_payload/latest.json`.
- **`artifact/dashboard.html`** — сама веб-страница дашборда (карточки курсов, дедлайны,
  файлы, отдельная страница на каждый предмет по клику).
- **`.claude/skills/canvas-sync/`** — инструкция для Claude, как взять `latest.json` и
  запушить его в твой Artifact.

## О приватности и общем доступе

Artifact с базой данных (`db` capability) технически **не может быть публичным** — он
виден только внутри организации Claude владельца. Поэтому это не "один дашборд на весь
универ": у каждого своя приватная копия со своими данными, которые никто другой не видит.
Токен Canvas никогда не покидает твой `.env` и никогда не пишется в Artifact — туда идут
только уже обработанные данные (названия курсов, даты, проценты, ссылки на файлы в самом
Canvas).

## Известные ограничения

- Canvas API не отдаёт содержимое .pptx/.docx для предпросмотра в браузере — дашборд
  просто ссылается на страницу файла в самом Canvas (`canvas_url`), открывается там же,
  где ты обычно смотришь материалы.
- Classic Quizzes и New Quizzes (Quizzes.Next) по-разному видны в API Canvas — синк
  использует Assignments API как единый источник дедлайнов, это покрывает оба варианта.
- Автообновление через `mcp__scheduled-tasks` работает, пока открыт Claude Code (или при
  следующем запуске, если было закрыто) — это не постоянно работающий демон.
