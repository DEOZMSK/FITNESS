# Отчёт по текущему состоянию проекта FITNESS

Дата фиксации: 2026-04-25

## 1. Текущий статус

### Реально готово
- Точка входа бота запускает polling, подключает роутеры и инициализирует SQLite.
- Есть рабочий `/start` и главное inline-меню с переходом в «Обо мне» и «Фитнес-диагностика».
- Реализован сценарий «Обо мне»: профиль, услуги, отзывы, контакты.
- Реализован FSM-сценарий быстрой диагностики (12 шагов), сохранение сессии в БД, отправка summary админу.
- Реализован FSM-сценарий полной анкеты (18 шагов), сохранение в БД, отправка summary админу.
- Реализован сценарий доната: ввод суммы, выставление инвойса Telegram, обработка successful payment, запись платежа в БД.
- Реализован слой SQLite с созданием таблиц и seed-данными для продуктов/отзывов.
- Реализованы отдельные калькуляторы и формулы (BMI, WHR, BMR/TDC, БЖУ, калипер, гибкость, beta-модули).

### Частично готово
- Контент профиля тренера заполнен заглушками (`[Добавьте ...]`).
- Пакет `app/bot/keyboards` существует, но отдельные переиспользуемые клавиатуры не вынесены (клавиатуры формируются в хендлерах).
- Есть модульные формулы, но они не встроены в пользовательский сценарий выдачи результатов в чате.
- В README указан `.env.example`, но в репозитории этого файла нет.

### Не начато / не реализовано
- Автотесты (unit/integration/e2e) в репозитории отсутствуют.
- Нет отдельной админки/панели для просмотра лидов и платежей.
- Нет явной системы повторной отправки лидов с `lead_sent=0`.

## 2. Структура проекта (реальная)

```text
app/
  bot/
    handlers/
      __init__.py
      about.py
      diagnostics.py
      start.py
    keyboards/
      __init__.py
    states/
      __init__.py
      diagnostics.py
      donate.py
      questionnaire.py
  calculators/
    __init__.py
    body_metrics.py
    calories.py
    caliper.py
    flexibility.py
    hypertrophy_beta.py
    letunov_beta.py
  data/
    __init__.py
    contraindications.py
    products.py
    reviews.py
    trainer_profile.py
  db/
    __init__.py
    configs.py
    database.py
  services/
    __init__.py
    admin_notify.py
    payments.py
  config.py
  main.py
README.md
requirements.txt
amvera.yml
docs/
  PROJECT_AUDIT_2026-04-25.md
```

## 3. Ключевые файлы

- `app/main.py` — старт приложения: загрузка env, инициализация БД, запуск polling.
- `app/bot/handlers/start.py` — `/start` и возврат в главное меню.
- `app/bot/handlers/about.py` — экраны «Обо мне» + FSM доната и обработка оплаты.
- `app/bot/handlers/diagnostics.py` — два сценария: quick (12 шагов) и full (18 шагов).
- `app/bot/states/diagnostics.py` — состояния quick-диагностики.
- `app/bot/states/questionnaire.py` — состояния полной анкеты.
- `app/bot/states/donate.py` — состояние доната.
- `app/data/contraindications.py` — стоп-факторы и защитное сообщение.
- `app/services/admin_notify.py` — отправка summary админу, mark-as-unsent при ошибке.
- `app/services/payments.py` — валидация суммы и отправка Telegram invoice.
- `app/db/database.py` — схема SQLite + CRUD для пользователей, анкет, диагностик, платежей.
- `app/calculators/*.py` — формулы и интерпретации по метрикам.

Отдельно:
- Где меню: `app/bot/handlers/start.py`, `app/bot/handlers/about.py`, `app/bot/handlers/diagnostics.py`.
- Где диагностика: `app/bot/handlers/diagnostics.py`, `app/bot/states/diagnostics.py`, `app/bot/states/questionnaire.py`.
- Где формулы: `app/calculators/body_metrics.py`, `calories.py`, `caliper.py`, `flexibility.py`, `hypertrophy_beta.py`, `letunov_beta.py`.
- Где база: `app/db/database.py`, `app/db/configs.py`.
- Где FSM: `app/bot/states/*.py` + переходы в `app/bot/handlers/about.py` и `app/bot/handlers/diagnostics.py`.

## 4. Реальные функции

(Список в репозитории, без выдуманных API)
- `bmi(height_cm, weight_kg)` → считает BMI.
- `bmi_interpretation(bmi_value)` → возвращает категорию BMI.
- `ideal_weight(height_cm, sex)` → считает «идеальный вес» по Broca.
- `somatotype(height_cm, weight_kg, wrist_cm)` → простая классификация соматотипа.
- `whr(waist_cm, hip_cm)` → коэффициент талия/бёдра.
- `whr_interpretation(whr_value, sex)` → риск по WHR.
- `body_fat_percent(sum_of_folds_mm, age, sex)` → оценка % жира по Jackson-Pollock.
- `lean_body_mass(weight_kg, body_fat_pct)` → безжировая масса.
- `bmr(weight_kg, height_cm, age, sex)` → базовый метаболизм.
- `tdc(bmr_value, activity_level)` → суточный расход калорий.
- `bju_distribution(weight_kg, calories_target, goal)` → распределение БЖУ.
- `sit_and_reach_score(distance_cm)` → результат теста наклона.
- `shoulder_flex_score(overlap_cm)` → результат плечевого теста.
- `total_flexibility_score(sit_and_reach_cm, shoulder_overlap_cm)` → суммарная оценка гибкости.
- `weekly_score(components)` → beta-скоринг гипертрофии.
- `classify_letunov(data)` → beta-интерпретация профиля Летунова.
- `create_invoice(message, amount_rub)` → выставляет Telegram invoice и пишет payment event.
- `send_diagnostics_summary(...)` → шлёт summary админу.

