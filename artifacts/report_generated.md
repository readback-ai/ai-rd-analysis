# GENERATED quarterly report — scripts/report.py

> Q1-2024 columns are a detector-validity check and review-practice baseline,
> NOT an AI-usage estimate: the detectable channels (trailers, agent accounts,
> branch conventions) did not exist yet, while autocomplete-era assistance was
> already widespread and is invisible to every layer. All rates are floors
> (one quantified exception: the two-sided bound section).

## Contributor-weighted metrics
```
period   weighting        repos           ai_code       ai_involved            merged       rejected_w8          limbo_w8      human_review         ai_review  other_bot_review         no_review           insider       self_merged         m_hum_rev          m_ai_rev          m_no_rev
Q1-2024  equal-weight       465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   77.3 [75.3,79.3]   14.4 [13.1,15.8]    8.3 [ 7.1, 9.6]   52.0 [48.9,54.8]    0.4 [ 0.1, 0.9]    0.9 [ 0.4, 1.4]   47.2 [44.3,50.2]   34.1 [31.3,37.0]   55.5 [52.7,58.4]   61.8 [58.2,65.2]    0.5 [ 0.0, 1.1]   37.4 [34.2,40.7]
Q1-2024  contrib-weight     465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   75.6 [69.5,80.9]   16.6 [12.5,22.6]    7.9 [ 5.9,10.1]   58.7 [51.8,64.9]    0.7 [ 0.0, 2.0]    0.9 [ 0.4, 1.5]   40.3 [34.4,47.6]   30.0 [25.4,34.9]   53.2 [47.7,58.9]   69.2 [60.8,76.6]    0.7 [ 0.0, 2.1]   29.9 [22.8,38.3]
Q4-2025  equal-weight       825    3.3 [ 2.6, 4.1]    4.6 [ 3.8, 5.4]   71.4 [69.7,73.1]   16.3 [15.2,17.5]   12.3 [11.1,13.4]   50.2 [48.1,52.3]   14.3 [12.7,16.1]    3.8 [ 2.7, 4.9]   42.4 [40.2,44.7]   35.9 [33.7,38.2]   54.8 [52.5,56.9]   63.9 [61.4,66.4]   15.4 [13.6,17.3]   30.2 [27.8,32.7]
Q4-2025  contrib-weight     825    2.1 [ 1.6, 2.6]    3.0 [ 2.4, 3.7]   72.0 [68.0,75.1]   17.8 [15.5,21.1]   10.2 [ 8.7,11.7]   61.0 [57.1,64.7]   24.4 [17.9,31.3]    3.3 [ 2.2, 4.7]   30.8 [26.6,35.5]   34.4 [30.3,38.5]   52.2 [46.6,58.1]   74.4 [69.3,79.2]   26.0 [19.2,33.5]   20.3 [15.7,25.8]
Q1-2026  equal-weight      1009   12.0 [10.9,13.0]   13.6 [12.5,14.7]   68.1 [66.5,69.7]   18.1 [17.1,19.1]   13.8 [12.7,15.0]   43.2 [41.2,45.2]   15.9 [14.4,17.6]    3.7 [ 2.8, 4.7]   48.4 [46.2,50.5]   34.7 [32.7,36.7]   53.0 [50.9,54.9]   57.7 [55.2,60.1]   17.5 [15.7,19.3]   35.6 [33.1,38.0]
Q1-2026  contrib-weight    1009    8.7 [ 7.5,10.0]   10.3 [ 8.9,11.7]   66.9 [63.1,70.5]   21.3 [18.6,24.5]   11.8 [10.4,13.4]   55.7 [52.1,58.7]   28.3 [22.3,34.4]    4.2 [ 2.9, 5.9]   32.6 [29.3,36.8]   32.5 [28.9,36.2]   52.4 [47.4,57.3]   71.5 [66.9,75.8]   29.9 [23.1,36.9]   21.3 [17.6,25.9]
WARN Q2-2026: 1 qualifying repos lack contributor weights (default 1.0) — e.g. ['sgl-project/ci-data']
Q2-2026  equal-weight      1154   15.8 [14.6,16.9]   18.7 [17.4,19.9]   67.3 [65.4,69.1]   17.2 [16.1,18.3]   15.6 [14.0,17.1]   41.7 [39.5,43.8]   16.4 [14.7,18.2]    4.6 [ 3.5, 5.8]   48.9 [46.7,51.1]   34.1 [32.2,36.0]   52.0 [49.9,54.3]   57.8 [55.1,60.4]   18.4 [16.6,20.5]   34.6 [32.4,37.2]
Q2-2026  contrib-weight    1154   13.8 [12.0,15.5]   16.9 [14.9,18.7]   64.3 [60.6,67.9]   21.3 [19.1,23.9]   14.4 [12.4,16.8]   54.7 [50.8,58.8]   28.0 [22.6,34.2]    5.8 [ 4.0, 7.9]   32.7 [29.1,36.7]   30.8 [26.9,34.3]   51.4 [46.0,56.8]   72.6 [67.8,76.8]   30.6 [24.2,37.0]   19.2 [15.9,23.4]

```

