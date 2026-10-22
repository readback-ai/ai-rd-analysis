# GENERATED quarterly report — scripts/report.py

> Q1-2024 columns are a detector-validity check and review-practice baseline,
> NOT an AI-usage estimate: the detectable channels (trailers, agent accounts,
> branch conventions) did not exist yet, while autocomplete-era assistance was
> already widespread and is invisible to every layer. All rates are floors
> (one quantified exception: the two-sided bound section).

## Contributor-weighted metrics
```
period   weighting        repos           ai_code       ai_involved            merged       rejected_w8          limbo_w8      human_review         ai_review  other_bot_review         no_review           insider       self_merged         m_hum_rev          m_ai_rev          m_no_rev
Q1-2024  equal-weight       465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   77.3 [75.4,79.2]   14.4 [13.0,15.8]    8.3 [ 7.1, 9.6]   52.0 [48.9,55.0]    0.4 [ 0.1, 0.9]    0.9 [ 0.4, 1.4]   47.2 [44.2,50.2]   34.0 [31.2,37.0]   55.5 [52.7,58.3]   61.8 [58.1,65.1]    0.5 [ 0.0, 1.2]   37.4 [34.0,40.6]
Q1-2024  contrib-weight     465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   75.6 [68.9,81.0]   16.6 [12.5,21.7]    7.9 [ 5.9,10.2]   58.7 [52.1,64.9]    0.7 [ 0.0, 2.0]    0.9 [ 0.4, 1.5]   40.3 [34.3,46.9]   30.0 [25.6,34.6]   53.2 [48.0,59.4]   69.2 [60.9,76.4]    0.7 [ 0.0, 2.0]   29.9 [22.7,38.2]
Q4-2025  equal-weight       825    3.3 [ 2.6, 4.1]    4.6 [ 3.7, 5.5]   71.4 [69.7,73.2]   16.3 [15.2,17.4]   12.3 [11.1,13.5]   50.2 [48.0,52.4]   14.3 [12.5,16.0]    3.8 [ 2.7, 4.9]   42.4 [40.1,44.7]   35.8 [33.6,38.1]   54.8 [52.5,56.9]   63.9 [61.3,66.3]   15.4 [13.5,17.4]   30.2 [27.7,32.8]
Q4-2025  contrib-weight     825    2.1 [ 1.6, 2.6]    3.0 [ 2.4, 3.7]   72.0 [68.3,75.1]   17.8 [15.5,20.9]   10.2 [ 8.8,11.6]   61.0 [56.8,64.5]   24.4 [17.6,31.6]    3.3 [ 2.2, 4.7]   30.8 [26.6,35.4]   34.4 [30.6,38.4]   52.2 [46.7,58.2]   74.4 [69.4,79.0]   26.0 [19.4,33.1]   20.3 [15.8,25.6]
Q1-2026  equal-weight      1009   12.0 [10.8,13.1]   13.6 [12.5,14.7]   68.1 [66.5,69.7]   18.1 [17.1,19.1]   13.8 [12.7,15.0]   43.2 [41.2,45.2]   15.9 [14.4,17.6]    3.7 [ 2.8, 4.6]   48.4 [46.3,50.4]   34.6 [32.6,36.7]   53.0 [51.0,54.9]   57.7 [55.2,60.1]   17.5 [15.7,19.2]   35.6 [33.1,37.9]
Q1-2026  contrib-weight    1009    8.7 [ 7.5,10.0]   10.3 [ 9.0,11.7]   66.9 [62.9,70.7]   21.3 [18.6,24.4]   11.8 [10.4,13.4]   55.7 [52.0,58.7]   28.3 [22.0,34.6]    4.2 [ 2.8, 5.8]   32.6 [29.2,36.6]   32.5 [28.8,36.1]   52.4 [47.6,57.4]   71.5 [67.1,75.6]   29.9 [23.5,36.5]   21.3 [17.6,25.6]
WARN Q2-2026: 1 qualifying repos lack contributor weights (default 1.0) — e.g. ['sgl-project/ci-data']
Q2-2026  equal-weight      1152   15.8 [14.6,17.0]   18.7 [17.4,19.9]   66.0 [64.3,67.6]   17.7 [16.8,18.7]   16.3 [15.0,17.5]   39.9 [38.0,41.7]   16.2 [14.7,17.8]    5.0 [ 4.0, 6.1]   49.9 [47.9,52.0]   33.6 [31.7,35.5]   54.3 [52.3,56.2]   55.9 [53.6,58.2]   17.9 [16.2,19.7]   35.9 [33.6,38.3]
Q2-2026  contrib-weight    1152   13.8 [12.0,15.4]   16.8 [14.8,18.7]   63.4 [60.0,66.8]   21.9 [19.9,24.2]   14.8 [12.8,16.7]   53.8 [50.2,57.6]   26.4 [21.7,31.0]    6.7 [ 5.0, 8.8]   33.5 [30.5,36.7]   30.7 [26.9,34.2]   53.2 [48.3,57.8]   72.3 [67.9,76.1]   28.9 [23.5,34.8]   19.7 [16.7,23.6]
2026-07  equal-weight       805   15.5 [14.1,17.0]   19.4 [17.9,21.0]   64.3 [61.9,66.7]   19.3 [17.5,21.1]   16.4 [14.4,18.3]   46.8 [44.2,49.5]   19.7 [17.4,22.2]    5.9 [ 4.4, 7.4]   41.5 [38.8,44.1]   32.5 [30.2,34.6]   49.7 [46.6,52.6]   67.2 [64.0,70.3]   21.9 [19.1,24.6]   24.2 [21.4,26.9]
2026-07  contrib-weight     805   15.0 [12.9,17.1]   19.2 [17.2,21.3]   60.3 [56.0,64.7]   22.8 [19.8,26.0]   16.9 [14.3,19.2]   55.5 [52.3,58.6]   30.5 [24.6,36.5]    7.9 [ 5.6,10.5]   29.8 [26.9,32.8]   30.1 [26.9,33.5]   49.7 [44.3,55.2]   77.2 [72.3,81.6]   32.4 [25.6,39.4]   15.1 [11.5,19.6]
2026-08  equal-weight       785   14.1 [12.8,15.5]   18.3 [16.8,19.9]                n/a                n/a                n/a                n/a                n/a                n/a                n/a   31.8 [29.5,34.0]                n/a                n/a                n/a                n/a
2026-08  contrib-weight     785   13.6 [11.7,15.6]   18.4 [16.3,20.6]                n/a                n/a                n/a                n/a                n/a                n/a                n/a   28.9 [25.8,32.2]                n/a                n/a                n/a                n/a

```