## 5. Реализованные формулы

- BMI: `weight / (height_m^2)` — `app/calculators/body_metrics.py`.
- Broca ideal weight: `(height_cm - 100) * coeff` — `app/calculators/body_metrics.py`.
- WHR: `waist / hip` — `app/calculators/body_metrics.py`.
- BMR Mifflin-St Jeor — `app/calculators/calories.py`.
- TDC: `BMR * activity_coeff` — `app/calculators/calories.py`.
- БЖУ от цели (cut/bulk/maintain) — `app/calculators/calories.py`.
- Jackson-Pollock (3-site) для % жира — `app/calculators/caliper.py`.
- LBM: `weight * (1 - fat_pct/100)` — `app/calculators/caliper.py`.
- Балльная оценка гибкости (2 теста) — `app/calculators/flexibility.py`.
- Hypertrophy beta normalization — `app/calculators/hypertrophy_beta.py`.
- Letunov beta: `recovery_delta`, pressure reactivity index — `app/calculators/letunov_beta.py`.

## 6. Не реализовано

- Нет автотестов.
- Нет обработчиков команд для непосредственного использования калькуляторов из чата.
- Нет повторной очереди доставки для lead-уведомлений при `lead_sent=0`.
- Нет реального контента в `trainer_profile.py` (заглушки).
- Нет отдельного UI/веб-интерфейса (только Telegram-бот).

## 7. FSM-сценарии

Работают:
- `/start` → главное меню → `diag:start`.
- `diag:quick` → 12 шагов (`name` ... `health`) → запись в `diagnosis_sessions` + `calculations_history` → уведомление админу.
- `diag:full` → 18 шагов → запись в `questionnaire_answers` → уведомление админу.
- `donate:start` → ввод суммы → invoice → successful_payment → запись в `payments`.

Стоп-сценарий:
- Если в тексте health/анкеты найдены стоп-факторы, бот завершает диалог безопасным сообщением.

## 8. База данных

Таблицы:
- `users`: telegram_id, username, first_name, last_name, created_at, updated_at.
- `diagnosis_sessions`: user_id, session_payload, lead_sent, created_at.
- `questionnaire_answers`: user_id, diagnosis_session_id, answers_payload, lead_sent, created_at.
- `calculations_history`: user_id, diagnosis_session_id, calculation_payload, created_at.
- `payments`: user_id, provider_payment_id, amount, currency, status, lead_sent, payload, created_at.
- `reviews`: author_name, rating, text, is_published, created_at.
- `products`: code, name, description, price, currency, is_active, created_at.

Где используется:
- upsert пользователя: при диагностике и оплате.
- сохранение быстрой диагностики: `save_diagnosis_session_and_calculation`.
- сохранение полной анкеты: `save_full_questionnaire`.
- сохранение платежей: `record_payment`.

## 9. Как проверить руками

1) Запустить бота (`python -m app.main`) с валидными env.
2) В Telegram отправить `/start`.
3) Нажать «🧪 Фитнес-диагностика» → «⚡ Быстрая диагностика».
4) Ввести 12 ответов; на шаге 10 можно «Пропустить».
5) Получить финал: либо «Быстрая диагностика сохранена», либо safety-message по стоп-факторам.
6) Повторить через «📋 Полная анкета» (18 шагов).
7) Проверить донат: пройти `donate:start`, ввести сумму >= 300, завершить тестовый платёж.
8) Проверить SQLite `fitness.db`: появились записи в users/diagnosis_sessions/questionnaire_answers/payments.

## 10. Тестовые данные

Quick-поток (без стоп-факторов):
- Имя: Артём
- Возраст: 37
- Пол: Мужской
- Рост: 189
- Вес: 75
- Талия: 55
- Бёдра: 88
- Грудь: 90
- Запястье: 13
- Рост сидя: пропуск
- Цель: Здоровье
- Здоровье: «без ограничений»

Quick-поток (со стоп-фактором):
- Здоровье: «после инсульта, острая боль в колене»

Full-поток:
- Сон: 7.5
- Стресс: средний
- Тренировок в неделю: 3
- Цель: снижение веса

## 11. Проблемы / сомнения

- В `amvera.yml` указан `scriptName: app.py`, а точка входа фактически `python -m app.main`.
- В summary админу виден сырой HTML (`<b>...`) из screenshot-поведения — возможно, parse_mode не везде срабатывает как ожидается.
- В `about.py` данные услуг берутся из `app/data/products.py`, но БД сидируется отдельным набором `app/db/configs.py` (два источника правды).
- Нет валидации реалистичности диапазонов (например, талия 55/бёдра 38 допускаются, если >0).

## 12. Оценка готовности

- **~72%** (честная оценка по коду):
  - Core-бот + FSM + БД + платежная интеграция есть.
  - Не хватает тестов, финального контента, связки калькуляторов с пользовательскими сценариями и операционного контура для retry lead-уведомлений.