## Figure 2: Traceable AI usage over time (CW, 95% CI)
```
Figure 2: Traceable AI usage over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule; LOC capped 20k/PR; all values are floors
period    repos  AI% of submitted PRs    AI% of merged PRs   AI-PR% of subm LOC  AI-PR% of merged LOC
Q1-2024     465      0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]      0.0% [ 0.0, 0.0]
Q4-2025     825      3.0% [ 2.4, 3.7]     2.2% [ 1.6, 2.9]     4.3% [ 3.4, 5.4]      2.7% [ 1.9, 3.6]
Q1-2026    1009     10.3% [ 8.9,11.7]     8.8% [ 7.5,10.3]    13.6% [11.7,15.4]     11.1% [ 9.3,12.9]
Q2-2026    1154     16.9% [14.9,18.8]    13.6% [11.6,15.8]    22.4% [19.7,25.0]     17.0% [14.4,19.7]

```

## Figure 3: Merged LOC per core contributor over time (CW, 95% CI)
```
Figure 3: Submitted and merged LOC per core contributor over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule (Q2 provisional); core = insider PR authors; repos with >=2 insider authors
period    repos    CW submitted kLOC/author  x base     CW merged kLOC/author  x base
Q1-2024     251          9.56 [ 6.72,12.82]   1.00x        6.45 [ 4.67, 8.63]   1.00x
Q4-2025     469         14.00 [ 9.39,21.18]   1.46x       10.04 [ 6.49,15.75]   1.56x
Q1-2026     532         16.28 [12.65,20.40]   1.70x       10.71 [ 8.41,13.59]   1.66x
Q2-2026     581         26.90 [19.45,37.27]   2.81x       19.08 [13.30,27.12]   2.96x

```

## Layered decomposition (pooled)
```
period        PRs A marker% B agent% C branch%  union%
Q1-2024     72290     0.00%    0.00%     0.00%   0.00%
Q4-2025    134088     2.62%    0.97%     0.26%   3.85%
Q1-2026    197860     9.65%    1.21%     0.99%  11.84%
Q2-2026    288234    13.20%    0.43%     3.48%  17.11%

```