## Figure 2: Traceable AI usage over time (CW, 95% CI)
```
Figure 2: Traceable AI usage over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule; LOC capped 20k/PR; all values are floors
period    repos  AI% of submitted PRs    AI% of merged PRs   AI-PR% of subm LOC  AI-PR% of merged LOC
Q1-2024     465      0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]      0.0% [ 0.0, 0.0]
Q4-2025     825      3.0% [ 2.3, 3.7]     2.2% [ 1.6, 2.9]     4.3% [ 3.4, 5.4]      2.7% [ 1.9, 3.6]
Q1-2026    1009     10.3% [ 9.0,11.7]     8.8% [ 7.5,10.4]    13.6% [11.7,15.4]     11.1% [ 9.5,12.9]
Q2-2026    1152     16.8% [14.8,18.7]    16.4% [14.3,18.4]    22.5% [19.6,25.0]     20.6% [17.9,23.2]

```

## Figure 3: Merged LOC per core contributor over time (CW, 95% CI)
```
Figure 3: Submitted and merged LOC per core contributor over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule; core = insider PR authors; repos with >=2 insider authors
period    repos    CW submitted kLOC/author  x base     CW merged kLOC/author  x base
Q1-2024     251          9.56 [ 6.72,12.82]   1.00x        6.45 [ 4.67, 8.63]   1.00x
Q4-2025     469         14.00 [ 9.39,21.18]   1.46x       10.04 [ 6.49,15.75]   1.56x
Q1-2026     531         16.28 [12.94,20.61]   1.70x       10.71 [ 8.37,13.54]   1.66x
Q2-2026     577         26.65 [18.85,37.71]   2.79x       19.01 [13.29,27.34]   2.95x

```

## Layered decomposition (pooled)
```
period        PRs A marker% B agent% C branch%  union%
Q1-2024     72290     0.00%    0.00%     0.00%   0.00%
Q4-2025    134088     2.62%    0.97%     0.26%   3.85%
Q1-2026    197860     9.65%    1.21%     0.99%  11.84%
Q2-2026    285088    13.33%    0.44%     3.47%  17.24%

```

## Slices: involvement
```

=== repo-scoped ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     147    0.0 [ 0.0, 0.0]   61.5 [49.1,73.8]    0.5 [ 0.0, 1.7]   80.9 [75.5,84.1]
Q4-2025     178    3.7 [ 2.3, 5.5]   60.1 [50.1,67.2]   22.6 [12.7,33.3]   72.5 [67.5,75.5]
Q1-2026     196   10.5 [ 7.4,14.2]   55.0 [46.0,62.6]   29.6 [18.7,39.2]   65.9 [62.0,69.3]
Q2-2026     210   13.7 [10.3,17.7]   54.0 [46.9,59.7]   25.8 [17.5,33.9]   63.9 [59.2,67.9]

=== AI-heavy ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      77    0.0 [ 0.0, 0.0]   51.0 [38.2,63.6]    0.0 [ 0.0, 0.0]   86.0 [83.1,88.7]
Q4-2025     119    5.4 [ 2.6,10.8]   51.2 [44.0,57.3]   11.0 [ 5.0,21.4]   80.3 [74.9,83.2]
Q1-2026     144   10.7 [ 5.8,18.4]   49.0 [38.4,54.9]   11.5 [ 6.1,21.0]   78.9 [70.8,83.5]
Q2-2026     162   12.3 [ 6.7,20.4]   55.0 [36.7,69.1]   18.5 [ 9.0,34.4]   73.5 [67.6,76.7]

=== AI-majority ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     241    0.0 [ 0.0, 0.0]   59.2 [49.1,66.3]    0.9 [ 0.0, 3.0]   72.0 [62.3,79.4]
Q4-2025     528    2.3 [ 1.8, 2.8]   63.3 [58.0,67.5]   27.6 [18.7,35.7]   70.1 [65.1,73.9]
Q1-2026     669   10.2 [ 9.0,11.6]   57.1 [52.5,60.9]   31.3 [24.0,38.9]   64.7 [60.2,68.8]
Q2-2026     780   18.4 [16.6,20.3]   53.6 [50.6,56.6]   28.0 [22.6,33.9]   61.3 [56.7,65.7]

=== private ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     223    0.0 [ 0.0, 0.0]   55.6 [46.2,62.7]    1.5 [ 0.0, 4.3]   83.1 [81.1,84.8]
Q4-2025     444    4.4 [ 3.4, 5.6]   57.1 [50.6,63.2]   23.1 [15.3,32.2]   74.0 [69.9,77.6]
Q1-2026     566   14.8 [13.2,16.7]   49.2 [42.9,54.4]   26.5 [20.0,32.9]   66.8 [62.5,70.7]
Q2-2026     663   21.2 [19.3,23.0]   47.7 [43.3,52.3]   25.9 [20.5,32.0]   63.8 [59.0,68.2]

=== community ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      68    0.0 [ 0.0, 0.0]   63.1 [47.2,76.1]    0.1 [ 0.0, 0.4]   67.9 [48.5,82.7]
Q4-2025     110    2.0 [ 1.1, 3.5]   66.3 [59.6,73.1]   28.0 [11.1,47.3]   70.2 [60.5,77.8]
Q1-2026     138    6.3 [ 4.1, 8.9]   62.3 [57.8,67.4]   31.1 [15.1,48.9]   66.5 [55.2,76.5]
Q2-2026     146   12.3 [ 7.8,17.2]   62.7 [54.7,71.6]   27.5 [15.4,40.3]   61.8 [51.7,70.8]

=== public ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     174    0.0 [ 0.0, 0.0]   59.0 [49.0,68.7]    0.0 [ 0.0, 0.0]   71.0 [61.3,79.8]
Q4-2025     271    1.4 [ 0.9, 1.8]   62.0 [57.4,65.8]   22.3 [16.3,28.4]   70.3 [66.9,73.1]
Q1-2026     305    6.1 [ 5.0, 7.1]   60.7 [56.5,64.6]   28.4 [22.7,34.4]   67.4 [64.4,70.5]
Q2-2026     343   13.2 [10.9,15.8]   56.3 [52.2,59.9]   26.2 [20.8,31.3]   64.4 [61.1,67.3]

```

