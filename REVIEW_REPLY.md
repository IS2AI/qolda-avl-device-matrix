# Reply text for the review thread

Replace `<REPO_URL>` with the published repository URL, and pin a commit hash so
the link keeps meaning the same thing after later edits.

Every claim below is checkable against a file in this repository.

---

## Russian

Измеренная матрица устройств опубликована: `<REPO_URL>`

Что в ней есть:

- `merged_results.csv` — все 471 измеренных запуска с трёх устройств в одной
  таблице. Каждое число в отчётах ссылается на строку в этом файле. Столбцы
  `device_id`, `source_file` и `source_row` дают обратную ссылку на исходный CSV
  конкретного устройства.
- `cross_device_summary.md` — сравнение между устройствами: границы измерения,
  таблицы по вариантам и режимам, и раздел о том, какие метрики между
  устройствами сопоставимы, а какие нет.
- `validation_report.md` — проверки того, что все три устройства выполняли одно
  и то же: коммит llama.cpp, sha256 артефактов, параметры генерации, число
  токенов промпта, сетка покрытия и все отклонения от протокола.
- Код каждого устройства в его папке (`rtx/`, `macbook/`, `one-plus/`) вместе со
  скриптами сборки и запуска. Входные данные — в `protocol/`, sha256 всех файлов
  — в `MANIFEST.md`. Скрипт `verify.sh` проверяет целостность данных без
  запуска бенчмарка.

Измерено:

| класс устройства | оборудование | бэкенд | строк |
|---|---|---|---|
| ноутбук с дискретным GPU | ASUS ROG Zephyrus G16, RTX 4090 Laptop, 16 ГБ VRAM | CUDA | 160 |
| ноутбук с объединённой памятью | MacBook Pro, Apple M4 Pro, 24 ГБ | Metal | 160 |
| флагманский смартфон | OnePlus 13R, Snapdragon 8 Gen 3, 16 ГБ LPDDR5X | CPU (ARM NEON/i8mm) | 151 |

Пять вариантов GGUF: BF16, Q8_0, Q6_K, Q5_K_M, Q4_K_M. Шесть режимов: текст
128 / 513 / 2048 токенов, изображение, аудио 10 с и 30 с. По пять повторов на
ячейку плюс две контрольные ячейки на устройство. Все три устройства работали на
llama.cpp `ea63b4d` с патчем `qwen3avl-support.patch`, на одних и тех же файлах
модели, с одинаковыми параметрами генерации и побайтово одинаковыми входными
данными. Это проверено по исходным файлам и зафиксировано в
`validation_report.md`.

Полнота сетки: все 471 строка — завершённые измерения, без частичных и
неудачных запусков. На Android четыре ячейки BF16
(`text-2048`, `vision`, `audio-10s`, `audio-30s`) не запускались: prefill BF16
на этом устройстве составляет 1.42 ток/с, то есть один запуск занял бы 20–25
минут и упёрся бы в разряд батареи. Причина указана в `one-plus/summary.md`;
в CSV этих строк нет, и они нигде не восполнены оценкой.

В каждой ячейке приведены пропускная способность декодирования, TTFT, prefill,
пиковая занятая память и среднее энергопотребление. Пропускная способность для
текстового и мультимодального режимов приведена отдельно.

Ключевой результат по варианту Q4_K_M (медиана из 5 запусков):

| | RTX 4090 Laptop | M4 Pro | Snapdragon 8 Gen 3 |
|---|---:|---:|---:|
| декодирование, текст | 91.4 ток/с | 75.8 ток/с | 9.78 ток/с |
| декодирование, изображение | 88.9 ток/с | 72.3 ток/с | 6.68 ток/с |
| TTFT, текст-128 | 0.243 с | 0.163 с | 2.93 с |
| TTFT, изображение | 1.37 с | 2.26 с | 161 с |
| пиковая память | 7.11 ГиБ VRAM | 5.32 ГиБ | 5.49 ГиБ RSS |

