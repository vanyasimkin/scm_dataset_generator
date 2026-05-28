# Vendor SCM core

Put `scm_core.py` from the validated repository here:

https://github.com/vanyasimkin/article_scm_triplets

Minimal expected API:

- `SCMParams`
- `MatrixSCMSystem`
- `fibonacci_sphere_points`
- `rotating_field_k`
- `analytic_single_sphere_bem_like_energy`

You can copy it manually:

```bash
cp /path/to/article_scm_triplets/scm_core.py vendor/scm_core.py
```

or use the helper:

```bash
python scripts/fetch_scm_core.py
```