## Slices: involvement
```

=== repo-scoped ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     147    0.0 [ 0.0, 0.0]   61.5 [46.5,73.3]    0.5 [ 0.0, 1.7]   80.9 [76.2,84.1]
Q4-2025     178    3.7 [ 2.3, 5.5]   60.1 [50.1,67.2]   22.6 [12.7,33.3]   72.5 [67.5,75.5]
Q1-2026     196   10.5 [ 7.5,13.8]   55.0 [45.9,62.6]   29.6 [19.8,40.1]   65.9 [62.0,69.3]
Q2-2026     210   13.7 [10.0,17.8]   54.8 [47.6,61.4]   26.6 [18.0,35.1]   65.1 [60.5,69.4]

=== AI-heavy ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      77    0.0 [ 0.0, 0.0]   51.0 [38.2,63.6]    0.0 [ 0.0, 0.0]   86.0 [83.1,88.7]
Q4-2025     119    5.4 [ 2.4,11.1]   51.2 [44.1,57.4]   11.0 [ 4.9,21.4]   80.3 [75.0,83.0]
Q1-2026     144   10.7 [ 6.0,18.4]   49.0 [39.3,55.5]   11.5 [ 6.0,21.1]   78.9 [70.0,84.0]
Q2-2026     162   12.4 [ 7.1,20.6]   57.2 [37.8,71.1]   17.5 [ 8.3,32.1]   74.7 [69.1,77.9]

=== AI-majority ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     241    0.0 [ 0.0, 0.0]   59.2 [51.6,66.3]    0.9 [ 0.0, 2.8]   72.0 [63.0,79.6]
Q4-2025     528    2.3 [ 1.9, 2.8]   63.3 [57.8,67.4]   27.6 [19.0,36.5]   70.1 [64.5,74.2]
Q1-2026     669   10.2 [ 9.1,11.4]   57.1 [52.2,60.7]   31.3 [23.7,38.5]   64.7 [60.2,68.8]
Q2-2026     782   18.4 [16.8,20.3]   55.6 [51.4,59.4]   31.6 [24.2,39.4]   62.0 [57.2,67.0]

=== private ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     223    0.0 [ 0.0, 0.0]   55.6 [46.2,62.7]    1.5 [ 0.0, 4.3]   83.1 [81.1,84.8]
Q4-2025     444    4.4 [ 3.4, 5.7]   57.1 [50.4,63.5]   23.1 [15.4,31.1]   74.0 [69.1,77.6]
Q1-2026     566   14.8 [13.0,16.7]   49.2 [42.9,54.6]   26.5 [19.4,33.1]   66.8 [62.6,70.8]
Q2-2026     665   21.2 [19.5,23.1]   49.4 [43.9,54.9]   27.7 [20.7,34.6]   64.7 [59.8,69.3]

=== community ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      68    0.0 [ 0.0, 0.0]   63.1 [47.2,76.1]    0.1 [ 0.0, 0.4]   67.9 [48.5,82.7]
Q4-2025     110    2.0 [ 1.1, 3.5]   66.3 [59.6,73.1]   28.0 [11.1,47.3]   70.2 [60.5,77.8]
Q1-2026     138    6.3 [ 4.1, 8.9]   62.3 [57.8,67.4]   31.1 [15.1,48.9]   66.5 [55.2,76.5]
Q2-2026     146   12.3 [ 7.3,17.7]   63.8 [54.9,71.3]   31.8 [16.3,52.2]   62.1 [52.0,71.2]

=== public ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     174    0.0 [ 0.0, 0.0]   59.0 [48.4,68.5]    0.0 [ 0.0, 0.0]   71.0 [61.4,80.7]
Q4-2025     271    1.4 [ 0.9, 1.8]   62.0 [57.6,65.6]   22.3 [16.0,28.2]   70.3 [67.1,73.2]
Q1-2026     305    6.1 [ 5.2, 7.3]   60.7 [56.7,64.5]   28.4 [22.4,34.0]   67.4 [64.2,70.3]
Q2-2026     343   13.2 [11.1,15.4]   58.9 [55.0,62.8]   27.8 [21.8,33.9]   65.8 [62.7,68.4]

```

