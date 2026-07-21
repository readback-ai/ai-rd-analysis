# GENERATED quarterly report — scripts/report.py

> Q1-2024 columns are a detector-validity check and review-practice baseline,
> NOT an AI-usage estimate: the detectable channels (trailers, agent accounts,
> branch conventions) did not exist yet, while autocomplete-era assistance was
> already widespread and is invisible to every layer. All rates are floors
> (one quantified exception: the two-sided bound section).

## Contributor-weighted metrics
```
period   weighting        repos           ai_code       ai_involved            merged       rejected_w8          limbo_w8      human_review         ai_review  other_bot_review         no_review           insider       self_merged         m_hum_rev          m_ai_rev          m_no_rev
Q1-2024  equal-weight       465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   77.3 [75.3,79.2]   14.4 [13.0,15.9]    8.3 [ 7.1, 9.5]   52.0 [49.1,55.0]    0.4 [ 0.1, 0.9]    0.9 [ 0.4, 1.5]   47.2 [44.2,50.3]   34.1 [31.2,37.1]   55.5 [52.7,58.3]   61.8 [58.3,65.2]    0.5 [ 0.0, 1.2]   37.4 [34.0,40.7]
Q1-2024  contrib-weight     465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   75.6 [68.9,81.0]   16.6 [12.5,21.9]    7.9 [ 5.9,10.2]   58.7 [51.3,64.6]    0.7 [ 0.0, 1.9]    0.9 [ 0.4, 1.5]   40.3 [34.4,46.9]   30.0 [25.8,35.0]   53.2 [48.0,59.4]   69.2 [61.2,76.6]    0.7 [ 0.0, 2.0]   29.9 [23.0,38.2]
Q4-2025  equal-weight       825    3.3 [ 2.6, 4.1]    4.6 [ 3.8, 5.5]   71.4 [69.7,73.1]   16.3 [15.2,17.5]   12.3 [11.2,13.5]   50.2 [48.0,52.4]   14.3 [12.6,16.0]    3.8 [ 2.7, 5.0]   42.4 [40.2,44.6]   35.9 [33.6,38.2]   54.8 [52.5,57.0]   63.9 [61.3,66.5]   15.5 [13.5,17.4]   30.2 [27.7,32.5]
Q4-2025  contrib-weight     825    2.1 [ 1.6, 2.6]    3.0 [ 2.4, 3.7]   72.0 [68.2,75.0]   17.8 [15.5,21.0]   10.2 [ 8.7,11.6]   61.0 [57.0,64.6]   24.4 [17.6,31.6]    3.4 [ 2.3, 4.7]   30.8 [26.7,35.3]   34.4 [30.3,38.4]   52.2 [46.5,58.2]   74.4 [69.4,79.0]   26.1 [18.9,33.4]   20.3 [15.7,25.5]
Q1-2026  equal-weight      1008   12.0 [10.9,13.2]   13.6 [12.5,14.7]   68.1 [66.5,69.6]   18.1 [17.1,19.1]   13.8 [12.6,15.1]   43.2 [41.3,45.3]   16.0 [14.4,17.6]    3.7 [ 2.8, 4.7]   48.3 [46.2,50.4]   34.7 [32.7,36.8]   52.9 [50.9,55.0]   57.7 [55.3,60.1]   17.5 [15.8,19.3]   35.5 [33.1,37.9]
Q1-2026  contrib-weight    1008    8.7 [ 7.5,10.0]   10.3 [ 9.0,11.7]   66.9 [63.2,70.5]   21.3 [18.7,24.3]   11.8 [10.4,13.4]   55.7 [52.2,58.8]   28.3 [22.4,34.5]    4.3 [ 2.9, 5.9]   32.6 [29.1,36.4]   32.5 [29.0,36.2]   52.4 [47.6,57.6]   71.5 [67.2,75.6]   29.9 [23.7,36.5]   21.3 [17.6,25.9]
WARN Q2-2026: 1 qualifying repos lack contributor weights (default 1.0) — e.g. ['sgl-project/ci-data']
Q2-2026  equal-weight      1154   15.8 [14.6,17.0]   18.7 [17.5,19.9]   67.3 [65.4,69.2]   17.2 [16.1,18.4]   15.6 [14.1,17.0]   41.7 [39.6,43.8]   16.4 [14.7,18.3]    4.7 [ 3.7, 5.8]   48.9 [46.6,51.2]   34.1 [32.2,35.9]   52.0 [49.9,54.2]   57.8 [55.1,60.4]   18.5 [16.5,20.5]   34.6 [32.2,37.1]
Q2-2026  contrib-weight    1154   13.8 [12.1,15.5]   16.9 [14.9,18.7]   64.3 [60.4,67.6]   21.3 [19.3,23.8]   14.4 [12.4,16.6]   54.7 [50.7,58.7]   28.0 [22.5,34.3]    5.9 [ 4.1, 8.0]   32.6 [29.2,37.0]   30.8 [27.1,34.7]   51.4 [46.2,56.7]   72.6 [67.5,77.0]   30.6 [23.9,37.4]   19.2 [16.0,23.2]

```