## Slices: self-merge
```

=== repo-scoped ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     147   51.6 [42.9,61.5]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   67.8 [48.4,82.7]
Q4-2025     178   48.1 [41.9,55.1]    2.0 [ 0.7, 3.8]    4.7 [ 2.3, 8.2]   50.7 [26.5,94.2]   66.1 [51.6,78.9]
Q1-2026     196   46.7 [40.4,53.2]    8.4 [ 5.0,12.1]   11.2 [ 7.6,16.5]   75.7 [50.0,92.4]   66.7 [53.1,78.1]
Q2-2026     210   45.8 [41.1,50.3]   14.7 [ 9.0,20.4]   14.0 [ 9.4,18.4]   74.6 [59.1,84.5]   69.4 [59.0,77.0]

=== AI-heavy ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      77   52.6 [44.9,59.5]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   51.9 [37.3,69.3]
Q4-2025     119   67.6 [49.7,79.9]    5.3 [ 2.1,10.9]    4.1 [ 1.5, 9.4]   45.0 [23.3,67.7]   51.7 [42.0,61.9]
Q1-2026     144   63.4 [46.9,73.9]   12.1 [ 5.9,23.7]    6.8 [ 3.3,13.3]   47.4 [29.1,66.5]   51.4 [40.4,58.7]
Q2-2026     162   65.5 [49.5,76.3]   12.9 [ 6.8,23.8]    7.5 [ 3.9,13.2]   36.1 [21.9,50.2]   61.6 [37.6,76.1]

=== AI-majority ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     241   53.8 [46.7,61.1]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   63.5 [50.0,75.2]
Q4-2025     528   50.7 [44.7,56.9]    1.0 [ 0.7, 1.6]    1.8 [ 1.0, 3.0]   64.0 [46.1,77.1]   72.4 [66.1,77.5]
Q1-2026     669   51.8 [45.8,56.9]    8.2 [ 7.0, 9.7]    8.5 [ 6.6,10.9]   68.5 [55.3,79.0]   68.2 [61.0,74.3]
Q2-2026     780   51.6 [46.7,56.7]   19.9 [17.4,22.6]   15.1 [13.3,16.6]   70.1 [61.5,78.4]   67.1 [58.5,74.0]

=== private ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     223   60.2 [53.2,67.8]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   56.0 [45.0,65.4]
Q4-2025     444   57.8 [51.7,63.8]    3.5 [ 2.3, 5.1]    4.1 [ 2.7, 5.8]   53.4 [33.1,69.0]   65.6 [57.4,72.7]
Q1-2026     566   58.1 [52.5,63.0]   13.5 [11.2,16.2]   12.7 [10.0,15.6]   62.0 [48.6,74.6]   60.2 [52.1,68.4]
Q2-2026     663   57.4 [52.2,62.9]   23.7 [20.9,26.5]   17.6 [15.6,19.8]   63.3 [53.3,72.4]   60.6 [51.6,67.9]

=== community ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      68   43.6 [36.7,52.6]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   66.2 [38.8,86.8]
Q4-2025     110   45.1 [30.8,61.3]    0.7 [ 0.2, 1.7]    1.4 [ 0.3, 3.6]   83.5 [39.0,94.6]   68.8 [56.6,81.0]
Q1-2026     138   44.3 [31.4,57.7]    5.1 [ 3.0, 7.4]    4.2 [ 2.5, 7.4]   69.3 [49.7,89.6]   66.4 [54.1,78.0]
Q2-2026     146   44.4 [30.9,61.1]   13.2 [ 7.2,21.1]    9.9 [ 6.3,14.4]   64.8 [45.6,80.9]   72.3 [56.5,83.7]

=== public ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     174   52.3 [44.3,61.0]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   75.6 [64.5,83.4]
Q4-2025     271   52.5 [48.1,57.3]    0.3 [ 0.1, 0.5]    1.7 [ 0.8, 2.6]   55.6 [ 0.0,100.0]   72.5 [65.1,79.6]
Q1-2026     305   51.3 [46.5,56.2]    4.1 [ 3.0, 5.5]    6.5 [ 4.7, 8.5]   85.4 [74.1,93.0]   74.9 [67.0,80.8]
Q2-2026     343   52.2 [48.2,56.5]   12.8 [10.2,16.2]   11.7 [ 9.6,14.1]   80.8 [72.2,87.7]   71.6 [65.0,77.5]

```

