# Изменения / Changes

## 0.2.0 — 2026-11-06

- CPU: native-помощники поиска823D9740/823DB370 с startup-проверкой и исходным fallback; в отдельном контролируемом CPU-замере время снизилось на20.7%/28.6%, это не процент прироста всей игры.
- Рендер: объединённые проверенные флаги descriptor/upload/memo/ZCULL, source-epoch revalidation, ограниченные image/material/staging caches, ring writeback. Отвергнутые AlphaCompare/ReadyTextures и повышение приоритета Main выключены.
- Исправлено замедление камеры/движения/анимации внутри проверенного помещения: min_frame_vblanks=1, immediate_flip=false. В проверке54.9FPS внутри, в конце после выхода29.9swaps/s; не обещается постоянный30FPS cap во всех внешних сценах.
- Загрузка востребованной текстуры дожидается существующего stream job. Пустые pending-подстановки устранены в этом пути; отдельное мерцание при новом регионе остаётся известной проблемой.
- Строгий PGO USE, 161 неизменённый профиль включая renderer; без нового GEN, missing-profile/coverage-mismatch0. Релизный захват кадров/clock diagnostics выключены.
- Оформление0.2.0, форвардер с четырьмя ядрами, русские/английские инструкции установки и обновления. В публичном пакете нет игровых данных и кешей; частный полный комплект включает проверенный накопленный кеш238шейдеров/1920pipeline.

### English

- Native integer table helpers with startup equivalence checks and original fallback; isolated CPU-workload time reductions20.7%/28.6% are not whole-game FPS gains.
- Tested descriptor/upload/memo/ZCULL flags, source-epoch revalidation, bounded image/material/staging caches and ring writeback. Rejected AlphaCompare/ReadyTextures/Main-priority experiments remain off.
- Fixed the tested interior's slow camera/movement/animation by preserving guest cadence. No universal30FPS outdoor guarantee.
- Referenced stream textures are completed before drawing; brief building flicker on new-area transitions remains a known limitation.
- Strict PGO USE with161 unchanged profiles, including renderer; no new training, zero missing/mismatch diagnostics. Test capture/clock diagnostics disabled.
- Version0.2.0 packaging, four-core forwarder, bilingual installation/update documentation. Public packages exclude game data/caches; the private full package includes the validated recorded238shader/1920pipeline cache.