## Figure 2: Traceable AI usage over time (CW, 95% CI)
```
Figure 2: Traceable AI usage over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule; LOC capped 20k/PR; all values are floors
period    repos  AI% of submitted PRs    AI% of merged PRs   AI-PR% of subm LOC  AI-PR% of merged LOC
Q1-2024     465      0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]      0.0% [ 0.0, 0.0]
Q4-2025     825      3.0% [ 2.4, 3.7]     2.2% [ 1.6, 2.9]     4.3% [ 3.4, 5.3]      2.7% [ 1.9, 3.7]
Q1-2026    1008     10.3% [ 8.9,11.7]     8.8% [ 7.5,10.3]    13.6% [11.7,15.4]     11.1% [ 9.4,12.9]
Q2-2026    1154     16.9% [14.8,18.8]    13.6% [11.6,15.7]    22.4% [19.7,25.0]     17.0% [14.3,19.7]

```

## Figure 3: Merged LOC per core contributor over time (CW, 95% CI)
```
Figure 3: Submitted and merged LOC per core contributor over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule (Q2 provisional); core = insider PR authors; repos with >=2 insider authors
period    repos    CW submitted kLOC/author  x base     CW merged kLOC/author  x base
Q1-2024     251          9.56 [ 6.76,12.72]   1.00x        6.45 [ 4.66, 8.63]   1.00x
Q4-2025     469         14.00 [ 9.45,21.18]   1.46x       10.04 [ 6.45,15.56]   1.56x
Q1-2026     532         16.28 [12.79,20.84]   1.70x       10.71 [ 8.38,13.50]   1.66x
Q2-2026     581         26.90 [19.03,37.83]   2.81x       19.08 [13.19,27.65]   2.96x

```

## Layered decomposition (pooled)
```
period        PRs A marker% B agent% C branch%  union%
Q1-2024     72290     0.00%    0.00%     0.00%   0.00%
Q4-2025    134091     2.62%    0.97%     0.26%   3.85%
Q1-2026    197845     9.65%    1.21%     0.99%  11.84%
Q2-2026    288236    13.20%    0.43%     3.48%  17.11%

```