## Slices: self-merge
```

=== repo-scoped ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     147   51.6 [42.1,61.7]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   67.8 [48.8,83.2]
Q4-2025     178   48.1 [41.9,55.1]    2.0 [ 0.7, 3.8]    4.7 [ 2.3, 8.2]   50.7 [26.5,94.2]   66.1 [51.6,78.9]
Q1-2026     196   46.7 [41.0,53.8]    8.4 [ 4.8,12.2]   11.2 [ 7.6,16.5]   75.7 [50.0,92.4]   66.7 [51.9,78.6]
Q2-2026     210   44.1 [38.9,49.7]   15.2 [ 9.0,21.6]   14.5 [ 9.4,20.9]   79.6 [64.6,91.5]   70.7 [59.0,79.6]

=== AI-heavy ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      77   52.6 [44.9,59.5]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   51.9 [37.3,69.3]
Q4-2025     119   67.6 [49.7,79.9]    5.3 [ 2.1,10.9]    4.1 [ 1.5, 9.4]   45.0 [23.3,67.7]   51.7 [42.0,61.9]
Q1-2026     144   63.4 [46.5,74.4]   12.1 [ 5.9,23.7]    6.8 [ 3.3,13.1]   47.4 [29.1,66.5]   51.4 [40.4,58.7]
Q2-2026     162   65.2 [48.7,75.9]   10.6 [ 5.1,21.4]    6.4 [ 3.1,12.6]   40.6 [24.6,54.1]   64.1 [38.4,77.7]

=== AI-majority ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     241   53.8 [47.2,62.1]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   63.5 [50.0,75.2]
Q4-2025     528   50.7 [44.6,56.8]    1.0 [ 0.6, 1.6]    1.8 [ 1.0, 3.0]   64.0 [46.1,77.1]   72.4 [65.9,78.0]
Q1-2026     669   51.8 [45.6,57.6]    8.2 [ 7.0, 9.9]    8.5 [ 6.6,10.8]   68.5 [55.3,79.0]   68.2 [61.3,74.8]
Q2-2026     782   49.5 [43.4,55.3]   15.6 [13.0,18.8]   13.0 [10.9,15.1]   71.4 [56.4,83.7]   69.0 [62.1,76.5]

=== private ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     223   60.2 [53.2,67.8]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   56.0 [45.0,65.4]
Q4-2025     444   57.8 [51.7,63.8]    3.5 [ 2.3, 5.1]    4.1 [ 2.7, 5.8]   53.4 [33.1,69.0]   65.6 [57.4,72.7]
Q1-2026     566   58.1 [53.3,63.0]   13.5 [11.3,16.4]   12.7 [10.1,15.8]   62.0 [48.6,74.6]   60.2 [51.0,68.2]
Q2-2026     665   55.8 [49.6,61.4]   18.6 [16.0,21.5]   15.6 [12.8,18.2]   66.6 [53.1,78.2]   61.7 [53.4,70.1]

=== community ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      68   43.6 [36.7,52.6]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   66.2 [38.8,86.8]
Q4-2025     110   45.1 [30.8,61.3]    0.7 [ 0.2, 1.7]    1.4 [ 0.3, 3.6]   83.5 [39.0,94.6]   68.8 [56.6,81.0]
Q1-2026     138   44.3 [31.4,57.7]    5.1 [ 3.0, 7.4]    4.2 [ 2.5, 7.4]   69.3 [49.7,89.6]   66.4 [54.1,78.0]
Q2-2026     146   42.7 [28.3,59.3]   11.0 [ 5.6,18.0]    8.5 [ 4.9,12.6]   71.3 [42.7,94.2]   74.6 [59.7,86.2]

=== public ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     174   52.3 [43.5,60.9]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   75.6 [62.9,83.6]
Q4-2025     271   52.5 [47.9,57.7]    0.3 [ 0.1, 0.5]    1.7 [ 0.8, 2.6]   55.6 [ 0.0,100.0]   72.5 [65.7,78.6]
Q1-2026     305   51.3 [46.8,55.8]    4.1 [ 3.0, 5.3]    6.5 [ 4.7, 8.5]   85.4 [74.1,93.0]   74.9 [68.2,81.1]
Q2-2026     343   50.7 [46.3,55.3]   12.3 [ 8.8,16.0]   10.7 [ 8.1,13.4]   82.6 [73.7,89.5]   74.1 [66.5,80.0]

```