## Balanced-panel sensitivity
```
balanced panel: 332 repos qualify in all 4 quarters
period        panel ai_involved         cross-section
Q1-2024      0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]
Q4-2025      3.0 [ 2.1, 4.0]    3.0 [ 2.4, 3.7]
Q1-2026      9.9 [ 8.2,11.7]   10.3 [ 9.0,11.8]
Q2-2026     15.6 [13.2,18.0]   16.8 [14.9,18.7]

```

## Reviewer profile of merged PRs (unmerged = implicitly rejected)
```

=== repo-scoped ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     147   70.2 [53.9,83.7]    0.3 [ 0.0, 1.2]    0.1 [ 0.0, 0.3]   29.4 [15.9,45.0]
Q4-2025     178   55.4 [43.5,67.0]    3.3 [ 1.9, 5.5]   19.1 [ 9.4,30.7]   22.2 [13.2,34.2]
Q1-2026     196   49.9 [38.8,61.0]    6.7 [ 2.2,14.3]   23.9 [15.1,33.5]   19.5 [13.1,27.6]
Q2-2026     210   52.5 [44.2,61.5]    4.5 [ 2.4, 6.9]   23.7 [15.4,32.1]   19.3 [14.0,25.3]

=== AI-heavy ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      77   57.0 [43.3,71.2]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   43.0 [28.9,58.3]
Q4-2025     119   51.8 [44.0,59.7]    4.9 [ 1.8,10.2]    6.5 [ 2.4,13.7]   36.8 [24.9,43.5]
Q1-2026     144   51.4 [39.6,58.7]    5.4 [ 2.6,10.3]    6.1 [ 2.8,11.9]   37.2 [30.1,44.6]
Q2-2026     162   56.7 [33.7,73.6]   11.4 [ 5.3,21.3]    8.0 [ 3.9,14.7]   24.0 [16.1,36.7]

=== AI-majority ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     241   71.2 [59.9,80.2]    0.6 [ 0.0, 2.2]    0.3 [ 0.0, 0.8]   27.8 [19.2,37.6]
Q4-2025     528   52.9 [45.0,60.8]    4.7 [ 3.0, 6.9]   25.3 [16.9,33.1]   17.1 [12.4,23.2]
Q1-2026     669   46.3 [39.9,53.5]    5.9 [ 3.8, 8.2]   28.0 [20.4,35.7]   19.9 [15.7,25.9]
Q2-2026     780   48.5 [43.2,53.6]    4.8 [ 3.6, 6.2]   25.3 [19.5,31.5]   21.4 [17.3,26.4]

=== private ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     223   61.9 [52.4,70.1]    1.0 [ 0.0, 3.3]    0.4 [ 0.0, 1.0]   36.7 [28.2,46.4]
Q4-2025     444   48.5 [41.6,57.2]    5.1 [ 3.4, 7.2]   20.6 [11.7,30.6]   25.8 [18.8,34.9]
Q1-2026     566   42.1 [36.0,49.0]    8.0 [ 4.9,12.1]   21.4 [14.2,31.7]   28.6 [22.6,37.1]
Q2-2026     663   44.1 [39.1,50.3]    7.1 [ 4.9, 9.6]   20.8 [13.9,28.3]   27.9 [22.2,33.7]

=== community ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      68   75.1 [57.0,90.8]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.1]   24.9 [ 9.7,47.5]
Q4-2025     110   54.9 [41.4,70.9]    4.2 [ 1.1, 9.1]   24.4 [10.1,44.4]   16.4 [ 7.8,25.9]
Q1-2026     138   51.8 [39.0,65.8]    4.6 [ 1.6, 9.3]   26.2 [12.3,42.7]   17.4 [10.8,24.5]
Q2-2026     146   59.8 [45.0,73.1]    4.9 [ 2.2, 8.7]   22.4 [12.8,35.6]   12.9 [ 9.1,18.5]

=== public ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     174   77.1 [67.1,85.2]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   22.9 [15.4,33.8]
Q4-2025     271   59.8 [53.3,66.5]    3.7 [ 2.4, 5.3]   19.9 [14.4,27.1]   16.6 [12.7,21.0]
Q1-2026     305   53.7 [48.0,60.1]    3.5 [ 2.4, 4.8]   27.6 [21.0,34.1]   15.3 [11.9,19.9]
Q2-2026     343   51.6 [46.7,56.5]    3.7 [ 2.5, 5.0]   26.5 [21.3,32.5]   18.2 [14.1,23.0]

```

## Two-sided bound (weak-prefix indeterminates)
```
headline ai_involved: two-sided bound (CW)
period       upper (reported)    lower (strict C)  delta pp
Q1-2024                 0.00%               0.00%     0.00
Q4-2025                 2.98%               2.98%     0.01
Q1-2026                10.30%              10.29%     0.01
Q2-2026                16.83%              16.72%     0.11

```

## Involvement sensitivity to bot-authored PRs in the denominator
```
involvement sensitivity to BOT-AUTHORED PRs in the denominator
published   = profile 'all', as reported (every bot PR in the denominator)
no-dilution = non-AI bot PRs dropped, layer-B coding agents KEPT — the clean counterfactual for denominator dilution
no-bots     = profile 'pr' (ALL bot authors dropped, INCLUDING agents): removes AI signal too, so it can move the OTHER way
the three columns share ONE repo set (all three defined) so the deltas are within-repo; pub(all) is the published column over every qualifying repo, for comparison
shares are contributor-weighted like the rates, not raw PR counts: dilbot% = non-AI bot authors (what no-dilution drops), bot% = all bot authors (what no-bots drops)
period    repos pub(all)           published         no-dilution             no-bots  dilbot%   bot%
Q1-2024     439     0.0%    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]     4.1%   4.1%
Q4-2025     763     3.0%    2.9 [ 2.3, 3.6]    3.2 [ 2.6, 4.0]    2.5 [ 1.9, 3.2]     5.4%   6.2%
Q1-2026     924    10.3%   10.3 [ 8.9,11.9]   11.4 [ 9.9,13.1]   10.4 [ 8.9,12.0]     6.5%   7.5%
Q2-2026    1037    16.8%   17.0 [14.9,19.0]   18.4 [16.2,20.3]   17.9 [15.8,19.8]     7.7%   8.2%

```