## Slices: involvement
```

=== repo-scoped ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     147    0.0 [ 0.0, 0.0]   61.5 [43.3,73.4]    0.5 [ 0.0, 1.7]   80.9 [76.1,84.3]
Q4-2025     178    3.7 [ 2.2, 5.7]   60.1 [51.0,67.7]   22.6 [12.4,35.1]   72.5 [68.1,76.2]
Q1-2026     196   10.5 [ 7.4,13.7]   55.0 [44.7,62.2]   29.7 [19.3,40.2]   65.9 [61.9,69.1]
Q2-2026     210   13.7 [10.0,17.0]   54.8 [48.0,61.2]   26.7 [17.7,34.9]   65.1 [59.9,69.2]

=== AI-heavy ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      77    0.0 [ 0.0, 0.0]   51.0 [38.0,66.0]    0.0 [ 0.0, 0.0]   86.0 [82.7,88.7]
Q4-2025     119    5.4 [ 2.4,10.6]   51.2 [43.1,58.3]   11.0 [ 5.4,20.9]   80.3 [75.2,83.1]
Q1-2026     144   10.7 [ 6.0,18.5]   49.0 [37.9,54.8]   11.5 [ 6.0,21.6]   78.9 [70.4,83.6]
Q2-2026     162   12.4 [ 6.7,20.6]   57.2 [37.7,71.2]   17.5 [ 8.2,33.4]   74.7 [69.6,77.9]

=== AI-majority ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     241    0.0 [ 0.0, 0.0]   59.2 [50.9,66.5]    0.9 [ 0.0, 2.6]   72.0 [61.8,80.1]
Q4-2025     528    2.3 [ 1.9, 2.8]   63.3 [58.3,67.5]   27.6 [18.4,35.3]   70.1 [65.2,74.0]
Q1-2026     668   10.2 [ 9.1,11.6]   57.2 [53.5,61.1]   31.3 [23.9,38.4]   64.7 [60.1,68.9]
Q2-2026     782   18.4 [16.5,20.4]   55.6 [51.2,59.3]   31.6 [24.5,38.4]   62.0 [57.3,66.3]

=== private ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     223    0.0 [ 0.0, 0.0]   55.6 [47.2,62.8]    1.5 [ 0.0, 4.3]   83.1 [81.1,84.9]
Q4-2025     444    4.4 [ 3.4, 5.7]   57.1 [49.5,63.3]   23.2 [15.3,31.9]   74.0 [69.2,77.4]
Q1-2026     565   14.8 [13.0,16.6]   49.3 [43.3,54.3]   26.6 [19.8,33.3]   66.8 [62.5,70.7]
Q2-2026     665   21.2 [19.6,23.1]   49.4 [43.1,54.6]   27.7 [20.7,34.9]   64.7 [59.5,69.1]

=== community ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      68    0.0 [ 0.0, 0.0]   63.1 [47.0,76.7]    0.1 [ 0.0, 0.4]   67.9 [49.9,82.5]
Q4-2025     110    2.0 [ 1.1, 3.4]   66.3 [60.3,73.0]   28.1 [12.0,47.8]   70.2 [58.9,77.8]
Q1-2026     138    6.3 [ 4.2, 9.0]   62.3 [57.7,67.1]   31.1 [13.7,50.1]   66.5 [55.3,76.8]
Q2-2026     146   12.3 [ 7.8,17.2]   63.8 [55.2,72.0]   31.8 [15.5,50.4]   62.1 [51.7,71.1]

=== public ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     174    0.0 [ 0.0, 0.0]   59.0 [48.9,69.1]    0.0 [ 0.0, 0.0]   71.0 [60.7,80.1]
Q4-2025     271    1.4 [ 0.9, 1.9]   62.0 [57.4,66.1]   22.3 [15.8,28.6]   70.3 [67.1,73.0]
Q1-2026     305    6.1 [ 5.1, 7.3]   60.7 [56.6,64.4]   28.4 [22.6,34.7]   67.4 [64.4,70.5]
Q2-2026     343   13.2 [11.3,15.6]   58.9 [54.7,63.0]   27.8 [21.6,34.3]   65.8 [62.6,69.0]

```

