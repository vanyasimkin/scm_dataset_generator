from pathlib import Path
from urllib.request import urlretrieve

URL = "https://raw.githubusercontent.com/vanyasimkin/article_scm_triplets/main/scm_core.py"
OUT = Path(__file__).resolve().parents[1] / "vendor" / "scm_core.py"

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL}")
    urlretrieve(URL, OUT)
    print(f"Saved to {OUT}")