Два ограничения указаны явно.

Первое: три устройства измеряют мощность на трёх разных границах. RTX 4090
измеряется по GPU package (`nvidia-smi`), MacBook по SoC package
(`powermetrics`, CPU + GPU), Android по разряду батареи всего устройства. Эти
границы охватывают разное оборудование, поэтому энергетические показатели
приводятся тремя отдельными блоками, каждый со своей подписью, а не в одной
таблице.

Второе: на смартфоне текстовый режим работоспособен, а мультимодальный
практически нет. 161 секунда до первого токена на изображении объясняется тем,
что один только визуальный энкодер занимает 133–135 секунд на CPU. Это измерено,
а не оценено.

Отдельно по замечанию про Docker-контейнер `IS2AI/Qolda-deployment`. Матрица
выше получена не через него, а через `llama.cpp` с GGUF-квантизациями
`issai/Qolda-AVL-5B-GGUF`. Q4_K_M занимает 2.326 ГиБ весов и работает резидентно
на смартфоне без дискретного GPU, при среднем потреблении 7.32 Вт по разряду
батареи. Команда запуска приведена в `README.md`. Границы применимости для
каждого устройства разобраны в `cross_device_summary.md`.

---

## English

The measured device matrix is published at `<REPO_URL>`.

It contains `merged_results.csv` (all 471 measured runs from three devices in one
table, with `device_id` / `source_file` / `source_row` pointing every row back to
its source CSV), `cross_device_summary.md` (the cross-device comparison and an
explicit section on which metrics are comparable across devices), and
`validation_report.md` (proof that all three devices ran the same commit, the
same hash-verified model files, the same generation settings and byte-identical
inputs). Each device folder carries the driver code that produced its rows plus
build and run scripts. `MANIFEST.md` gives sha256 for every file, and
`verify.sh` checks the published data without running the benchmark.

Measured: three device classes (RTX 4090 Laptop on CUDA, Apple M4 Pro on Metal,
Snapdragon 8 Gen 3 on ARM CPU), five GGUF variants (BF16, Q8_0, Q6_K, Q5_K_M,
Q4_K_M), six modes (text at 128 / 513 / 2048 tokens, image, 10 s audio, 30 s
audio), five repetitions per cell plus two control cells per device. Each cell
reports decode throughput, TTFT, prefill, peak resident memory and average power,
with text and multimodal throughput given separately.

Grid completeness: all 471 rows are completed measurements, none partial or
failed. Four BF16 cells on Android
(`text-2048`, `vision`, `audio-10s`, `audio-30s`) were not run, because BF16
prefill on that device is 1.42 tok/s, putting a single run at 20 to 25 minutes
and into the battery floor. The reason is recorded in `one-plus/summary.md`;
those rows are absent from the CSV and are not filled in by estimation anywhere.

Two limits are stated in the report rather than smoothed over.

The three devices measure power at three different boundaries (GPU package, SoC
package, whole device battery), which enclose different hardware, so energy
figures appear in three separately labelled blocks instead of one table.

On the phone, text generation is usable at 9.78 tok/s and the multimodal path is
not: 161 s to first token on an image, because the vision encoder alone costs
133 to 135 s on CPU. That figure is measured, not estimated.

On the Docker point: this matrix was produced through `llama.cpp` with the
`issai/Qolda-AVL-5B-GGUF` quantizations, not through the
`IS2AI/Qolda-deployment` container. Q4_K_M is 2.326 GiB of weights and runs
resident on the phone with no discrete GPU, drawing 7.32 W at the battery. The
launch command is in `README.md`. The feasibility boundary for each device is
given in `cross_device_summary.md`.

---

## 3. Before you post

- Replace `<REPO_URL>` in both blocks and pin a commit hash.
- `README.md` and the reports name the devices, including the MacBook's OS build
  and the phone's model number. Check that is acceptable to publish.