## Productivity decomposition (authors vs output/author)
```
balanced repo panel: 396 repos (pooled)
period        PRs  authors PRs/auth merged/auth klines/auth
Q1-2024     63447    10915     5.81        4.42        1.63
Q4-2025     81621    13850     5.89        4.20        2.03
Q1-2026    101828    18802     5.42        3.43        1.92
Q2-2026    118009    23004     5.13        3.02        1.88

```

## Persistent-author productivity (same person, same repo)
```
persistent same-repo authors (active Q1-2024 AND Q2-2026): 1409
  PRs/quarter            2024 mean  18.91 median  7.0 | 2026 mean  22.27 median  7.0
  merged/quarter         2024 mean  14.95 median  5.0 | 2026 mean  16.38 median  4.0
  AI-using in 2026       n=  436  merged/q 22.55->31.03 (1.38x)  klines/q 9.08->22.83 (2.51x)
  non-AI in 2026         n=  973  merged/q 11.54->9.81 (0.85x)  klines/q 4.32->5.79 (1.34x)
  (adopter selection caveat: AI-users were already ~2x heavier contributors in 2024; descriptive, not causal)

```

## Core-contributor merged LOC (CW)
```
period    repos  CW merged kLOC / core author
Q1-2024     251                          6.45
Q4-2025     469                         10.04
Q1-2026     531                         10.71
Q2-2026     577                         19.01

```

## Core-contributor merged LOC split by AI involvement (CW, 95% CI)
```
core-contributor merged (w8) kLOC split by AI involvement (CW, bootstrap 95% CI; floors: undetected AI counts as nonAI)
AI-user columns are per AI-USING core author and sum to their total; noAI-author LOC never enters them
period    repos AI-user repos      noAI-author kLOC    AI-user AI-PR kLOC  AI-user nonAI-PR kLOC
Q1-2024     251             0    6.45 [ 4.57, 8.57]         (no AI users)          (no AI users)
Q4-2025     463            83    6.75 [ 5.33, 8.22]    4.11 [ 1.47, 8.39]    33.85 [ 9.63,77.88]
Q1-2026     511           318    6.41 [ 4.91, 8.56]    4.16 [ 2.95, 5.65]    17.57 [12.47,23.38]
Q2-2026     513           430    5.87 [ 4.87, 6.96]    9.86 [ 5.74,15.50]    21.03 [15.16,28.06]

```

## Figure A1: Merged LOC per core author by adoption cohort (pooled, 95% CI on total)
```
merged (w8) kLOC per CORE author by fixed adoption cohort (pooled author-level means over quarter-active members; bootstrap 95% CI on total)
  fleet: fleet operators: >=300 merged PRs in some quarter (assigned before the AI-timing cohorts)
  early: early adopters: first PR with AI evidence by end of 2026-02
  medium: middle adopters: first AI evidence 2026-03..2026-04
  late: late adopters: first AI evidence 2026-05 or later
  never: non-adopters: no PR with AI evidence in the study period
undetected AI counts as nonAI (floors)

period   cohort   authors  AI kLOC nonAI kLOC total kLOC          95% CI  median
Q1-2024  fleet         11     0.00      41.14      41.14   [19.21, 65.43]   34.68
Q1-2024  early        189     0.00      11.88      11.88   [ 8.41, 16.23]    2.19
Q1-2024  medium       138     0.00       9.15       9.15   [ 5.55, 13.27]    2.29
Q1-2024  late         102     0.00       8.91       8.91   [ 4.72, 14.65]    1.54
Q1-2024  never       1003     0.00       3.74       3.74   [ 3.19,  4.33]    0.48
Q4-2025  fleet         21    10.72     106.35     117.07   [71.57,177.82]   68.18
Q4-2025  early        504     1.30      15.38      16.68   [14.18, 19.54]    4.73
Q4-2025  medium       404     0.00       9.74       9.74   [ 7.85, 11.93]    2.65
Q4-2025  late         260     0.00       6.82       6.82   [ 5.23,  8.55]    1.53
Q4-2025  never       1834     0.00       5.63       5.63   [ 4.66,  7.03]    0.71
Q1-2026  fleet         32    32.98     123.67     156.64   [100.61,218.26]  106.36
Q1-2026  early        574     6.31      16.63      22.93   [20.00, 26.31]    8.50
Q1-2026  medium       571     1.14      10.92      12.06   [ 9.95, 14.42]    3.21
Q1-2026  late         316     0.00      10.22      10.22   [ 8.14, 12.58]    2.42
Q1-2026  never       1864     0.00       6.05       6.05   [ 5.27,  7.05]    0.89
Q2-2026  fleet         33   225.72     305.51     531.23   [223.46,1021.74]  202.28
Q2-2026  early        499     9.99      16.70      26.69   [22.52, 31.01]    8.06
Q2-2026  medium       610     6.22      15.31      21.53   [18.46, 24.76]    7.23
Q2-2026  late         538     3.87      10.95      14.82   [12.80, 17.07]    4.22
Q2-2026  never       1879     0.00       6.16       6.16   [ 5.43,  6.95]    0.90

```

## Merged LOC by approval channel
```
period    merged MLOC humanRev% botOnly% selfUnrev% otherUnrev%
Q1-2024          19.0     72.8%     0.7%      20.3%        6.1%
Q4-2025          47.6     71.0%     9.4%      15.4%        3.9%
Q1-2026          71.6     69.5%    11.3%      15.9%        3.2%
Q2-2026         103.0     60.0%    15.0%      21.4%        3.6%

```

