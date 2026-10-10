# Сборка из исходников

Сборка проверялась на Windows 10 с Docker Desktop и Git Bash. Нужны: Docker, Python 3, Git, PowerShell
и **ваш** образ игры (файлы игры в репозитории нет и не будет).

## 1. Внешние репозитории (на зафиксированных коммитах)

```sh
git clone https://github.com/nebadasSwifty/masseffect-nx.git reference/masseffect-nx
git -C reference/masseffect-nx checkout a85b0b419ec3e332165ae1617c980bd399856a44
git -C reference/masseffect-nx apply ../../patches/rexglue-sdk-masseffect-nx.patch

git clone --recursive https://github.com/rexglue/rexglue-sdk.git reference/rexglue-upstream
git -C reference/rexglue-upstream checkout f5337cdc947ff6d4c4196737e2c807a48f2a1fc2
git -C reference/rexglue-upstream submodule update --init --recursive

git clone https://github.com/danfromtico/mesa-switch.git reference/mesa-switch-src
git -C reference/mesa-switch-src checkout d4a00ea0ab3f59afb967cc5d779e4263d237bd77
git -C reference/mesa-switch-src apply ../../patches/mesa-switch.patch
```

`patches/` содержит **все** изменения порта в SDK (Horizon-форк ReXGlue из masseffect-nx) и в Mesa одним файлом
на репозиторий. Отдельные патчи в `tools/patches/` - история тех же изменений по шагам, при сборке по этой
инструкции их применять не нужно.

```sh
python tools/materialize_dependency_links.py
```

## 2. Данные игры и кодогенерация

1. Распакуйте образ диска в `assets/game_root/` (см. README, раздел "Образ игры").
   `default.xex` должен иметь SHA-256 `48e805e4a2c1c4f7b409245dc9f2d02e2e8a94eaa0e9f1744d150ddce00bf72b`.
2. Скачайте ReXGlue SDK 0.10.0 для Windows
   ([rexglue-sdk releases](https://github.com/rexglue/rexglue-sdk/releases)) и распакуйте в `tools/bin/`.
3. Сгенерируйте C++ из `default.xex` (результат попадает в `app/generated/`, в git его не кладут):
   ```powershell
   tools/codegen.ps1
   python tools/codegen_no_volatile.py
   ```

## 3. Mesa (NVK/NAK для Horizon), один раз, около часа

```powershell
docker build -t mercenaries2-mesa-build:dev -f tools/Dockerfile.mesa tools
tools/continue_switch_build.ps1
```

Результат: `out/mesa-sdk/opt/devkitpro/portlibs/switch` (libvulkan.a).

## 4. Игра

```sh
MSYS_NO_PATHCONV=1 docker run --rm --mount "type=bind,source=$(pwd -W),target=/work" -w /work \
  devkitpro/devkita64:latest bash -lc "cmake -S app -B out/nx -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=/work/tools/switch/cmake/switch-devkitA64.cmake \
  -DREXSDK_DIR=/work/reference/masseffect-nx/sdk \
  -DREXGLUE_SWITCH_NVK_SDK=/work/out/mesa-sdk/opt/devkitpro/portlibs/switch \
  -DMERCENARIES2_EMULATOR_GUARDS=OFF && cmake --build out/nx --target mercenaries2 -j 6"
```

Результат: `out/nx/mercenaries2.nro` (полная сборка около 5 минут). Настройки по умолчанию для релиза:
`release/mercenaries2.toml`.

## 5. Форвардер NSP (иконка на главном экране)

```sh
SWITCH_PROD_KEYS=/path/to/prod.keys tools/build_forwarder.sh out/nx/mercenaries2.nro out/forwarder
```

Нужны **ваши собственные** ключи консоли (Lockpick_RCM). Из них берутся только `header_key` и
`key_area_key_application_00`, в NSP ключи не попадают. NSP запускает `sdmc:/switch/Mercenaries2/mercenaries2.nro`
в режиме приложения с 39-битным адресным пространством (title ID `014d455243530000`). Иконка и название берутся
из NRO.

## Что в репозитории

| Путь | Содержимое |
|---|---|
| `app/` | Код порта: точка входа, хуки, нативный рендерер (`app/src/native`), манифест кодогенерации |
| `tools/` | Сборка, кодогенерация, анализ логов и профилей с консоли, отладочные пробы |
| `tools/patches/` | Изменения SDK и Mesa по шагам (история) |
| `patches/` | Итоговые изменения SDK и Mesa для сборки |
| `extras/` | Иконка |
