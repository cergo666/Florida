# Florida

Патченый [Frida](https://github.com/frida/frida) для Android: с бинарника снимаются известные строки-отпечатки (`gum-js-loop`, `frida-agent-*.so`, `frida_agent_main`, порт `27042`, `ggbond`, `/memfd:jit-cache` и другие).

Каждый прогон CI даёт **новый** набор имён и **новый** порт. Значения лежат в `florida-identities-<version>.json` рядом с артефактами релиза.

**Русский** · [English](README_EN.md)

Форк: [Ylarod/Florida](https://github.com/Ylarod/Florida). Magisk-модуль: [MagiskHluda](https://github.com/cergo666/MagiskHluda).

## Что изменилось относительно старых патчей

| Было | Стало |
|---|---|
| `ggbond` / `jit-cache` / экспорт `main` | случайные значения на каждую сборку |
| double-Base64 `frida:rpc` (известный блоб) | XOR в рантайме; по проводу по-прежнему `frida:rpc`, чтобы работал стоковый `frida` CLI |
| `sed` по ELF | правки исходников + замена той же длины для `gmain`/`gdbus` в `post-process.py` |
| `git am`, который ломается на каждом бампе Frida | `scripts/rewrite.py` с подсчётом якорей |
| strip только у agent `.so` | тот же strip у server, gadget, inject |
| TCP **27042** | порт сборки (см. identities JSON) |

Намеренно **не** переименовывается: D-Bus `re.frida.*` (его ждёт официальный клиент). Имена GObject вроде `frida_agent_message_transmitter_*` тоже остаются — детекторы обычно ищут не их, а `gum-js-loop`, `frida-agent-*.so`, порт `27042`.

Правки исходников не прячут inline-хуки и проверку `.text` против диска. Это уже инструментация, а не строка.

## Скачать

Артефакты релиза: `florida-server-*` / `florida-gadget-*` / `florida-inject-*`.

## Подключение

Сервер больше не слушает `27042`. Порт берите из `florida-identities-*.json`:

```bash
adb push florida-server /data/local/tmp/app_process
adb shell su -c 'chmod 755 /data/local/tmp/app_process'
adb shell su -c '/data/local/tmp/app_process'   # 127.0.0.1:<control_port>
adb forward tcp:<control_port> tcp:<control_port>
frida-ps -H 127.0.0.1:<control_port>
```

Если нужен стоковый `frida -U` (он всегда открывает `tcp:27042` на устройстве):

```bash
adb shell su -c '/data/local/tmp/app_process -l 127.0.0.1:27042'
```

Приложения, которые только тыкают `27042`, кастомный порт не увидят. Те, что сканируют все localhost-порты, по-прежнему видят handshake Frida — без смены протокола (и клиента) это не убрать.

Бинарник на устройстве лучше переименовать. `frida-server` в `/data/local/tmp` сам по себе строка для детекта.

## Сборка

Нужен checkout Frida с сабмодулями `frida-core` и `frida-gum`.

```bash
python3 scripts/identities.py -o identities.json
python3 scripts/rewrite.py --frida-dir /path/to/frida --identities identities.json

# проверка якорей на чистом дереве (дерево не меняется)
python3 scripts/rewrite.py --frida-dir /path/to/frida --check --seed ci
```

Дальше обычная сборка Frida (`./configure --host=android-arm64 && make`).

`scripts/rewrite.py` работает по **рабочей копии**. Не гоняйте его по дереву, которое хотите оставить нетронутым.

## Тесты

Только stdlib `unittest`, без pytest:

```bash
python3 -m unittest discover -s tests -v
```

CI: эти тесты, затем `rewrite.py --check` на свежем клоне Frida, затем `scripts/scan_binary.py` по собранным `frida-server` / gadget / inject.

## Ссылки

- https://github.com/frida/frida
- https://github.com/darvincisec/DetectFrida
- https://github.com/qtfreet00/AntiFrida
- https://github.com/Ylarod/Florida
- https://github.com/cergo666/MagiskHluda
