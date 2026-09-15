# Silla — дашборд для Canvas

Личный дашборд курсов: прогресс по силлабусу, ближайшие дедлайны и файлы всех твоих
дисциплин на одной странице, с автоматической синхронизацией из Canvas LMS.

**Никакого ИИ и подписок не нужно.** Python-скрипт тянет данные из Canvas и сам
генерирует готовую веб-страницу (`dashboard.html`) — открываешь её в браузере, как любой
локальный файл. Каждый ставит себе свою собственную копию со своим Canvas-токеном; никто
не видит чужие оценки.

## Что нужно

- macOS или Linux
- Python 3.10+
- Личный access token Canvas (см. шаг 1)

## Установка

### 1. Получи Canvas API token

В Canvas: **Account → Settings → New Access Token**. Дай ему любое название (например
"Silla"), сохрани — Canvas покажет токен только один раз.

Также посмотри домен своего Canvas — адрес, на который ты заходишь в браузере (например
`myuni.instructure.com` или, как у Narxoz, свой собственный домен вида `canvas.myuni.kz`).

### 2. Склонируй репозиторий

```bash
git clone https://github.com/cyrexxxd/zachetka ~/PycharmProjects/silla
cd ~/PycharmProjects/silla
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

### 4. Синхронизируй и открой дашборд

```bash
./scripts/run_sync.sh
```

Это найдёт твои активные курсы, скачает файлы в `~/Documents/canvas files/<курс>/_synced/`
и сгенерирует `dashboard.html` в папке проекта. Открой этот файл в браузере (двойным
щелчком в Finder, или `open dashboard.html`) — готово, весь семестр на одной странице.

Первый запуск может занять несколько минут в зависимости от скорости твоего Canvas.

### 5. Автообновление

Проще всего — гонять `./scripts/run_sync.sh` руками перед тем, как заглянуть на дашборд
(идемпотентно, безопасно запускать сколько угодно раз). Для полной автоматизации на macOS
можно добавить `launchd`-задачу, которая запускает этот скрипт раз в день:

```bash
cat > ~/Library/LaunchAgents/com.silla.sync.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.silla.sync</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>-c</string>
    <string>cd ~/PycharmProjects/silla && ./scripts/run_sync.sh</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
</dict></plist>
PLIST
launchctl load ~/Library/LaunchAgents/com.silla.sync.plist
```

`dashboard.html` обновится каждое утро в 7:00 — просто обнови страницу в браузере.

## Бонус: живая ссылка через Claude (опционально)

Если у тебя есть [Claude Code](https://claude.com/claude-code), можно вместо локального
файла опубликовать дашборд как веб-страницу со своей ссылкой и живым обновлением без
пересборки файла — см. `.claude/skills/canvas-sync/SKILL.md`. Это не обязательно: локальный
`dashboard.html` из шага 4 даёт ровно тот же дашборд без каких-либо подписок.

Важно: у такой опубликованной страницы (Artifact с базой данных) технически **нет
публичного режима** — она видна только внутри организации Claude владельца. То есть даже
с Claude это не "один дашборд на весь универ", а личная ссылка для тебя одного.

## Как это устроено

- **`src/`** — Python-синк: авторизация в Canvas, расчёт процентов по силлабусу (веса
  групп заданий), скачивание файлов, локальная SQLite-база (`state/canvas.sqlite3`) как
  источник правды.
- **`templates/dashboard_template.html` → `dashboard.html`** — статическая страница
  дашборда с данными внутри; пересобирается при каждом синке, ничего кроме браузера не
  требует.
- **`artifact/dashboard.html`** и **`.claude/skills/canvas-sync/`** — опциональная версия
  через Claude Artifact (см. "Бонус" выше).

## Приватность

Токен Canvas никогда не покидает твой `.env`. `dashboard.html` содержит только уже
обработанные данные (названия курсов, даты, проценты, ссылки на файлы в самом Canvas) и
никогда не коммитится в git.

## Известные ограничения

- Canvas API не отдаёт содержимое .pptx/.docx для предпросмотра в браузере — дашборд
  просто ссылается на страницу файла в самом Canvas, открывается там же, где ты обычно
  смотришь материалы.
- Classic Quizzes и New Quizzes (Quizzes.Next) по-разному видны в API Canvas — синк
  использует Assignments API как единый источник дедлайнов, это покрывает оба варианта.