## Figure 6: review mix of merged PRs/LOC, core vs external
```
review mix of MERGED PRs (mature-gated, pooled, FLEET-OPERATOR authors excluded): PR share / LOC share per approval channel
humanRev = reviewer!=author human review; botOnly = AI/CI bot only; selfUnrev/otherUnrev = merged unreviewed

--- sliced by author role ---
period   slice   merged        humanRev         botOnly       selfUnrev      otherUnrev
Q1-2024  ins      16033   70.4/ 63.2%    0.6/  0.9%   24.9/ 30.9%    4.1/  4.9%
Q1-2024  ext      32006   81.1/ 80.1%    0.3/  0.5%   10.5/ 12.3%    7.9/  7.1%
Q4-2025  ins      35185   74.8/ 69.5%    8.0/  9.3%   14.6/ 17.8%    2.6/  3.5%
Q4-2025  ext      48178   85.0/ 76.5%    4.2/  7.2%    5.2/ 11.2%    4.8/  4.6%
Q1-2026  ins      43753   71.8/ 69.2%    9.4/ 11.2%   16.3/ 17.7%    2.5/  2.0%
Q1-2026  ext      59107   83.1/ 78.1%    5.6/  9.1%    5.4/  8.0%    5.5/  4.6%
Q2-2026  ins      50722   68.7/ 63.7%   13.3/ 16.1%   15.2/ 17.4%    2.7/  2.8%
Q2-2026  ext      70846   82.8/ 76.8%    6.8/  9.8%    4.9/  7.6%    5.5/  5.6%

--- sliced by PR AI involvement ---
period   slice   merged        humanRev         botOnly       selfUnrev      otherUnrev
Q1-2024  nonai    48039   77.5/ 73.6%    0.4/  0.7%   15.3/ 19.5%    6.6/  6.2%
Q4-2025  ai        2807   73.2/ 65.2%    9.9/ 16.0%   11.2/ 14.8%    4.7/  3.7%
Q4-2025  nonai    81502   81.0/ 73.7%    5.6/  7.8%    9.0/ 14.0%    3.9/  4.2%
Q1-2026  ai       11993   69.1/ 65.4%   10.7/ 15.4%   14.3/ 12.8%    5.6/  6.0%
Q1-2026  nonai    92805   79.5/ 75.1%    6.8/  9.3%    9.3/ 12.2%    4.2/  3.3%
Q2-2026  ai       23935   70.5/ 65.2%   12.3/ 13.9%   12.7/ 16.0%    4.4/  4.7%
Q2-2026  nonai    99117   78.5/ 72.3%    8.8/ 12.3%    8.2/ 11.0%    4.4/  4.4%

```

## Attention per line (comments/kLOC primary, bot-clean)
```
attention per line — merged, human-reviewed PRs (pooled)
cohort             PRs     kLOC comments/kLOC window h/kLOC
Q1-2024 all      38703   14,127          3.86         220.9
Q1-2024 ins      12312    4,954          3.41         165.6
Q1-2024 ext      26391    9,173          4.10         250.8
Q4-2025 all      69627   33,833          2.60         192.7
Q4-2025 ins      27627   14,436          2.03         149.4
Q4-2025 ext      42000   19,397          3.03         224.9
Q1-2026 all      84120   49,977          1.98         155.6
Q1-2026 ins      33330   21,749          1.55         114.6
Q1-2026 ext      50790   28,229          2.32         187.2
Q2-2026 all      99542   62,270          1.76         156.3
Q2-2026 ins      37941   26,758          1.41         111.1
Q2-2026 ext      61601   35,512          2.02         190.4

comments/kLOC within FIXED size bands (composition-controlled)
band         Q1-2024    Q4-2025    Q1-2026    Q2-2026
<=10           39.73      33.24      29.02      24.10
11-100         19.55      15.38      12.90       9.29
101-1k          8.18       6.05       4.96       3.97
>1k             1.09       0.96       0.81       0.85

attention by PR AI involvement (mature merged human-reviewed PRs, pooled, fleet-operator authors excluded)
period   slice      PRs     kLOC  comments/kLOC  first-rev h/kLOC
Q1-2024  nonai    37165   13,603           3.96             103.9
Q4-2025  ai        2054    1,095           1.91              72.4
Q4-2025  nonai    65906   31,790           2.69              96.7
Q1-2026  ai        8276    5,564           1.74              76.8
Q1-2026  nonai    73706   42,750           2.09              80.7
Q2-2026  ai       16856   12,776           1.55              77.4
Q2-2026  nonai    77745   46,436           1.89              87.2

```