## Slices: self-merge
```

=== repo-scoped ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     147   51.6 [40.1,62.6]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   67.8 [47.9,82.6]
Q4-2025     178   48.1 [41.4,55.2]    2.0 [ 0.8, 3.7]    4.7 [ 2.3, 8.0]   50.7 [21.0,95.4]   66.1 [50.6,77.1]
Q1-2026     196   46.7 [40.9,53.4]    8.4 [ 4.4,12.2]   11.2 [ 7.1,16.1]   75.7 [50.0,92.7]   66.7 [51.1,78.9]
Q2-2026     210   44.1 [39.6,50.2]   15.2 [ 9.0,22.2]   14.5 [10.3,19.1]   79.6 [64.4,91.2]   70.7 [60.1,78.9]

=== AI-heavy ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      77   52.6 [45.1,59.9]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   51.9 [35.5,67.5]
Q4-2025     119   67.6 [49.6,79.9]    5.3 [ 2.1,11.4]    4.1 [ 1.7, 9.1]   45.0 [21.4,65.9]   51.7 [42.7,61.0]
Q1-2026     144   63.4 [47.1,73.8]   12.1 [ 5.9,23.1]    6.8 [ 3.3,12.7]   47.4 [27.3,65.1]   51.4 [39.9,59.2]
Q2-2026     162   65.2 [47.3,75.5]   10.6 [ 5.3,22.0]    6.4 [ 2.8,12.6]   40.6 [26.7,54.4]   64.1 [39.6,77.6]

=== AI-majority ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     241   53.8 [47.0,62.4]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   63.5 [49.2,74.9]
Q4-2025     528   50.7 [45.2,57.1]    1.0 [ 0.6, 1.5]    1.8 [ 1.0, 3.0]   64.0 [43.4,76.8]   72.4 [66.7,77.8]
Q1-2026     668   51.7 [46.2,57.5]    8.2 [ 6.9, 9.7]    8.5 [ 6.7,11.1]   68.5 [57.6,79.4]   68.3 [60.8,74.4]
Q2-2026     782   49.5 [43.1,55.8]   15.6 [12.9,18.5]   13.0 [10.9,15.1]   71.4 [55.6,85.1]   69.0 [61.4,76.7]

=== private ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     223   60.2 [52.4,67.5]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   56.0 [44.9,65.1]
Q4-2025     444   57.8 [51.8,63.6]    3.5 [ 2.3, 5.1]    4.1 [ 2.7, 5.9]   53.4 [33.2,68.5]   65.6 [58.9,73.0]
Q1-2026     565   58.0 [52.6,62.9]   13.5 [11.1,16.2]   12.7 [10.2,15.6]   62.0 [50.4,74.0]   60.2 [51.3,68.3]
Q2-2026     665   55.8 [49.7,61.2]   18.6 [15.8,21.4]   15.6 [12.9,18.3]   66.6 [51.1,78.7]   61.7 [52.6,69.9]

=== community ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      68   43.6 [36.4,52.9]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   66.2 [43.8,87.8]
Q4-2025     110   45.1 [30.5,62.7]    0.7 [ 0.2, 1.6]    1.4 [ 0.4, 3.4]   83.5 [42.4,94.6]   68.8 [56.5,81.4]
Q1-2026     138   44.3 [29.8,61.2]    5.1 [ 3.0, 8.3]    4.2 [ 2.5, 6.9]   69.3 [50.0,88.0]   66.4 [54.2,78.8]
Q2-2026     146   42.7 [28.6,57.7]   11.0 [ 5.9,18.7]    8.5 [ 5.3,12.4]   71.3 [43.7,94.3]   74.6 [57.4,86.0]

=== public ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     174   52.3 [43.7,59.9]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   75.6 [63.0,84.6]
Q4-2025     271   52.5 [47.6,57.7]    0.3 [ 0.1, 0.5]    1.7 [ 0.8, 2.7]   55.6 [ 0.0,100.0]   72.5 [65.5,78.8]
Q1-2026     305   51.3 [46.2,55.9]    4.1 [ 3.0, 5.6]    6.5 [ 4.8, 8.5]   85.4 [72.9,93.6]   74.9 [67.8,80.5]
Q2-2026     343   50.7 [46.5,55.4]   12.3 [ 8.6,16.7]   10.7 [ 8.1,13.6]   82.6 [74.5,88.8]   74.1 [66.3,80.9]

```

## Balanced-panel sensitivity
```
balanced panel: 332 repos qualify in all 4 quarters
period        panel ai_involved         cross-section
Q1-2024      0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]
Q4-2025      3.0 [ 2.2, 4.0]    3.0 [ 2.3, 3.7]
Q1-2026      9.9 [ 8.4,11.6]   10.3 [ 8.9,11.6]
Q2-2026     15.6 [13.2,17.9]   16.9 [15.0,18.7]

```

