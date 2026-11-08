# Что выполнить дома

Готово локально: M1; T-201/202/203; T-301/302/303. Данные и логи находятся в
`docs/evidence/`. Полный MVP и M2/M3 пока не объявлены завершёнными.

## 1. Разблокировать T-205 — реальный CI

Перенесите проект в выбранный вами GitHub-репозиторий, сохранив `.github/`.
Публикация отсюда не выполнялась. Сейчас есть пустой Git checkout без HEAD и
remote; целевой GitHub-репозиторий не настроен.
В Actions запустите workflow **Verify RedMud** через Run workflow или push.

Нужны все шесть сочетаний Ubuntu 24.04 x86_64 / macOS 15 arm64 × CPython
3.11/3.12/3.13, а также security job. Сохраните URL запуска и артефакты:
`verification-*/ci-*.log`, результаты независимых wheel/sdist установок,
`security-evidence` со сканами и логом. Конфигурация workflow не заменяет запуск.
При ошибке сначала исправить её, затем записать повторный результат в EVIDENCE.
Только после проверки всей матрицы можно закрывать T-205.

## 2. Локальная проверка

Выполнено 2026-11-08: macOS 26.6 arm64, Rust 1.99.1, CPython
3.11.15/3.12.13/3.13.3. Для каждой версии прошли `scripts/check.sh` и
независимые чистые установки wheel/sdist: 10 Rust PASS / 1 diagnostic ignored;
80 Python PASS / 1 Linux-only skipped на каждый Python suite; native/dataclass
примеры PASS. Логи, точные команды и SHA256: [E-22](../EVIDENCE.md#e-22--t-205-local-macos-verification-2026-11-08)
и [артефакты](evidence/t205-macos/artifacts.json). Это локальное выполнение,
не hosted CI; T-205 остаётся BLOCKED. M4 не начат.

Из корня проекта, с установленным Rust 1.99.1 и CPython 3.11–3.13:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
rustup toolchain install 1.99.1 --profile minimal --component rustfmt,clippy
rustup override set 1.99.1
bash scripts/check.sh
python scripts/package_check.py
```

Команды не требуют коннекторов или внешних сервисов. Сборке нужны доступные
реестры Cargo/Python и инструменты компиляции. `package_check.py` проверяет
wheel и sdist в отдельных venv; одна локальная ОС не заменяет CI-матрицу.
Сканеры в workflow ставятся изолированно по уже проверенным версиям.

## 3. Повторить измерения и принять решение T-304

Сначала измерьте текущую версию как reference на своей машине, без параллельных
сборок и других нагрузок. Каждый запуск пишет в новую директорию:

```sh
python -m benchmarks.run --profile smoke --output target/home-smoke
python -m benchmarks.run --profile baseline --repeat 5 --rss-repeat 3 --record-scale 10 --output target/home-baseline
python -m benchmarks.run --profile stream --rss-repeat 3 --output target/home-stream
python -m benchmarks.components --repeat 5 --records 1000 --output target/home-components
```

На Linux можно добавить `--pin-cpu`; на macOS не добавлять. Измеритель RSS macOS
пока не проверен: не выдавайте его результат за подтверждённую корректную метрику.
Исходный TCore необязателен: `--tcore-source /путь/к/tcore-project/src` добавляет
проверенный адаптер. Не устанавливайте Polars/msgspec ради этого запуска.
Не используйте Python `-O`: проверки эквивалентности обязательны.

[Методика и все результаты](benchmarks.md) объясняют единицы, накладные расходы,
ограничения p95 и исправление RSS. [Предложение T-304](performance-proposal.md)
содержит измеренные ориентиры и правила сравнения; они ещё не утверждены.
Следующее решение — утвердить/изменить правила и разрешить отдельный эксперимент
T-401 либо явно отложить M4. Затем продолжать по TASKS; не начинать сразу оба
преобразования FFI и не менять контракты ради ускорения.