## Balanced-panel sensitivity
```
balanced panel: 332 repos qualify in all 4 quarters
period        panel ai_involved         cross-section
Q1-2024      0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]
Q4-2025      3.0 [ 2.1, 4.0]    3.0 [ 2.3, 3.6]
Q1-2026      9.9 [ 8.2,11.7]   10.3 [ 8.9,11.7]
Q2-2026     15.6 [13.2,17.9]   16.9 [14.8,18.8]

```

## Reviewer profile of merged PRs (unmerged = implicitly rejected)
```

=== repo-scoped ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     147   70.2 [54.0,84.0]    0.3 [ 0.0, 1.2]    0.1 [ 0.0, 0.3]   29.4 [16.4,45.7]
Q4-2025     178   55.4 [43.5,67.0]    3.3 [ 1.9, 5.5]   19.1 [ 9.4,30.7]   22.2 [13.2,34.2]
Q1-2026     196   49.9 [39.5,60.8]    6.7 [ 2.3,13.8]   23.9 [15.8,33.2]   19.5 [13.8,27.1]
Q2-2026     210   51.9 [42.8,60.0]    4.3 [ 1.9, 7.6]   24.6 [16.1,31.9]   19.2 [13.1,28.7]

=== AI-heavy ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      77   57.0 [43.3,71.2]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   43.0 [28.9,58.3]
Q4-2025     119   51.8 [44.0,59.7]    4.9 [ 1.8,10.2]    6.5 [ 2.4,13.7]   36.8 [24.9,43.5]
Q1-2026     144   51.4 [38.5,59.1]    5.4 [ 2.4,10.4]    6.1 [ 2.7,12.0]   37.2 [30.6,45.1]
Q2-2026     162   60.1 [37.2,75.7]   10.9 [ 3.6,22.8]    6.5 [ 3.2,12.4]   22.5 [15.2,36.2]

=== AI-majority ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     241   71.2 [60.3,79.8]    0.6 [ 0.0, 2.2]    0.3 [ 0.0, 0.8]   27.8 [19.1,38.2]
Q4-2025     528   52.9 [45.1,61.7]    4.7 [ 2.9, 7.0]   25.3 [17.6,32.6]   17.1 [12.8,23.8]
Q1-2026     669   46.3 [39.9,53.1]    5.9 [ 3.7, 8.6]   28.0 [20.5,36.5]   19.9 [15.5,25.6]
Q2-2026     782   47.0 [40.6,54.1]    4.8 [ 3.4, 6.5]   28.9 [21.0,37.3]   19.3 [14.5,25.1]

=== private ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     223   61.9 [52.4,70.1]    1.0 [ 0.0, 3.3]    0.4 [ 0.0, 1.0]   36.7 [28.2,46.4]
Q4-2025     444   48.5 [41.6,57.2]    5.1 [ 3.4, 7.2]   20.6 [11.7,30.6]   25.8 [18.8,34.9]
Q1-2026     566   42.1 [35.3,48.1]    8.0 [ 4.8,12.0]   21.4 [14.2,30.2]   28.6 [22.0,36.2]
Q2-2026     665   44.2 [38.0,51.2]    7.4 [ 5.0,10.0]   22.4 [15.5,30.6]   26.0 [20.4,33.4]

=== community ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      68   75.1 [57.0,90.8]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.1]   24.9 [ 9.7,47.5]
Q4-2025     110   54.9 [41.4,70.9]    4.2 [ 1.1, 9.1]   24.4 [10.1,44.4]   16.4 [ 7.8,25.9]
Q1-2026     138   51.8 [39.0,65.8]    4.6 [ 1.6, 9.3]   26.2 [12.3,42.7]   17.4 [10.8,24.5]
Q2-2026     146   56.3 [36.4,72.2]    4.9 [ 2.0, 8.9]   26.8 [12.4,45.2]   11.9 [ 7.6,17.9]

=== public ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     174   77.1 [67.9,85.2]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   22.9 [15.0,33.0]
Q4-2025     271   59.8 [52.7,66.4]    3.7 [ 2.5, 5.4]   19.9 [14.0,26.8]   16.6 [12.7,21.0]
Q1-2026     305   53.7 [47.7,59.8]    3.5 [ 2.4, 4.7]   27.6 [20.8,33.1]   15.3 [11.7,19.7]
Q2-2026     343   52.3 [46.4,58.1]    2.9 [ 2.0, 3.9]   28.0 [21.6,34.3]   16.7 [12.3,21.3]

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
Q4-2025     763     3.0%    2.9 [ 2.3, 3.6]    3.2 [ 2.6, 4.0]    2.5 [ 1.9, 3.1]     5.4%   6.2%
Q1-2026     924    10.3%   10.3 [ 8.9,11.8]   11.4 [ 9.9,13.0]   10.4 [ 9.1,11.9]     6.5%   7.5%
Q2-2026    1040    16.9%   17.0 [15.0,19.0]   18.4 [16.4,20.3]   17.9 [15.6,19.8]     7.7%   8.3%

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
Q1-2024     251             0    6.45 [ 4.57, 8.57]         (no AI users)          (no AI users)
Q4-2025     463            83    6.75 [ 5.33, 8.22]    4.11 [ 1.47, 8.39]    33.85 [ 9.63,77.88]
Q1-2026     512           318    6.41 [ 4.92, 8.50]    4.16 [ 2.95, 5.65]    17.57 [12.47,23.38]
Q2-2026     519           440    5.90 [ 4.89, 7.10]    9.68 [ 5.52,15.69]    20.99 [15.01,27.67]

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
Q1-2024  fleet         11     0.00      41.14      41.14   [19.21, 65.43]   34.68
Q1-2024  early        188     0.00      11.89      11.89   [ 8.41, 15.90]    2.15
Q1-2024  medium       136     0.00       9.23       9.23   [ 5.75, 13.40]    2.29
Q1-2024  late          99     0.00       8.73       8.73   [ 4.45, 14.36]    1.35
Q1-2024  never        999     0.00       3.76       3.76   [ 3.22,  4.32]    0.48
Q4-2025  fleet         21    10.72     106.35     117.07   [71.57,177.82]   68.18
Q4-2025  early        502     1.31      15.50      16.81   [14.25, 19.69]    4.73
Q4-2025  medium       399     0.00       9.90       9.90   [ 7.98, 11.95]    2.74
Q4-2025  late         249     0.00       7.46       7.46   [ 5.57,  9.67]    1.41
Q4-2025  never       1816     0.00       5.53       5.53   [ 4.54,  6.85]    0.71
Q1-2026  fleet         32    32.98     123.67     156.64   [100.85,218.55]  106.36
Q1-2026  early        572     6.34      16.55      22.89   [19.87, 26.40]    8.45
Q1-2026  medium       564     1.15      11.14      12.30   [10.26, 14.76]    3.26
Q1-2026  late         303     0.00      10.31      10.31   [ 8.17, 12.76]    2.35
Q1-2026  never       1841     0.00       6.03       6.03   [ 5.21,  7.02]    0.89
Q2-2026  fleet         33   225.66     305.03     530.68   [221.94,1018.98]  202.28
Q2-2026  early        498     9.88      16.94      26.83   [22.70, 31.16]    7.79
Q2-2026  medium       605     6.27      15.31      21.59   [18.54, 24.87]    7.05
Q2-2026  late         517     3.92      11.31      15.23   [13.03, 17.51]    3.99
Q2-2026  never       1844     0.00       6.17       6.17   [ 5.45,  7.00]    0.87

```

