# Florida

<p align="center">
  <a href="https://github.com/cergo666/Florida/releases"><img src="https://img.shields.io/github/v/release/cergo666/Florida?style=flat-square&logo=github" alt="release"></a>
  <a href="https://github.com/cergo666/Florida/releases"><img src="https://img.shields.io/github/downloads/cergo666/Florida/total?style=flat-square&color=blue" alt="downloads"></a>
  <a href="https://github.com/cergo666/Florida/releases/latest"><img src="https://img.shields.io/github/downloads/cergo666/Florida/latest/total?style=flat-square&label=latest%20downloads" alt="latest downloads"></a>
  <a href="https://github.com/cergo666/Florida/stargazers"><img src="https://img.shields.io/github/stars/cergo666/Florida?style=flat-square" alt="stars"></a>
  <a href="https://github.com/cergo666/Florida/actions/workflows/build.yml"><img src="https://img.shields.io/github/actions/workflow/status/cergo666/Florida/build.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/cergo666/Florida?style=flat-square" alt="license"></a>
</p>

<p align="center">
  <b>Русский</b> · <a href="README_EN.md">English</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/cergo666/MagiskHluda"><img src="https://img.shields.io/github/v/release/cergo666/MagiskHluda?style=flat-square&label=MagiskHluda" alt="MagiskHluda"></a>
</p>

