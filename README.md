# SCM dataset generator

Проект для последовательного расчета энергий центральной частицы методом matrix SCM по локальным конфигурациям из `*.pkl`.

Метод опирается на validated matrix SCM implementation из `vanyasimkin/article_scm_triplets`: там описана физическая постановка с `eps1_r=3.9`, `eps2_r=81.0`, `a=1.06e-6`, `E0=1e5`, `n_orient=8`, а ядро находится в `scm_core.py`. Репозиторий также указывает, что геометро-зависимая transfer matrix собирается один раз для фиксированной геометрии и `lmax`, а затем переиспользуется для всех ориентаций поля, что важно для скорости расчета.

## Входной формат

Ожидается `pkl` со списком конфигураций. В каждой конфигурации:

```python
cfg[0]   # центральная частица в (0, 0)
cfg[1:]  # соседи после отсечения r/d <= 6
```

Если координаты безразмерные в единицах диаметра `d`, оставь в конфиге:

```yaml
coordinates:
  units: diameter
```

Тогда перед SCM координаты переводятся в СИ как `centers = coords * d`, где `d = 2a`.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Скопируй `scm_core.py` из основного репозитория:

```bash
cp /path/to/article_scm_triplets/scm_core.py vendor/scm_core.py
```

Или попробуй скачать автоматически:

```bash
python scripts/fetch_scm_core.py
```

## Запуск

Скопируй один из split-файлов в `data/input/`, например:

```text
data/input/coordinates_cut_r6_part_01.pkl
```

Создай конфиг:

```bash
cp config.example.yaml config.part01.yaml
```

Проверь в нем пути:

```yaml
input_pkl: data/input/coordinates_cut_r6_part_01.pkl
output_dir: data/output/part_01_lmax5
scm:
  lmax: 5
```

Запуск:

```bash
python run_dataset.py --config config.part01.yaml
```

Smoke test на 3 конфигурациях:

```bash
python run_dataset.py --config config.part01.yaml --max-configs 3
```

## Resume после отключения электричества

Результаты пишутся после каждой конфигурации в два файла:

```text
results.jsonl
summary.csv
```

При повторном запуске скрипт читает `results.jsonl` и пропускает `config_id`, которые уже имеют `status="ok"`.

```bash
python run_dataset.py --config config.part01.yaml
```

Для принудительного пересчета без resume:

```bash
python run_dataset.py --config config.part01.yaml --no-resume
```

## Что сохраняется

Главный файл: `results.jsonl`, одна строка на конфигурацию. Ключевые поля:

- `config_id`
- `n_particles`
- `lmax`
- `U_total_avg_J`
- `U_center_avg_J`
- `U_single_avg_J`
- `Phi_center_avg_J = <U_center - U_single>`
- `Phi_center_orient_J`
- `elapsed_s`
- `status`

`Phi_center_avg_J` — основная величина для датасета: энергия центральной частицы с вычитанием энергии одиночной сферы в той же ориентации поля.

## Как раздать на 5 компьютеров

На каждом компьютере свой input/output:

```bash
python run_dataset.py --config config.part01.yaml
python run_dataset.py --config config.part02.yaml
python run_dataset.py --config config.part03.yaml
python run_dataset.py --config config.part04.yaml
python run_dataset.py --config config.part05.yaml
```

Для каждого компьютера достаточно перенести:

```text
vendor/scm_core.py
requirements.txt
run_dataset.py
src/
config.partXX.yaml
data/input/coordinates_cut_r6_part_XX.pkl
```

## Инициализация GitHub-репозитория

```bash
git init
git add .
git commit -m "Initial SCM dataset generator"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

Большие `*.pkl` не коммить: они исключены через `.gitignore`.
