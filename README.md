# PostgreSQL 17 GiST at 500 Million Geo-Points

Reproducible Docker assignment showing how PostgreSQL GiST changes the nearby-
places workload at 500 million rows, plus a measured comparison with geohashing.

The experiment was executed on 12 November 2026 on a Hetzner CPX42 VM:

- 8 AMD vCPU, 16 GB RAM, 320 GB SSD
- Docker 27.5.1 and Docker Compose 2.32.4
- PostgreSQL 17.5 with PostGIS 3.5
- Dockerized pgAdmin 4 accessed through an SSH tunnel

## Results

| Query | Before GiST | After GiST - cold | After GiST - warm | Indexed plan |
|---|---:|---:|---:|---|
| NYC bounding box | 21,820.542 ms | 63.938 ms | 1.263 ms | Bitmap Index + Heap |
| Circle | 22,121.710 ms | 0.093 ms | 0.086 ms | Bitmap Index + Heap |
| Top-100 K-NN | 29,897.233 ms | 0.321 ms | 0.295 ms | Ordered GiST Index Scan |
| Polygon `COUNT(*)` | 21,644.234 ms | 3.798 ms | 0.181 ms | GiST Index Only Scan |
| Polygon rows (extension) | same predicate | 13.597 ms | 0.151 ms | Bitmap Index + Heap |

Dataset and index evidence:

- Exact row count: **500,000,000**
- Planner estimate after `ANALYZE`: **499,995,584**
- Heap: **36 GB**
- Primary-key index: **10 GB**
- GiST index: **31 GB**
- GiST build time: **14 minutes 10.698 seconds**
- Complete automated pipeline: **25 minutes**

## Geohash extension

The comparison uses the same first 50 million rows:

- Geohash B-tree: 1,071 MB
- Comparison GiST: 3,181 MB
- Coarse `dr%` prefix: 48,768 candidates for 108 true rows
- False positives: 48,660
- Precision: 0.221%; recall: 100%
- Overfetch: 451.6x
- 877 of 1,000 point pairs about 101 m apart crossed precision-7 cell boundaries
- The Times Square precision-5 cell contained only 2 rows, so it cannot answer
  top-100 nearest neighbors without widening and querying neighboring cells

Conclusion: geohash is useful as a shard/partition prefix and cache key, while
GiST is the better in-database structure for exact containment and K-NN. A
distributed design can combine both.

## Repository layout

```text
compose.yaml          PostgreSQL 17/PostGIS + pgAdmin Docker stack
scripts/              loader, step runner, status and bootstrap scripts
sql/                  tutorial queries and measured extensions
evidence/transcripts/ exact psql/system transcripts from the 500M run
report/               PDF and Excalidraw generators
output/pdf/            final 14-page assignment PDF
output/excalidraw/     editable one-page visual summary
```

## Reproduce

Create a private `.env` from `.env.example`, then:

```bash
docker compose up -d
bash scripts/run-step.sh 01_schema
TOTAL=500000000 WORKERS=4 BATCH=10000000 bash scripts/run-load.sh
bash scripts/run-step.sh 03_finalize_load
bash scripts/run-step.sh --cold 04_baseline
bash scripts/run-step.sh 05_index
bash scripts/run-step.sh --cold 06_after_gist
bash scripts/run-step.sh 07_verify
bash scripts/run-step.sh 08_geohash
bash scripts/run-step.sh --cold 09_polygon_bitmap
bash scripts/run-step.sh --cold 10_geohash_isolated
```

`scripts/bootstrap.sh` runs steps 01 through 08 unattended and fails before
index creation if the one-shot baseline fails.

## Methodology notes

- The bulk fixture is `UNLOGGED` to avoid WAL duplication for regenerable data.
- Four loaders use disjoint ID ranges; the sequence and primary key are restored
  before measurements, so the final schema matches the tutorial.
- Cold passes restart PostgreSQL and clear the Linux page cache; warm passes run
  the same SQL immediately afterward.
- Built-in PostgreSQL `POINT` treats longitude/latitude as planar degrees. Use
  PostGIS geography for production geodesic distances.
- The polygon `COUNT(*)` naturally becomes an Index Only Scan in PostgreSQL 17.
  `09_polygon_bitmap.sql` returns complete rows to demonstrate the rubric's
  requested Bitmap Index + Bitmap Heap plan without disabling planner choices.

## Report and evidence

- [Final PDF](output/pdf/postgres_gist_500m_assignment.pdf)
- [Editable Excalidraw summary](output/excalidraw/postgres-gist-500m-summary.excalidraw)
- [Before-GiST transcript](evidence/transcripts/04_baseline-20261112-051316.txt)
- [After-GiST transcript](evidence/transcripts/06_after_gist-20261112-053044.txt)
- [Verification transcript](evidence/transcripts/07_verify-20261112-053045.txt)
- [Geohash transcript](evidence/transcripts/08_geohash-20261112-053106.txt)

All reported timings come from the committed transcripts rather than copied
tutorial output.

## References

- Tutorial: https://medium.com/@jramcloud1/21-postgresql-17-performance-tuning-gist-generalized-search-tree-8e5cacea9fc8
- Automation baseline: https://github.com/nabeel-hussain/postgres-gist-500m-geopoints
- PostgreSQL 17 documentation: https://www.postgresql.org/docs/17/
- PostGIS documentation: https://postgis.net/docs/