## Reviewer profile of merged PRs (unmerged = implicitly rejected)
```

=== repo-scoped ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     147   70.2 [51.6,82.7]    0.3 [ 0.0, 1.3]    0.1 [ 0.0, 0.3]   29.4 [16.0,46.2]
Q4-2025     178   55.3 [44.6,67.7]    3.3 [ 1.8, 5.1]   19.2 [ 9.4,30.8]   22.2 [13.5,33.9]
Q1-2026     196   49.8 [39.4,60.4]    6.7 [ 2.4,13.7]   24.0 [15.5,33.0]   19.5 [13.5,27.3]
Q2-2026     210   51.9 [43.7,60.1]    4.3 [ 2.0, 7.6]   24.6 [17.4,32.0]   19.2 [13.3,26.2]

=== AI-heavy ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      77   57.0 [41.9,73.3]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   43.0 [27.0,57.5]
Q4-2025     119   51.8 [41.8,58.6]    4.9 [ 2.1,10.8]    6.6 [ 2.5,13.7]   36.8 [24.4,43.6]
Q1-2026     144   51.3 [39.5,58.4]    5.4 [ 2.4,10.8]    6.1 [ 2.8,11.8]   37.2 [29.4,44.5]
Q2-2026     162   60.1 [36.2,75.8]   10.9 [ 4.0,22.1]    6.5 [ 3.3,12.8]   22.5 [14.4,35.2]

=== AI-majority ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     241   71.2 [61.5,80.3]    0.6 [ 0.0, 2.3]    0.3 [ 0.0, 0.8]   27.8 [19.2,39.0]
Q4-2025     528   52.8 [44.8,61.9]    4.7 [ 2.9, 7.0]   25.3 [16.3,34.3]   17.1 [12.6,23.5]
Q1-2026     668   46.3 [38.8,53.8]    5.9 [ 3.7, 8.4]   28.0 [21.1,35.6]   19.9 [15.7,25.2]
Q2-2026     782   47.0 [40.2,54.7]    4.9 [ 3.5, 6.6]   28.9 [21.3,36.3]   19.2 [15.0,25.3]

=== private ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     223   61.9 [51.7,70.5]    1.0 [ 0.0, 2.9]    0.4 [ 0.0, 1.0]   36.7 [28.9,47.1]
Q4-2025     444   48.5 [39.6,57.2]    5.1 [ 3.5, 7.2]   20.6 [12.3,29.8]   25.8 [18.9,33.8]
Q1-2026     565   42.1 [35.2,48.4]    8.0 [ 4.8,11.8]   21.4 [13.4,29.4]   28.6 [22.2,36.2]
Q2-2026     665   44.2 [37.7,51.6]    7.4 [ 5.0,10.2]   22.4 [15.4,31.3]   25.9 [19.8,33.4]

=== community ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      68   75.1 [55.7,90.0]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.1]   24.9 [ 9.5,44.6]
Q4-2025     110   54.8 [41.3,69.8]    4.2 [ 1.1, 9.2]   24.5 [ 9.4,44.5]   16.4 [ 8.1,26.3]
Q1-2026     138   51.8 [37.4,65.4]    4.6 [ 1.5, 8.8]   26.2 [12.3,45.1]   17.4 [10.5,25.1]
Q2-2026     146   56.3 [38.6,73.0]    4.9 [ 1.8, 9.1]   26.8 [13.0,43.7]   11.9 [ 7.7,17.5]

=== public ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     174   77.1 [67.0,84.6]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   22.9 [14.9,32.8]
Q4-2025     271   59.8 [52.9,66.3]    3.7 [ 2.2, 5.5]   19.9 [14.0,26.7]   16.6 [13.1,22.1]
Q1-2026     305   53.6 [47.3,59.0]    3.5 [ 2.4, 4.9]   27.7 [21.0,33.9]   15.3 [11.6,20.3]
Q2-2026     343   52.3 [46.3,58.5]    2.9 [ 2.1, 4.0]   28.0 [21.3,34.4]   16.7 [12.5,21.4]

```

## Two-sided bound (weak-prefix indeterminates)
```
headline ai_involved: two-sided bound (CW)
period       upper (reported)    lower (strict C)  delta pp
Q1-2024                 0.00%               0.00%     0.00
Q4-2025                 2.98%               2.98%     0.01
Q1-2026                10.30%              10.29%     0.01
Q2-2026                16.85%              16.74%     0.11

```

## Productivity decomposition (authors vs output/author)
```
balanced repo panel: 396 repos (pooled)
period        PRs  authors PRs/auth merged/auth klines/auth
Q1-2024     63447    10915     5.81        4.42        1.63
Q4-2025     81621    13850     5.89        4.20        2.03
Q1-2026    101828    18802     5.42        3.43        1.92
Q2-2026    118362    23087     5.13        2.97        1.82

```

## Persistent-author productivity (same person, same repo)
```
persistent same-repo authors (active Q1-2024 AND Q2-2026): 1411
  PRs/quarter            2024 mean  18.92 median  7.0 | 2026 mean  22.31 median  7.0
  merged/quarter         2024 mean  14.96 median  5.0 | 2026 mean  16.28 median  4.0
  AI-using in 2026       n=  434  merged/q 22.68->30.88 (1.36x)  klines/q 9.11->22.46 (2.46x)
  non-AI in 2026         n=  977  merged/q 11.52->9.80 (0.85x)  klines/q 4.33->5.67 (1.31x)
  (adopter selection caveat: AI-users were already ~2x heavier contributors in 2024; descriptive, not causal)

```

## Core-contributor merged LOC (CW)
```
period    repos  CW merged kLOC / core author
Q1-2024     251                          6.45
Q4-2025     469                         10.04
Q1-2026     532                         10.71
Q2-2026     581                         19.08

```