## PR fates at matched horizons (w8 primary, w26 sensitivity)
```
--- fates at w8 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        63587    75.5%     18.1%    6.4%
Q1-2024 ins        19642    81.6%     14.5%    3.9%
Q1-2024 ext        43944    72.8%     19.7%    7.5%
Q1-2024 nonAI      63586    75.5%     18.1%    6.4%
Q4-2025 all       117163    72.0%     18.2%    9.9%
Q4-2025 ins        43687    80.6%     13.8%    5.6%
Q4-2025 ext        72056    66.9%     20.6%   12.5%
Q4-2025 AI          4875    57.6%     31.1%   11.4%
Q4-2025 nonAI     112288    72.6%     17.6%    9.8%
Q1-2026 all       166872    62.8%     24.4%   12.8%
Q1-2026 ins        55374    79.1%     15.1%    5.9%
Q1-2026 ext       108803    54.5%     29.1%   16.4%
Q1-2026 AI         21194    56.6%     28.7%   14.7%
Q1-2026 nonAI     145678    63.7%     23.8%   12.5%
Q2-2026 all       233171    52.8%     28.8%   18.4%
Q2-2026 ins        65409    77.7%     15.8%    6.6%
Q2-2026 ext       166188    42.8%     34.0%   23.2%
Q2-2026 AI         43368    55.2%     27.8%   17.0%
Q2-2026 nonAI     189803    52.2%     29.1%   18.7%
suppressed (n < 20, too few PRs to carry a rate): Q1-2024 AI n=1
note: all = AI + nonAI exactly; all = ins + ext + agent-authored (a Bot has no human author association) — Q1-2024 1, Q4-2025 1420, Q1-2026 2695, Q2-2026 1574

--- fates at w26 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        63587    76.4%     20.8%    2.9%
Q1-2024 ins        19642    82.3%     16.3%    1.4%
Q1-2024 ext        43944    73.7%     22.7%    3.5%
Q1-2024 nonAI      63586    76.4%     20.8%    2.9%
Q4-2025 all       117163    73.0%     22.7%    4.3%
Q4-2025 ins        43687    81.3%     16.5%    2.2%
Q4-2025 ext        72056    68.1%     26.3%    5.6%
Q4-2025 AI          4875    58.7%     35.8%    5.6%
Q4-2025 nonAI     112288    73.6%     22.2%    4.2%
Q1-2026 all       100704    67.5%     26.6%    5.9%
Q1-2026 ins        35299    80.2%     17.1%    2.7%
Q1-2026 ext        63646    60.4%     31.8%    7.8%
Q1-2026 AI         10989    61.1%     31.1%    7.9%
Q1-2026 nonAI      89715    68.3%     26.0%    5.7%
suppressed (n < 20, too few PRs to carry a rate): Q1-2024 AI n=1
note: all = AI + nonAI exactly; all = ins + ext + agent-authored (a Bot has no human author association) — Q1-2024 1, Q4-2025 1420, Q1-2026 1759


```

## Responsiveness to human asks (clean lane identified)
```
unit nonresponse (eq): 2 selected PRs (0.0%) unretrievable at hydration (repos privatized/PRs disabled after the census) — excluded, weights unchanged
unit nonresponse (pps): 5 selected PRs (0.1%) unretrievable at hydration (repos privatized/PRs disabled after the census) — excluded, weights unchanged
conditional responsiveness to HUMAN ASKS (changes-requested or inline comments)
CLEAN lane = no AI-reviewer activity (identified); mixed = descriptive; all-cause = companion only
two designs, one frame: responded% is the EQUAL-PROBABILITY sample share (uniform inclusion — unweighted); post-ask LOC share% is the HT-weighted ratio over the PPS-by-LOC sample (the estimand that design is efficient for)

--- all sampled PRs ---
lane                     PRs responded%   PRs post-ask LOC share%
Q1-2024 CLEAN            379      79.4%   512               44.0%
Q1-2024 CLEAN+nonAI      379      79.4%   512               44.0%
Q1-2024 all-cause       1200      35.4%   951               31.8%
Q4-2025 CLEAN            217      79.3%   296               69.1%
Q4-2025 CLEAN+nonAI      210      79.0%   282               71.3%
Q4-2025 mixed            148      77.7%   226               74.8%
Q4-2025 all-cause       1200      37.2%  1088               57.6%
Q1-2026 CLEAN            200      79.0%   244               50.6%
Q1-2026 CLEAN+AI          23      82.6%    23               81.5%
Q1-2026 CLEAN+nonAI      177      78.5%   221               46.3%
Q1-2026 mixed            141      80.1%   229               58.3%
Q1-2026 all-cause       1199      37.4%  1093               41.6%
Q2-2026 CLEAN            175      81.1%   251               51.3%
Q2-2026 CLEAN+AI          31      80.6%    55               43.2%
Q2-2026 CLEAN+nonAI      144      81.2%   196               53.4%
Q2-2026 mixed            147      87.8%   256               59.3%
Q2-2026 all-cause       1199      38.1%  1118               40.6%

--- FLEET-OPERATOR authors EXCLUDED (domain estimation, same weights) ---
lane                     PRs responded%   PRs post-ask LOC share%
Q1-2024 CLEAN            375      79.7%   505               43.9%
Q1-2024 CLEAN+nonAI      375      79.7%   505               43.9%
Q1-2024 all-cause       1164      36.3%   934               31.8%
Q4-2025 CLEAN            215      79.1%   289               69.4%
Q4-2025 CLEAN+nonAI      208      78.8%   275               71.6%
Q4-2025 mixed            145      77.2%   223               75.0%
Q4-2025 all-cause       1161      37.4%  1052               57.6%
Q1-2026 CLEAN            193      79.8%   235               51.0%
Q1-2026 CLEAN+AI          22      81.8%    21               85.9%
Q1-2026 CLEAN+nonAI      171      79.5%   214               46.4%
Q1-2026 mixed            140      80.0%   225               57.8%
Q1-2026 all-cause       1151      37.9%  1044               41.3%
Q2-2026 CLEAN            173      80.9%   243               50.9%
Q2-2026 CLEAN+AI          30      80.0%    52               42.8%
Q2-2026 CLEAN+nonAI      143      81.1%   191               52.9%
Q2-2026 mixed            146      87.7%   252               59.0%
Q2-2026 all-cause       1139      38.7%  1062               40.4%

```

