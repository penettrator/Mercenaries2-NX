# Mercenaries 2: World in Flames для Nintendo Switch — 0.2.0

[English](README.en.md)

Автор порта: [penettrator](https://github.com/penettrator). Поддержка: [Boosty](https://boosty.to/itgenius). Донаты помогают выпускать новые порты.

Нативный порт Xbox 360 версии Mercenaries 2: World in Flames на Nintendo Switch: статическая рекомпиляция PowerPC в ARM64 через ReXGlue и собственный Vulkan-рендерер на NVK/Mesa. Нужна собственная официальная копия игры; игровые данные и кеши игры в публичный пакет не входят.

## Что нового

- Оптимизированы CPU-помощники поиска и работа рендера; используется PGO.
- Уменьшены повторные выделения памяти при загрузке текстур, добавлены ограниченные кеши материалов и изображений.
- Исправлено замедление движения, камеры и анимаций в проверенной локации внутри здания: убрано дополнительное ограничение порта в 30 FPS.
- Запрошенная текстура дожидается готовности загрузки вместо пустой подстановки.
- Накопленные варианты шейдеров и pipeline прогреваются до начала игры. Тестовый захват кадров и диагностика игрового времени выключены.

## Что нужно

- Nintendo Switch с Atmosphère.
- Не менее **8 ГБ** свободного места на SD; FAT32 подходит.
- DBI или другой менеджер установки NSP.
- Своя Xbox 360 копия игры. Поддерживается `default.xex` с SHA-256 `48e805e4a2c1c4f7b409245dc9f2d02e2e8a94eaa0e9f1744d150ddce00bf72b`.

## Установка

### 1. Файлы порта

Готовые файлы распространяются через [Releases](https://github.com/penettrator/Mercenaries2-NX/releases):

| Файл | Назначение |
|---|---|
| `Mercenaries2-NX.zip` | Готовый порт, настройки и VERSION: `switch/Mercenaries2/` |
| `Mercenaries2-forwarder.nsp` | Иконка HOME; разрешает использование четырёх ядер |

Распакуйте ZIP в корень SD. Должна получиться `SD:/switch/Mercenaries2/`, без лишней папки `switch/switch`. Самостоятельная сборка для установки не нужна.

### 2. Своя игра

Если игра уже распакована, назовите папку с `default.xex` **`game_root`**. Иначе распакуйте свою Xbox 360 ISO с помощью [extract-xiso](https://github.com/XboxDev/extract-xiso/releases):

```text
extract-xiso.exe -x "Mercenaries 2.iso" -d game_root
```

Скопируйте всю `game_root` в `SD:/switch/Mercenaries2/`. Внутри должны лежать `default.xex`, `vz.wad`, `shell.wad`, папки `audios`, `movies` и остальные файлы издания. Папка `$SystemUpdate` игре не требуется.

```text
SD:/switch/Mercenaries2/
  mercenaries2.nro
  mercenaries2.toml
  VERSION
  game_root/
    default.xex
    vz.wad
    ...остальные файлы игры
```

### 3. Запуск

Установите **Mercenaries2-forwarder.nsp** через DBI и запустите игру с HOME без удержания R. NSP запускает NRO с SD: папку игры на карте оставьте.

**Форвардер уже разрешает четыре ядра. Заменять `atmosphere/hbl.nsp` и править системные файлы не нужно.**

Альтернатива: удерживайте R при запуске обычной установленной игры, дождитесь hbmenu и выберите Mercenaries 2. Четвёртое ядро зависит от загрузчика. **Через Альбом не запускайте:** памяти недостаточно.

## Обновление с предыдущей версии

1. Полностью закройте игру: HOME → X → «Закрыть».
2. Скопируйте на компьютер `SD:/switch/Mercenaries2/mercenaries2/` (сохранения и кеш) и свой старый TOML.
3. Замените в `SD:/switch/Mercenaries2/` только `mercenaries2.nro`, `mercenaries2.toml`, `VERSION` из нового ZIP.
4. Установите новый форвардер поверх старого и выберите «Продолжить».

`game_root` повторно копировать не нужно. Не удаляйте существующую папку игры и вложенную `mercenaries2`: сохранения лежат там. Если меняли язык или другие настройки, перенесите нужные значения в новый TOML; не возвращайте старый файл целиком.

## Настройки

Файл: **`SD:/switch/Mercenaries2/mercenaries2.toml`**. После правок полностью перезапустите игру.

| Параметр | Значение | Назначение |
|---|---|---|
| `user_language` | `12` | `12` — русский, `1` — английский; текст и озвучка зависят от издания |
| `present_effect` | `"fsr"` | FSR 1, внутреннее разрешение 960×544 |
| `achievement_notifications` | `false` | Уведомления достижений выключены |
| `mercs2_min_frame_vblanks` | `1` | Сохранение кадрового темпа игры, включая помещения |
| `mercs2_native_texture_demand_wait` | `true` | Дождаться востребованной текстуры вместо пустого материала |
| `mercs2_native_prewarm_before_game` | `true` | Прогреть известный кеш pipeline до начала игры |

Проверки проводились в handheld на CPU1785 / GPU768 / RAM2200 МГц. Порт сам не задаёт частоты; этот профиль измерений не является универсальным требованием для всех ревизий Switch.

## Известные ограничения

- При въезде в новую локацию могут сохраняться просадки и краткое мерцание материалов зданий. Полное устранение этого дефекта не подтверждено.
- Прогрев покрывает накопленные варианты; неизвестные шейдеры и состояния pipeline ещё могут создаваться при первом появлении. Первый запуск без собственного кеша может быть менее плавным.
- В конфиге сохранены 3 каскада теней и прежние настройки эффектов; дальние тени ограничены относительно оригинала.

## Исходники, благодарности и лицензии

Инструкции разработчикам: [сборка на русском](docs/building.md), [English build guide](docs/building.en.md). Изменения версии: [CHANGELOG.md](CHANGELOG.md). Сгенерированный код, образы, сохранения, сырые PGO-профили и кеши игры в Git не включаются.

- [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk) / [Xenia](https://xenia.jp).
- [masseffect-nx](https://github.com/nebadasSwifty/masseffect-nx).
- [project8-sw](https://github.com/R-drg/project8-sw), [the-simpsons-game-nx](https://github.com/R-drg/the-simpsons-game-nx), [NFSMW-NX](https://github.com/StevensND/NFSMW-NX).
- [Prototype2-NX](https://github.com/penettrator/Prototype2-NX) — опыт общих оптимизаций.
- [mesa-switch](https://github.com/danfromtico/mesa-switch) / [Mesa](https://mesa3d.org).
- [AMD FidelityFX FSR 1](https://github.com/GPUOpen-Effects/FidelityFX-FSR).
- [Forwarder-Mod](https://github.com/Skywalker25/Forwarder-Mod) / nx-hbloader, [hacBrewPack](https://github.com/rlaphoenix/hacBrewPack).

Код порта — GPL-3.0: [LICENSE](LICENSE). Сторонние компоненты: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [лицензия форвардера](LICENSE-Forwarder-Mod.txt). Проект не связан с Electronic Arts, Pandemic Studios, Microsoft или Nintendo.