## Core-contributor merged LOC split by AI involvement (CW, 95% CI)
```
core-contributor merged (w8) kLOC split by AI involvement (CW, bootstrap 95% CI; floors: undetected AI counts as nonAI)
AI-user columns are per AI-USING core author and sum to their total; noAI-author LOC never enters them
period    repos AI-user repos      noAI-author kLOC    AI-user AI-PR kLOC  AI-user nonAI-PR kLOC
Q1-2024     251             0    6.45 [ 4.66, 8.63]         (no AI users)          (no AI users)
Q4-2025     463            83    6.75 [ 5.46, 8.28]    4.11 [ 1.41, 8.70]    33.85 [ 9.71,77.52]
Q1-2026     512           318    6.41 [ 4.92, 8.51]    4.16 [ 2.97, 5.63]    17.57 [12.51,23.53]
Q2-2026     519           440    5.90 [ 4.82, 7.06]    9.68 [ 5.55,15.13]    20.99 [14.68,27.73]

```

## Figure A1: Merged LOC per core author by adoption cohort (pooled, 95% CI on total)
```
merged (w8) kLOC per CORE author by fixed adoption cohort (pooled author-level means over quarter-active members; bootstrap 95% CI on total)
  fleet: fleet operators: >=300 merged PRs in some quarter (assigned before the AI-timing cohorts)
  early: early adopters: first PR with AI evidence by end of 2026-02
  medium: middle adopters: first AI evidence 2026-03..2026-04
  late: late adopters: first AI evidence 2026-05 or later
  never: non-adopters: no PR with AI evidence in the study period
Q2-2026 w8-deflated for May/June PRs; undetected AI counts as nonAI (floors)

period   cohort   authors  AI kLOC nonAI kLOC total kLOC          95% CI  median
Q1-2024  fleet         11     0.00      41.14      41.14   [19.88, 65.38]   34.68
Q1-2024  early        188     0.00      11.89      11.89   [ 8.44, 16.07]    2.15
Q1-2024  medium       136     0.00       9.23       9.23   [ 5.74, 13.69]    2.29
Q1-2024  late          99     0.00       8.73       8.73   [ 4.32, 14.49]    1.35
Q1-2024  never        999     0.00       3.76       3.76   [ 3.21,  4.35]    0.48
Q4-2025  fleet         21    10.72     106.35     117.07   [68.39,174.73]   68.18
Q4-2025  early        502     1.31      15.50      16.81   [14.31, 19.70]    4.73
Q4-2025  medium       399     0.00       9.90       9.90   [ 8.01, 12.16]    2.74
Q4-2025  late         249     0.00       7.46       7.46   [ 5.50,  9.83]    1.41
Q4-2025  never       1816     0.00       5.53       5.53   [ 4.52,  6.90]    0.71
Q1-2026  fleet         32    32.98     123.67     156.64   [99.64,218.67]  106.36
Q1-2026  early        572     6.34      16.55      22.89   [19.90, 26.27]    8.45
Q1-2026  medium       564     1.15      11.14      12.30   [10.20, 14.78]    3.26
Q1-2026  late         303     0.00      10.31      10.31   [ 8.13, 12.68]    2.35
Q1-2026  never       1841     0.00       6.03       6.03   [ 5.21,  7.08]    0.89
Q2-2026  fleet         33   225.66     305.03     530.68   [224.53,1052.92]  202.28
Q2-2026  early        498     9.88      16.94      26.83   [22.37, 31.34]    7.79
Q2-2026  medium       605     6.27      15.31      21.59   [18.60, 24.86]    7.05
Q2-2026  late         517     3.92      11.31      15.23   [13.05, 17.55]    3.99
Q2-2026  never       1844     0.00       6.17       6.17   [ 5.44,  7.03]    0.87

```

## Merged LOC by approval channel
```
period    merged MLOC humanRev% botOnly% selfUnrev% otherUnrev%
Q1-2024          19.4     72.8%     0.8%      20.0%        6.1%
Q4-2025          47.8     70.9%     9.4%      15.4%        3.9%
Q1-2026          72.1     69.3%    11.5%      15.8%        3.3%
Q2-2026          34.6     63.1%    15.9%      16.5%        4.4%

```