## Adoption event-study (merged kLOC w8 + submitted kLOC in event time)
```
alignable adopters (core, clean pre-period): 1720
outcome A = MERGED kLOC (w8); months after 2026-06 (w8-immature at AS_OF) excluded. outcome B = SUBMITTED kLOC; full window.

=== outcome A: MERGED kLOC (w8) ===

ALL alignable adopters (unbalanced event panel)
event month  authors mean kLOC/mo  median
t-4             1481         2.72    0.00
t-3             1617         2.67    0.00
t-2             1665         3.06    0.00
t-1             1720         4.24    0.11
t+0             1720         8.80    1.80
t+1             1479         9.83    1.16
t+2             1180        12.89    0.87
t+3              849        10.08    0.69
t+4              517         6.90    0.36

BALANCED cohort (observed at every offset in [-2..+2]; post-t0 offsets past 2026-06 excluded)
event month  authors mean kLOC/mo  median
t-4              941         3.32    0.00
t-3             1077         2.92    0.01
t-2             1125         3.07    0.03
t-1             1125         4.34    0.19
t+0             1125         9.40    1.92
t+1             1125        10.69    1.22
t+2             1125        13.01    0.87
t+3              794        10.07    0.72
t+4              462         6.79    0.33

FULLY-MATURE balanced cohort (t0 <= 2026-04: every offset in [-2..+2] w8-mature)
event month  authors mean kLOC/mo  median
t-4              941         3.32    0.00
t-3             1077         2.92    0.01
t-2             1125         3.07    0.03
t-1             1125         4.34    0.19
t+0             1125         9.40    1.92
t+1             1125        10.69    1.22
t+2             1125        13.01    0.87
t+3              794        10.07    0.72
t+4              462         6.79    0.33

=== outcome B: SUBMITTED kLOC (all PRs created in the month; no censoring, full window through 2026-06) ===

ALL alignable adopters (unbalanced event panel)
event month  authors mean kLOC/mo  median
t-4             1481         3.66    0.00
t-3             1617         3.87    0.01
t-2             1665         4.46    0.07
t-1             1720         5.90    0.32
t+0             1720        13.66    4.10
t+1             1479        14.09    2.33
t+2             1180        16.85    1.89
t+3              849        13.59    1.76
t+4              517        11.19    1.15

BALANCED cohort (observed at every offset in [-2..+2])
event month  authors mean kLOC/mo  median
t-4              941         4.39    0.03
t-3             1077         4.31    0.05
t-2             1125         4.54    0.13
t-1             1125         6.04    0.41
t+0             1125        14.62    4.44
t+1             1125        15.36    2.63
t+2             1125        17.02    1.91
t+3              794        13.51    1.77
t+4              462        10.86    0.93

t0 <= 2026-04 cohort (same authors as fully-mature merged panel)
event month  authors mean kLOC/mo  median
t-4              941         4.39    0.03
t-3             1077         4.31    0.05
t-2             1125         4.54    0.13
t-1             1125         6.04    0.41
t+0             1125        14.62    4.44
t+1             1125        15.36    2.63
t+2             1125        17.02    1.91
t+3              794        13.51    1.77
t+4              462        10.86    0.93

```

## Code churn: within-org adoption contrast + calendar sensitivity
```
code churn, WITHIN-ORG ADOPTION CONTRAST on TRACEABLE adoption (an evidence floor): per org, deleted:added at its highest-adoption quarter vs its lowest, endpoints from Q4-2025..Q2-2026 only (the 2024 baseline's zero is by construction — a low endpoint there would contrast marker availability, not adoption); same-quarter-trimmed merge windows (capped sides; org-quarters qualify at >= 20 PRs)
external reference, NOT a replication target (different population): Faros's broad-industry report has this multiple at ~x9.6 (+861%)
orgs contrasted: 154 — attrition: 168 orgs with >= 1 qualifying era quarter, 155 with >= 2, minus 1 with zero adoption spread and 0 with an undefined/zero endpoint ratio; cross-quarter merges trimmed: 18322
geomean churn multiple (high/low adoption): 0.85 [0.75,0.96]  median 0.82  churn rose in 58/154 orgs (38%)
median adoption spread low->high: 16pp; multiples pool adds/dels across each org's population repos

code churn, CALENDAR-TREND SENSITIVITY (fixed quarters and PR-level arms — a different cut than the within-org adoption contrast above, and not comparable to any external figure). Same-quarter-trimmed merge windows. CW = contributor-weighted mean of per-repo deleted:added (capped sides, >= 5 PRs/repo, 95% CI over repos); pooled = raw ratio of totals; x2024 = pooled ratio vs the same-arm pooled 2024 baseline
period   arm     repos   CW del:add [95% CI]     PRs  pooled  capped  medPR  del>add   x2024
Q1-2024  all       408   0.563 [0.492,0.645]   48834   0.554   0.514  0.470    14.8%    1.00
Q1-2024  nonAI     408   0.563 [0.493,0.647]   48834   0.554   0.514  0.470    14.8%    1.00
Q4-2025  all       698   0.531 [0.461,0.622]   86458   0.637   0.453  0.390    15.2%    1.15
Q4-2025  AI         74   0.450 [0.298,0.635]    2916   0.391   0.390  0.190    12.1%     nan
Q4-2025  nonAI     681   0.535 [0.468,0.631]   83542   0.644   0.455  0.400    15.4%    1.16
Q1-2026  all       828   0.478 [0.433,0.528]  111756   0.384   0.404  0.286    13.7%    0.69
Q1-2026  AI        314   0.526 [0.364,0.801]   13042   0.420   0.399  0.200    12.2%     nan
Q1-2026  nonAI     759   0.475 [0.429,0.526]   98714   0.378   0.405  0.303    13.9%    0.68
Q2-2026  all       918   0.451 [0.394,0.520]  139947   0.373   0.341  0.171    11.0%    0.67
Q2-2026  AI        453   0.355 [0.312,0.401]   27860   0.287   0.337  0.144     9.8%     nan
Q2-2026  nonAI     819   0.447 [0.387,0.518]  112087   0.421   0.342  0.180    11.3%    0.76
2024 caption: detector-validity baseline and review-practice control, not an AI-usage estimate; AI arm has no 2024 baseline by construction (and the 2024 baseline is excluded from the adoption contrast above)

```