## Merged LOC by approval channel
```
period    merged MLOC humanRev% botOnly% selfUnrev% otherUnrev%
Q1-2024          19.0     72.8%     0.7%      20.3%        6.1%
Q4-2025          47.6     71.0%     9.4%      15.4%        3.9%
Q1-2026          71.6     69.5%    11.3%      15.9%        3.2%
Q2-2026          34.3     63.0%    15.9%      16.6%        4.4%

```

## Figure 6: review mix of merged PRs/LOC, core vs external
```
review mix of MERGED PRs (mature-gated, pooled, FLEET-OPERATOR authors excluded): PR share / LOC share per approval channel
humanRev = reviewer!=author human review; botOnly = AI/CI bot only; selfUnrev/otherUnrev = merged unreviewed

--- sliced by author role ---
period   slice   merged        humanRev         botOnly       selfUnrev      otherUnrev
Q1-2024  ins      16037   70.3/ 63.2%    0.6/  0.9%   24.9/ 30.9%    4.1/  4.9%
Q1-2024  ext      32002   81.1/ 80.1%    0.3/  0.5%   10.5/ 12.3%    7.9/  7.1%
Q4-2025  ins      35190   74.8/ 69.5%    8.0/  9.3%   14.6/ 17.8%    2.6/  3.5%
Q4-2025  ext      48173   85.0/ 76.5%    4.2/  7.2%    5.2/ 11.2%    4.8/  4.6%
Q1-2026  ins      43764   71.8/ 69.2%    9.4/ 11.2%   16.3/ 17.7%    2.5/  2.0%
Q1-2026  ext      59096   83.1/ 78.1%    5.6/  9.1%    5.4/  8.0%    5.5/  4.6%
Q2-2026  ins      18769   69.2/ 62.4%   11.7/ 14.6%   16.4/ 19.5%    2.6/  3.5%
Q2-2026  ext      26109   82.6/ 75.5%    6.9/ 12.0%    5.2/  6.1%    5.3/  6.3%

--- sliced by PR AI involvement ---
period   slice   merged        humanRev         botOnly       selfUnrev      otherUnrev
Q1-2024  nonai    48039   77.5/ 73.6%    0.4/  0.7%   15.3/ 19.5%    6.6/  6.2%
Q4-2025  ai        2807   73.2/ 65.2%    9.9/ 16.0%   11.2/ 14.8%    4.7/  3.7%
Q4-2025  nonai    81502   81.0/ 73.7%    5.6/  7.8%    9.0/ 14.0%    3.9/  4.2%
Q1-2026  ai       11993   69.1/ 65.4%   10.7/ 15.4%   14.3/ 12.8%    5.6/  6.0%
Q1-2026  nonai    92805   79.5/ 75.1%    6.8/  9.3%    9.3/ 12.2%    4.2/  3.3%
Q2-2026  ai        7916   70.6/ 64.2%   11.3/ 16.0%   13.3/ 13.6%    4.7/  6.1%
Q2-2026  nonai    37618   78.5/ 70.5%    8.4/ 12.5%    9.0/ 12.3%    4.1/  4.7%

```

