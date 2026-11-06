# Сборка Mercenaries2-NX 0.2.0

[English](building.en.md)

Нужны Windows, PowerShell, Python3, Git, Docker Desktop и своя Xbox 360 копия игры. Готовые файлы устанавливаются без самостоятельной сборки — см. [README](../README.md).

## Зависимости

Работайте из корня репозитория. Базовые коммиты и монолитные патчи:

```sh
git clone https://github.com/nebadasSwifty/masseffect-nx.git reference/masseffect-nx
git -C reference/masseffect-nx checkout a85b0b419ec3e332165ae1617c980bd399856a44
git -C reference/masseffect-nx apply ../../patches/rexglue-sdk-masseffect-nx.patch

git clone https://github.com/rexglue/rexglue-sdk.git reference/rexglue-upstream
git -C reference/rexglue-upstream checkout f5337cdc947ff6d4c4196737e2c807a48f2a1fc2
git -C reference/rexglue-upstream submodule update --init --recursive

git clone https://github.com/danfromtico/mesa-switch.git reference/mesa-switch-src
git -C reference/mesa-switch-src checkout d4a00ea0ab3f59afb967cc5d779e4263d237bd77
git -C reference/mesa-switch-src apply ../../patches/mesa-switch.patch
python tools/materialize_dependency_links.py
```

Монолитные `patches/` содержат актуальные изменения SDK/Mesa. `tools/patches` и применялки являются сборочными/историческими шагами с проверками повторного применения; не накладывайте вручную все шаговые патчи поверх монолитного экспорта.

## Данные и кодогенерация

Поместите свою распакованную игру в `assets/game_root/`. SHA-256 `default.xex`: `48e805e4a2c1c4f7b409245dc9f2d02e2e8a94eaa0e9f1744d150ddce00bf72b`. Нужны остальные WAD, audio и movie файлы издания.

Распакуйте официальный Windows SDK ReXGlue0.10.0 из [releases](https://github.com/rexglue/rexglue-sdk/releases) под `tools/bin/`, чтобы скрипт нашёл `rexglue.exe`.

```powershell
tools/codegen.ps1
```

Скрипт запускает подготовку generated-кода. `app/generated/` остаётся локальным, его нельзя добавлять в Git.

## NVK/Mesa для Switch

```powershell
docker build -t mercenaries2-mesa-build:dev -f tools/Dockerfile.mesa tools
tools/continue_switch_build.ps1
```

Результат: `out/mesa-sdk/opt/devkitpro/portlibs/switch/lib/libvulkan.a`. Это длительный шаг. Логи сохраняйте в локальной папке logs/out.

## Сборка NRO

```powershell
tools/build_switch.ps1 -Jobs 6 -GlobalOptimizations -SlotSourceEpoch -ImageReuse -MaterialRetention -RingWriteback -NativeTableLookup -Pgo OFF -BuildDirectory out/nx-release
```

Контейнер NRO зафиксирован в `tools/build_switch.ps1`: `devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282` (GCC15.2.0). Результат: `out/nx-release/mercenaries2.nro`. Иконка берётся из `extras/icon.jpg`, версия NACP0.2.0.

Скопируйте NRO и `config/mercenaries2.toml` в `SD:/switch/Mercenaries2/`, свои данные — в `game_root/`. Обычный скрипт явно выключает невыбранные эксперименты, GPU draw profiling, CSV и emulator guards. Отвергнутые AlphaCompare/ReadyTextures не включайте.

## PGO и релизный бинарник

Подготовленный бинарник использует PGO USE: 161 исходный профиль, включая renderer. Две изменённые native TU и новая TU помощников не потребляют старые данные. Старые 163 gcda/GEN graphs сохранены неизменными; итоговая строгая сборка не дала missing-profile/coverage-mismatch. CSV и диагностика игрового времени выключены.

Сырые профили не распространяются: обычная сборка выше использует PGO OFF и не обещает идентичный FPS. Для собственного обучения используйте `-Pgo GEN`, уникальный `-PgoSession`, зафиксированный компилятор и проверки `tools/pgo_session.py` (prepare/finalize/import/audit). Не смешивайте профили разных исходников/режимов и не подавляйте mismatch. `-Pgo USE` допускается только с собственной завершённой совместимой сессией. Подробности механизма и ограничений: [performance-2026-11-06.md](performance-2026-11-06.md).

## Форвардер HOME

Из Git Bash, с собственным файлом ключей консоли:

```sh
SWITCH_PROD_KEYS=/path/to/prod.keys tools/build_forwarder.sh out/nx-release/mercenaries2.nro out/forwarder
```

Скрипт использует закреплённые Forwarder-Mod/hacBrewPack и контейнер. Проверяет 39-bit address space и ядра0–3 в ACI0/ACID. Title ID `014d455243530000`, путь `sdmc:/switch/Mercenaries2/mercenaries2.nro`. Ключи не входят в NSP/пакеты/Git и не выводятся в сборочный лог.

## Кеш и проверка

Нативный кеш создаётся на консоли в `mercenaries2/cache/shaders/driver/`. С включёнными `mercs2_native_pipeline_prewarm=true` и `mercs2_native_prewarm_before_game=true` известные варианты прогреваются до Main; неизвестные варианты остаются first-use. Кеш другого порта не подходит. Кеш игры не публикуется в исходниках/общедоступном пакете.

`tools/audit_native_shader_cache.py` проверяет формат, XXH3 checksum и ссылки ключей. Ему нужна host-библиотека xxHash (`--hash-library` при необходимости). Host-проверки readiness: `python tools/test_native_bugfix16.py` в Linux с g++23/ASan/UBSan; native lookup: `python tools/test_native_table_lookup.py`. Они используют locally generated код своей игры; их PASS не заменяет Switch-проверку.