## Figure 6: review mix of merged PRs/LOC, core vs external
```
review mix of MERGED PRs (mature-gated, pooled): PR share / LOC share per approval channel
humanRev = reviewer!=author human review; botOnly = AI/CI bot only; selfUnrev/otherUnrev = merged unreviewed
period   slice   merged        humanRev         botOnly       selfUnrev      otherUnrev
Q1-2024  ins      17729   68.2/ 62.5%    0.8/  1.0%   27.1/ 31.7%    3.8/  4.7%
Q1-2024  ext      32677   80.5/ 79.5%    0.3/  0.6%   11.2/ 12.8%    7.7/  7.1%
Q4-2025  ins      38672   71.0/ 65.6%    9.2/ 11.3%   17.0/ 19.8%    2.7/  3.2%
Q4-2025  ext      50050   83.8/ 75.6%    4.4/  7.7%    6.2/ 11.7%    4.7/  4.5%
Q1-2026  ins      50564   65.4/ 64.0%   10.8/ 12.4%   21.2/ 21.7%    2.6/  1.9%
Q1-2026  ext      63680   79.4/ 74.4%    6.6/ 10.3%    8.4/ 10.7%    5.3/  4.4%
Q2-2026  ins      23028   63.1/ 56.7%   12.9/ 17.6%   21.6/ 22.7%    2.5/  3.0%
Q2-2026  ext      29745   74.4/ 69.3%    8.0/ 14.3%   12.7/ 10.5%    4.9/  5.8%

```

## Attention per line (comments/kLOC primary, bot-clean)
```
attention per line — merged, human-reviewed PRs (pooled)
cohort             PRs     kLOC comments/kLOC window h/kLOC
Q1-2024 all      38703   14,127          3.98         220.9
Q1-2024 ins      12314    4,954          3.52         165.6
Q1-2024 ext      26389    9,173          4.22         250.8
Q4-2025 all      69628   33,833          2.68         192.7
Q4-2025 ins      27632   14,437          2.08         149.4
Q4-2025 ext      41996   19,396          3.12         224.9
Q1-2026 all      84120   49,977          2.04         155.6
Q1-2026 ins      33340   21,751          1.59         114.6
Q1-2026 ext      50780   28,226          2.38         187.2
Q2-2026 all      37068   21,817          1.88         162.5
Q2-2026 ins      14621    9,780          1.37         115.5
Q2-2026 ext      22447   12,037          2.30         200.7

comments/kLOC within FIXED size bands (composition-controlled)
band         Q1-2024    Q4-2025    Q1-2026    Q2-2026
<=10           39.73      33.24      29.02      25.23
11-100         19.56      15.38      12.92       9.38
101-1k          8.37       6.14       5.02       4.21
>1k             1.18       1.03       0.86       0.91

```

## PR fates at matched horizons (w8 primary, w26 sensitivity)
```
--- fates at w8 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        67013    76.4%     17.5%    6.1%
Q1-2024 ins        21879    83.0%     13.4%    3.6%
Q1-2024 ext        45134    73.2%     19.4%    7.3%
Q1-2024 nonAI      67013    76.4%     17.5%    6.1%
Q4-2025 all       122572    72.8%     17.7%    9.5%
Q4-2025 ins        47846    81.4%     13.3%    5.2%
Q4-2025 ext        74726    67.3%     20.4%   12.3%
Q4-2025 AI          3746    56.8%     30.0%   13.2%
Q4-2025 nonAI     118826    73.3%     17.3%    9.4%
Q1-2026 all       178951    64.4%     23.6%   12.0%
Q1-2026 ins        63795    79.8%     14.7%    5.4%
Q1-2026 ext       115156    55.8%     28.6%   15.7%
Q1-2026 AI         20737    57.6%     27.9%   14.5%
Q1-2026 nonAI     158214    65.2%     23.1%   11.7%
Q2-2026 all        92945    57.4%     26.7%   15.9%
Q2-2026 ins        29575    78.4%     16.1%    5.4%
Q2-2026 ext        63370    47.6%     31.6%   20.8%
Q2-2026 AI         15346    57.2%     27.3%   15.4%
Q2-2026 nonAI      77599    57.5%     26.6%   16.0%

--- fates at w26 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        67013    77.2%     20.0%    2.8%
Q1-2024 ins        21879    83.6%     15.1%    1.3%
Q1-2024 ext        45134    74.1%     22.4%    3.5%
Q1-2024 nonAI      67013    77.2%     20.0%    2.8%
Q4-2025 all       121699    73.8%     22.1%    4.1%
Q4-2025 ins        47515    82.1%     15.8%    2.0%
Q4-2025 ext        74184    68.5%     26.1%    5.4%
Q4-2025 AI          3707    58.2%     35.4%    6.5%
Q4-2025 nonAI     117992    74.3%     21.7%    4.0%


```