## Attention per line (comments/kLOC primary, bot-clean)
```
attention per line — merged, human-reviewed PRs (pooled)
cohort             PRs     kLOC comments/kLOC window h/kLOC
Q1-2024 all      38703   14,127          3.98         220.9
Q1-2024 ins      12314    4,954          3.52         165.6
Q1-2024 ext      26389    9,173          4.22         250.8
Q4-2025 all      69627   33,833          2.68         192.7
Q4-2025 ins      27632   14,437          2.08         149.4
Q4-2025 ext      41995   19,396          3.12         224.9
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

attention by PR AI involvement (mature merged human-reviewed PRs, pooled, fleet-operator authors excluded)
period   slice      PRs     kLOC  comments/kLOC  first-rev h/kLOC
Q1-2024  nonai    37165   13,603           4.09             103.9
Q4-2025  ai        2054    1,095           1.92              72.4
Q4-2025  nonai    65906   31,790           2.77              96.7
Q1-2026  ai        8276    5,564           1.78              76.8
Q1-2026  nonai    73706   42,750           2.15              80.7
Q2-2026  ai        5587    3,899           1.79              78.1
Q2-2026  nonai    29479   16,802           2.01              90.7

```

## PR fates at matched horizons (w8 primary, w26 sensitivity)
```
--- fates at w8 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        63587    75.5%     18.1%    6.4%
Q1-2024 ins        19649    81.6%     14.5%    3.9%
Q1-2024 ext        43937    72.8%     19.7%    7.5%
Q1-2024 nonAI      63586    75.5%     18.1%    6.4%
Q4-2025 all       117163    72.0%     18.2%    9.9%
Q4-2025 ins        43692    80.6%     13.8%    5.6%
Q4-2025 ext        72051    66.9%     20.6%   12.5%
Q4-2025 AI          4875    57.6%     31.1%   11.4%
Q4-2025 nonAI     112288    72.6%     17.6%    9.8%
Q1-2026 all       166872    62.8%     24.4%   12.8%
Q1-2026 ins        55389    79.1%     15.1%    5.9%
Q1-2026 ext       108788    54.5%     29.1%   16.4%
Q1-2026 AI         21194    56.6%     28.7%   14.7%
Q1-2026 nonAI     145678    63.7%     23.8%   12.5%
Q2-2026 all        83521    54.5%     28.0%   17.5%
Q2-2026 ins        24162    77.8%     16.0%    6.3%
Q2-2026 ext        58714    44.7%     33.0%   22.2%
Q2-2026 AI         14465    54.7%     28.8%   16.5%
Q2-2026 nonAI      69056    54.5%     27.8%   17.7%
suppressed (n < 20, too few PRs to carry a rate): Q1-2024 AI n=1
note: all = AI + nonAI exactly; all = ins + ext + agent-authored (a Bot has no human author association) — Q1-2024 1, Q4-2025 1420, Q1-2026 2695, Q2-2026 645

--- fates at w26 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        63587    76.4%     20.8%    2.9%
Q1-2024 ins        19649    82.3%     16.3%    1.4%
Q1-2024 ext        43937    73.8%     22.7%    3.5%
Q1-2024 nonAI      63586    76.4%     20.8%    2.9%
Q4-2025 all       116336    73.0%     22.7%    4.3%
Q4-2025 ins        43414    81.3%     16.5%    2.2%
Q4-2025 ext        71523    68.1%     26.3%    5.6%
Q4-2025 AI          4816    58.6%     35.8%    5.6%
Q4-2025 nonAI     111520    73.6%     22.2%    4.2%
suppressed (n < 20, too few PRs to carry a rate): Q1-2024 AI n=1
note: all = AI + nonAI exactly; all = ins + ext + agent-authored (a Bot has no human author association) — Q1-2024 1, Q4-2025 1399


```

## Responsiveness to human asks (clean lane identified)
```
unit nonresponse (eq): 5 selected PRs (0.1%) unretrievable at hydration (repos privatized/PRs disabled after the census) — excluded, weights unchanged
unit nonresponse (pps): 12 selected PRs (0.3%) unretrievable at hydration (repos privatized/PRs disabled after the census) — excluded, weights unchanged
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
Q2-2026 CLEAN            182      80.2%   245               58.5%
Q2-2026 CLEAN+AI          19        n/a    49               49.1%
Q2-2026 CLEAN+nonAI      163      79.8%   196               62.2%
Q2-2026 mixed            137      74.5%   224               58.7%
Q2-2026 all-cause       1196      35.7%  1016               39.7%

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
Q2-2026 CLEAN            177      80.8%   237               58.7%
Q2-2026 CLEAN+AI          18        n/a    46               47.7%
Q2-2026 CLEAN+nonAI      159      79.9%   191               62.9%
Q2-2026 mixed            130      74.6%   218               58.4%
Q2-2026 all-cause       1125      36.2%   970               39.6%

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