Патченый [Frida](https://github.com/frida/frida) для Android: с бинарника снимаются известные строки-отпечатки (`gum-js-loop`, `frida-agent-*.so`, `frida_agent_main`, порт `27042`, `ggbond`, `/memfd:jit-cache` и другие).

Каждый прогон CI даёт **новый** набор имён и **новый** порт. Значения лежат в `florida-identities-<version>.json` рядом с артефактами релиза.

## Экосистема

| Репозиторий | Роль |
|---|---|
| **Florida** (этот) | сборка `florida-server` / gadget / inject |
| [MagiskHluda](https://github.com/cergo666/MagiskHluda) | Magisk / KernelSU / APatch-модуль, старт на boot |
| [Ylarod/Florida](https://github.com/Ylarod/Florida) | исходный форк |

## Установка на устройство

Два пути. `hluda` из MagiskHluda сюда **не** копируется: там порт берётся из `module.cfg` модуля, здесь — из `identities.json`.

### Magisk / KernelSU / APatch

Поставьте [MagiskHluda](https://github.com/cergo666/MagiskHluda). Сервер поднимается на boot, порт в `module.cfg`. С хоста:

```bash
hluda ps
hluda -f com.example.app
```

`hluda` живёт в репозитории MagiskHluda: `scripts/hluda`.

### Вручную (этот репозиторий)

1. Скачайте с [Releases](https://github.com/cergo666/Florida/releases) `florida-server-*-android-<arch>.gz` и **тот же** `florida-identities-<version>.json`.
2. Распакуйте сервер и поставьте скриптом — он пушит бинарник, ставит `chmod` и печатает команды с портом из JSON:

```bash
gunzip -k florida-server-*-android-arm64.gz
python3 install.py \
  --server florida-server-*-android-arm64 \
  --identities florida-identities-*.json
```

3. Дальше выполните то, что скрипт напечатал: старт на устройстве и `adb forward`. Бинарник кладётся в `/data/local/tmp/app_process` (не `frida-server` — это строка для детекта).

Без скрипта то же самое руками — см. [Подключение](#подключение).

## Скрипты

Всё для сборки лежит в `scripts/`. Для **установки на девайс** нужен корневой [`install.py`](install.py).

| Скрипт | Зачем |
|---|---|
| [`install.py`](install.py) | **Установка** на телефон или эмулятор: `adb push` + chmod, печать `adb forward` / `frida-ps -H` с портом из identities |
| [`identities.py`](scripts/identities.py) | Сгенерировать `identities.json` (имена, порт, XOR для RPC) |
| [`rewrite.py`](scripts/rewrite.py) | Вписать identities в checkout Frida. `--check` только проверяет якоря, дерево не трогает |
| [`strip-fingerprints.py`](scripts/strip-fingerprints.py) | Замена `gmain` / `gdbus` той же длины в ELF. CI вешает его на `post-process.py`, руками обычно не вызывают |
| [`scan_binary.py`](scripts/scan_binary.py) | Проверка, что в бинарнике не осталось `gum-js-loop`, `27042`, `frida:rpc` и т.п. |

`rewrite.py` работает по **рабочей копии** Frida. Не гоняйте его по дереву, которое хотите оставить нетронутым.

## Подключение

Сервер слушает **не** `27042`, а `control_port` из identities. После `install.py` (или ручного пуша):

```bash
adb shell su -c '/data/local/tmp/app_process -l 127.0.0.1:<control_port>'
adb forward tcp:<control_port> tcp:<control_port>
frida-ps -H 127.0.0.1:<control_port>
frida -H 127.0.0.1:<control_port> -f com.example.app
```

Полностью вручную, без скрипта:

```bash
adb push florida-server /data/local/tmp/app_process
adb shell su -c 'chmod 755 /data/local/tmp/app_process'
adb shell su -c '/data/local/tmp/app_process'
```

Если нужен стоковый `frida -U` (он всегда открывает `tcp:27042` на устройстве):

```bash
adb shell su -c '/data/local/tmp/app_process -l 127.0.0.1:27042'
```

Приложения, которые только тыкают `27042`, кастомный порт не увидят. Те, что сканируют все localhost-порты, по-прежнему видят handshake Frida — без смены протокола (и клиента) это не убрать.

## Чем этот форк отличается от [Ylarod/Florida](https://github.com/Ylarod/Florida)

Одинаково: это всё ещё Frida по протоколу. Стоковый `frida` CLI работает. D-Bus `re.frida.*` и GObject-имена вроде `frida_agent_message_transmitter_*` **не** переименовываются (их ждёт официальный клиент). Inline-хуки и сверка `.text` с диском так же не прячутся.

| | [Ylarod/Florida](https://github.com/Ylarod/Florida) | Этот форк |
|---|---|---|
| Как патчится Frida | `git am` нумерованных `.patch` | `scripts/rewrite.py` — якоря с подсчётом вхождений |
| Имена потоков / memfd / agent | фиксированные (`ggbond`, `jit-cache`, экспорт `main`, …) | **случайные на каждую CI-сборку** (`identities.py`) |
| Порт | классический **27042** | свой `control_port` (не 27042), в `florida-identities-*.json` |
| Listen | обычно все интерфейсы | по умолчанию **127.0.0.1** (модуль MagiskHluda) |
| `frida:rpc` в бинарнике | double-Base64 — известный блоб | XOR в рантайме; по проводу по-прежнему `frida:rpc` |
| Снятие строк с ELF | `sed` / в основном agent `.so` | исходники + same-length replace `gmain`/`gdbus`; server, gadget, inject |
| Бамп upstream Frida | патчи часто не накладываются | якоря проверяются (`rewrite.py --check`); при сдвиге CI падает явно |
| Релиз | `florida-server-*` | то же + **`florida-identities-<version>.json`** |
| Проверки сборки | нет скана отпечатков | unittest + `scan_binary.py` (нет `gum-js-loop`, `27042`, `frida:rpc`, …) |
| На устройство | руками `adb push` | [`install.py`](install.py); на boot — [этот MagiskHluda](https://github.com/cergo666/MagiskHluda) + `hluda` |
| Magisk-модуль | [Exo1i/MagiskHluda](https://github.com/Exo1i/MagiskHluda): `0.0.0.0:27042`, без identities | [cergo666/MagiskHluda](https://github.com/cergo666/MagiskHluda): порт из JSON, **127.0.0.1**, обёртка `hluda` (таблица там) |
| Документация | короткий README | RU + EN, установка и таблица скриптов |

## Сборка

Нужен checkout Frida с сабмодулями `frida-core` и `frida-gum`.

```bash
python3 scripts/identities.py -o identities.json
python3 scripts/rewrite.py --frida-dir /path/to/frida --identities identities.json

# проверка якорей на чистом дереве (дерево не меняется)
python3 scripts/rewrite.py --frida-dir /path/to/frida --check --seed ci
```

Дальше обычная сборка Frida (`./configure --host=android-arm64 && make`).

На устройство из локальной сборки:

```bash
python3 install.py \
  --server build-android-arm64/subprojects/frida-core/server/frida-server \
  --identities identities.json
```

## Тесты

Только stdlib `unittest`, без pytest:

```bash
python3 -m unittest discover -s tests -v
```

CI: эти тесты, затем `rewrite.py --check` на свежем клоне Frida, затем `scripts/scan_binary.py` по собранным `frida-server` / gadget / inject.

## Ограничения

Правки исходников не прячут inline-хуки и проверку `.text` против диска. Это уже инструментация, а не строка. Если Florida всё ещё ловят, можно смотреть в сторону [ZygiskFrida](https://github.com/lico-n/ZygiskFrida).

## Ссылки

- [Frida](https://github.com/frida/frida)
- [DetectFrida](https://github.com/darvincisec/DetectFrida)
- [AntiFrida](https://github.com/qtfreet00/AntiFrida)
- [Ylarod/Florida](https://github.com/Ylarod/Florida)
- [MagiskHluda](https://github.com/cergo666/MagiskHluda)

<p align="center">
  <a href="https://github.com/cergo666/Florida/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=cergo666/Florida" alt="contributors">
  </a>
</p>