## Responsiveness to human asks (clean lane identified)
```
unit nonresponse: 13 selected PRs (0.3%) unretrievable at hydration (repos privatized/PRs disabled after the census) — excluded, HT weights unchanged
conditional responsiveness to HUMAN ASKS (changes-requested or inline comments)
CLEAN lane = no AI-reviewer activity (identified); mixed = descriptive; all-cause = companion only
HT inclusion-probability weighted (PPS sample -> population estimands): responded% is PR-weighted; LOC share% is the population post-ask LOC ratio
lane                     PRs responded% post-ask LOC share%
Q1-2024 CLEAN            489      81.5%               46.0%
Q1-2024 CLEAN+nonAI      489      81.5%               46.0%
Q1-2024 all-cause        959      34.5%               56.7%
Q4-2025 CLEAN            309      83.1%               40.3%
Q4-2025 CLEAN+nonAI      302      83.6%               41.4%
Q4-2025 mixed            214      93.6%               77.1%
Q4-2025 all-cause       1086      56.8%               59.1%
Q1-2026 CLEAN            252      79.3%               61.1%
Q1-2026 CLEAN+AI          28      92.4%               41.8%
Q1-2026 CLEAN+nonAI      224      78.5%               62.0%
Q1-2026 mixed            246      84.4%               70.3%
Q1-2026 all-cause       1101      26.2%               48.3%
Q2-2026 CLEAN            242      74.5%               62.8%
Q2-2026 CLEAN+AI          49      93.3%               70.7%
Q2-2026 CLEAN+nonAI      193      71.6%               59.5%
Q2-2026 mixed            232      93.4%               41.2%
Q2-2026 all-cause       1020      36.2%               32.3%

```

## Adoption event-study (merged kLOC w8 + submitted kLOC in event time)
```
alignable adopters (core, clean pre-period): 1692
outcome A = MERGED kLOC (w8); months after 2026-04 (w8-immature at AS_OF) excluded. outcome B = SUBMITTED kLOC; full window.

=== outcome A: MERGED kLOC (w8) ===

ALL alignable adopters (unbalanced event panel)
event month  authors mean kLOC/mo  median
t-4             1452         2.76    0.00
t-3             1588         2.67    0.00
t-2             1636         3.15    0.00
t-1             1470         4.39    0.14
t+0             1173         9.54    1.92
t+1              845         8.62    1.31
t+2              516         8.75    1.02
t+3              240         7.85    0.90
t+4              104         7.25    0.40

BALANCED cohort (observed at every offset in [-2..+2]; post-t0 offsets past 2026-04 excluded)
event month  authors mean kLOC/mo  median
t-4              933         3.32    0.00
t-3             1069         2.97    0.01
t-2             1117         3.12    0.03
t-1             1117         4.35    0.19
t+0             1117         9.47    1.92
t+1              789         8.69    1.38
t+2              460         8.57    1.14
t+3              184         7.15    1.14
t+4               48         6.72    0.08

FULLY-MATURE balanced cohort (t0 <= 2026-02: every offset in [-2..+2] w8-mature)
event month  authors mean kLOC/mo  median
t-4              276         5.75    0.07
t-3              412         3.88    0.09
t-2              460         4.18    0.14
t-1              460         4.94    0.44
t+0              460         9.62    2.16
t+1              460         8.03    1.26
t+2              460         8.57    1.14
t+3              184         7.15    1.14
t+4               48         6.72    0.08

=== outcome B: SUBMITTED kLOC (all PRs created in the month; no censoring, full window through 2026-06) ===

ALL alignable adopters (unbalanced event panel)
event month  authors mean kLOC/mo  median
t-4             1452         3.71    0.00
t-3             1588         3.86    0.01
t-2             1636         4.58    0.07
t-1             1692         5.93    0.30
t+0             1692        13.90    4.13
t+1             1470        14.15    2.33
t+2             1173        16.90    1.82
t+3              845        13.84    1.91
t+4              516        11.12    1.16

BALANCED cohort (observed at every offset in [-2..+2])
event month  authors mean kLOC/mo  median
t-4              933         4.40    0.03
t-3             1069         4.37    0.05
t-2             1117         4.59    0.13
t-1             1117         6.06    0.41
t+0             1117        14.75    4.44
t+1             1117        15.42    2.63
t+2             1117        17.08    1.87
t+3              789        13.79    1.96
t+4              460        10.80    1.03

t0 <= 2026-02 cohort (same authors as fully-mature merged panel)
event month  authors mean kLOC/mo  median
t-4              276         7.23    0.20
t-3              412         5.39    0.28
t-2              460         6.16    0.26
t-1              460         7.17    0.69
t+0              460        15.49    4.79
t+1              460        12.98    2.75
t+2              460        12.66    2.34
t+3              460        11.70    2.39
t+4              460        10.80    1.03

```

