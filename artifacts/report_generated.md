# GENERATED quarterly report — scripts/report.py

> Q1-2024 columns are a detector-validity check and review-practice baseline,
> NOT an AI-usage estimate: the detectable channels (trailers, agent accounts,
> branch conventions) did not exist yet, while autocomplete-era assistance was
> already widespread and is invisible to every layer. All rates are floors
> (one quantified exception: the two-sided bound section).

## Contributor-weighted metrics
```
period   weighting        repos           ai_code       ai_involved            merged       rejected_w8          limbo_w8      human_review   human_rev_other         ai_review  other_bot_review         no_review           insider       self_merged         m_hum_rev          m_ai_rev          m_no_rev
Q1-2024  equal-weight       465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   77.3 [75.2,79.2]   14.4 [13.1,15.8]    8.3 [ 7.1, 9.6]   53.8 [51.0,56.8]   53.3 [50.3,56.1]    0.4 [ 0.1, 1.0]    0.9 [ 0.4, 1.5]   45.4 [42.4,48.4]   34.1 [31.3,37.1]   55.3 [52.5,58.1]   61.8 [58.5,65.2]    0.5 [ 0.0, 1.2]   37.3 [34.0,40.6]
Q1-2024  contrib-weight     465    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   75.6 [69.5,81.4]   16.6 [12.4,21.9]    7.9 [ 5.9,10.2]   59.9 [53.1,65.6]   59.4 [52.7,65.7]    0.7 [ 0.0, 2.1]    0.9 [ 0.4, 1.5]   39.2 [33.3,46.1]   30.0 [25.6,34.9]   53.1 [47.9,59.2]   69.3 [61.2,76.6]    0.7 [ 0.0, 2.0]   29.8 [22.6,38.0]
Q4-2025  equal-weight       825    3.3 [ 2.6, 4.1]    4.5 [ 3.7, 5.4]   71.4 [69.7,73.1]   16.3 [15.2,17.4]   12.3 [11.1,13.5]   52.0 [49.8,54.2]   51.1 [48.9,53.2]   14.4 [12.7,16.2]    3.8 [ 2.8, 4.9]   41.3 [39.2,43.7]   35.9 [33.7,38.0]   54.5 [52.1,56.6]   63.9 [61.4,66.5]   15.5 [13.6,17.5]   30.1 [27.6,32.5]
Q4-2025  contrib-weight     825    2.0 [ 1.5, 2.5]    2.9 [ 2.3, 3.6]   72.0 [67.9,75.0]   17.8 [15.5,21.0]   10.2 [ 8.8,11.6]   63.3 [60.3,66.3]   62.0 [58.4,65.2]   24.5 [18.2,31.5]    3.4 [ 2.3, 4.6]   29.4 [25.8,33.1]   34.4 [30.4,38.5]   52.2 [46.8,58.1]   74.7 [70.1,79.2]   26.1 [19.3,33.6]   20.0 [15.8,24.5]
Q1-2026  equal-weight      1008   11.9 [10.8,13.0]   13.5 [12.5,14.8]   68.1 [66.5,69.6]   18.1 [17.1,19.1]   13.8 [12.7,15.0]   45.0 [43.0,46.9]   43.8 [41.9,45.8]   16.1 [14.5,17.7]    3.7 [ 2.8, 4.7]   47.5 [45.4,49.6]   34.7 [32.8,36.8]   53.0 [51.0,55.0]   57.8 [55.3,60.2]   17.5 [15.8,19.3]   35.5 [33.2,37.8]
Q1-2026  contrib-weight    1008    8.4 [ 7.3, 9.6]   10.0 [ 8.8,11.5]   66.7 [63.0,70.2]   21.4 [18.8,24.5]   11.9 [10.4,13.4]   58.0 [54.3,61.1]   56.5 [53.1,59.7]   28.4 [22.4,34.6]    4.3 [ 2.9, 5.9]   31.7 [28.1,35.7]   32.4 [28.6,36.2]   52.5 [47.2,57.8]   72.0 [67.1,76.0]   29.9 [23.2,36.9]   20.9 [17.3,25.0]
WARN Q2-2026: 1 qualifying repos lack contributor weights (default 1.0) — e.g. ['sgl-project/ci-data']
Q2-2026  equal-weight      1154   15.7 [14.5,16.9]   18.6 [17.4,19.8]   67.3 [65.5,69.1]   17.2 [16.1,18.4]   15.6 [14.1,17.1]   40.2 [38.3,41.9]   38.5 [36.7,40.4]   16.2 [14.6,17.8]    5.0 [ 4.0, 6.0]   50.6 [48.5,52.6]   34.1 [32.1,36.0]   55.4 [53.4,57.4]   55.3 [53.0,57.6]   17.9 [16.1,19.5]   36.4 [34.2,38.6]
Q2-2026  contrib-weight    1154   13.6 [11.9,15.3]   16.6 [14.7,18.5]   64.4 [60.7,68.1]   21.3 [19.1,23.9]   14.4 [12.2,16.5]   54.0 [50.5,57.7]   52.1 [48.3,55.9]   26.7 [22.2,31.5]    6.7 [ 4.9, 8.8]   34.3 [31.1,38.1]   30.9 [27.5,34.4]   53.7 [49.0,58.8]   72.1 [67.8,76.0]   29.1 [24.1,34.8]   19.8 [16.7,23.9]

```

## Figure 2: Traceable AI usage over time (CW, 95% CI)
```
Figure 2: Traceable AI usage over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule; LOC capped 20k/PR; all values are floors
period    repos  AI% of submitted PRs    AI% of merged PRs   AI-PR% of subm LOC  AI-PR% of merged LOC
Q1-2024     465      0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]     0.0% [ 0.0, 0.0]      0.0% [ 0.0, 0.0]
Q4-2025     825      2.9% [ 2.3, 3.6]     2.1% [ 1.6, 2.8]     4.2% [ 3.2, 5.3]      2.6% [ 1.9, 3.4]
Q1-2026    1008     10.0% [ 8.7,11.5]     8.7% [ 7.3,10.1]    13.4% [11.6,15.2]     10.9% [ 9.2,12.6]
Q2-2026    1154     16.6% [14.7,18.5]    15.9% [14.0,18.0]    22.1% [19.5,24.6]     20.1% [17.6,22.7]

```

## Figure 3: Merged LOC per core contributor over time (CW, 95% CI)
```
Figure 3: Merged LOC per core contributor over time
contributor-weighted repo means, bootstrap 95% CI; merged = w8 rule; core = insider PR authors; repos with >=2 insider authors
period    repos    CW merged kLOC/core author  x baseline
Q1-2024     251            6.45 [ 4.62, 8.68]       1.00x
Q4-2025     469           10.04 [ 6.49,15.99]       1.56x
Q1-2026     532           10.72 [ 8.45,13.54]       1.66x
Q2-2026     582           17.62 [12.01,26.23]       2.73x

```

## Layered decomposition (pooled)
```
period        PRs A marker% B agent% C branch%  union%
Q1-2024     72297     0.00%    0.00%     0.00%   0.00%
Q4-2025    134104     2.45%    0.97%     0.26%   3.68%
Q1-2026    197995     9.30%    1.21%     0.98%  11.49%
Q2-2026    288461    12.81%    0.43%     3.47%  16.71%

```

## Slices: involvement
```

=== repo-scoped ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     147    0.0 [ 0.0, 0.0]   62.2 [46.9,74.3]    0.5 [ 0.0, 1.8]   80.9 [76.6,84.0]
Q4-2025     178    3.2 [ 1.9, 4.8]   61.0 [51.3,68.2]   22.9 [13.3,35.4]   72.5 [68.2,75.8]
Q1-2026     196    9.7 [ 7.0,12.8]   55.7 [45.8,63.7]   29.8 [20.1,39.4]   65.9 [61.6,69.0]
Q2-2026     210   13.0 [ 9.4,16.8]   52.0 [44.7,57.5]   25.9 [17.3,35.1]   60.8 [56.6,64.8]

=== AI-heavy ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      77    0.0 [ 0.0, 0.0]   51.4 [38.7,67.1]    0.0 [ 0.0, 0.0]   86.0 [83.2,88.7]
Q4-2025     119    5.4 [ 2.3,10.5]   51.5 [44.9,57.8]   11.1 [ 5.0,23.0]   80.3 [75.3,83.4]
Q1-2026     144   10.7 [ 5.6,19.0]   52.0 [38.1,59.7]   11.7 [ 5.9,20.6]   77.9 [71.0,82.0]
Q2-2026     162   12.4 [ 6.8,20.5]   54.3 [36.3,67.6]   22.0 [15.6,33.0]   72.6 [65.9,76.3]

=== AI-majority ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     241    0.0 [ 0.0, 0.0]   59.9 [50.6,66.8]    0.9 [ 0.0, 3.0]   72.0 [63.8,79.9]
Q4-2025     528    2.3 [ 1.9, 2.9]   64.5 [60.4,68.5]   27.8 [18.8,37.2]   70.1 [65.0,74.1]
Q1-2026     668   10.0 [ 8.8,11.4]   57.6 [53.4,61.4]   31.4 [24.0,39.2]   64.7 [60.6,69.1]
Q2-2026     782   18.3 [16.7,20.0]   51.7 [48.2,54.8]   27.8 [22.6,33.7]   58.6 [53.7,62.7]

=== private ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     223    0.0 [ 0.0, 0.0]   56.2 [47.1,63.7]    1.5 [ 0.0, 4.2]   83.1 [81.2,84.9]
Q4-2025     444    4.2 [ 3.3, 5.4]   58.5 [53.4,64.0]   23.3 [15.4,33.0]   74.0 [69.1,77.4]
Q1-2026     565   14.3 [12.7,16.3]   49.6 [43.6,54.8]   26.7 [20.1,34.8]   66.8 [62.2,70.7]
Q2-2026     665   20.7 [18.9,22.5]   46.1 [41.2,50.0]   25.7 [19.6,31.5]   61.4 [57.2,65.7]

=== community ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024      68    0.0 [ 0.0, 0.0]   63.7 [47.6,77.3]    0.1 [ 0.0, 0.4]   67.8 [49.2,82.1]
Q4-2025     110    2.0 [ 1.1, 3.5]   66.8 [60.7,73.8]   28.2 [12.2,47.5]   70.2 [59.4,78.8]
Q1-2026     138    6.3 [ 4.0, 9.3]   64.2 [59.2,68.8]   31.2 [14.5,49.7]   66.0 [55.4,75.5]
Q2-2026     146   12.3 [ 7.6,17.7]   60.7 [52.4,69.0]   29.1 [19.1,40.4]   59.4 [49.6,69.4]

=== public ===
period    repos           ai_involved               hum_rev                ai_rev                merged
Q1-2024     174    0.0 [ 0.0, 0.0]   59.8 [49.6,69.7]    0.0 [ 0.0, 0.0]   71.0 [60.5,80.4]
Q4-2025     271    1.4 [ 0.9, 1.8]   62.9 [58.4,67.2]   22.6 [17.4,29.5]   70.3 [67.2,73.1]
Q1-2026     305    6.1 [ 5.1, 7.2]   61.2 [57.1,64.8]   28.6 [22.8,34.8]   67.4 [64.2,70.3]
Q2-2026     343   13.2 [11.1,15.3]   54.7 [51.0,58.3]   26.1 [20.9,31.6]   61.4 [58.5,64.9]

```

## Slices: self-merge
```

=== repo-scoped ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     147   51.6 [41.2,61.5]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   67.8 [49.3,82.8]
Q4-2025     178   48.1 [41.4,56.4]    1.4 [ 0.5, 2.6]    4.3 [ 2.0, 8.1]   46.5 [18.8,95.4]   66.1 [51.7,77.7]
Q1-2026     196   46.7 [40.4,53.4]    7.4 [ 4.0,11.2]   10.4 [ 6.7,14.8]   75.2 [51.0,92.3]   66.6 [52.9,78.7]
Q2-2026     210   46.2 [41.8,51.3]   14.0 [ 8.1,19.8]   12.8 [ 8.7,17.2]   72.7 [56.9,82.6]   68.5 [57.0,76.3]

=== AI-heavy ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      77   52.5 [45.4,59.0]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   51.9 [35.1,69.4]
Q4-2025     119   68.1 [48.9,80.1]    5.1 [ 2.0,11.8]    4.2 [ 1.6, 9.9]   46.3 [24.2,68.6]   51.9 [41.9,61.5]
Q1-2026     144   64.1 [48.3,74.6]   11.9 [ 6.0,22.8]    6.6 [ 3.2,13.4]   47.5 [28.3,64.3]   51.5 [38.0,59.8]
Q2-2026     162   66.0 [50.0,75.8]   12.9 [ 6.3,23.7]    7.6 [ 4.1,13.9]   37.7 [23.0,53.8]   62.2 [37.4,77.1]

=== AI-majority ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     241   53.7 [46.3,61.7]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   63.8 [52.2,76.1]
Q4-2025     528   50.6 [44.4,57.4]    1.0 [ 0.7, 1.6]    1.8 [ 1.0, 3.0]   64.0 [44.8,76.9]   72.6 [65.9,78.0]
Q1-2026     668   51.7 [46.0,57.0]    8.2 [ 7.0, 9.7]    8.4 [ 6.5,10.8]   68.6 [57.0,78.9]   68.3 [61.3,74.9]
Q2-2026     782   51.9 [46.1,57.1]   19.7 [16.8,22.8]   14.8 [13.1,16.6]   69.4 [61.7,77.7]   66.7 [58.5,74.0]

=== private ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     223   60.1 [52.7,67.3]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   56.4 [44.8,65.9]
Q4-2025     444   57.7 [51.3,64.5]    3.3 [ 2.2, 4.8]    4.0 [ 2.6, 5.6]   52.0 [33.2,65.6]   65.8 [58.4,73.0]
Q1-2026     565   58.0 [52.9,63.1]   13.1 [10.8,15.7]   12.3 [ 9.6,15.7]   61.9 [47.9,73.5]   60.5 [51.0,68.1]
Q2-2026     665   57.7 [52.3,62.9]   23.1 [20.3,26.3]   17.0 [15.0,19.4]   62.8 [52.2,71.7]   60.5 [51.5,68.0]

=== community ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024      68   43.5 [36.7,51.9]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   66.2 [41.6,86.2]
Q4-2025     110   44.9 [29.4,61.6]    0.6 [ 0.2, 1.3]    1.4 [ 0.3, 3.8]   90.2 [55.7,97.4]   68.9 [56.6,81.7]
Q1-2026     138   44.2 [31.4,59.8]    5.0 [ 2.9, 8.0]    4.2 [ 2.5, 7.4]   69.3 [47.2,87.2]   66.1 [53.4,79.0]
Q2-2026     146   44.5 [30.1,60.7]   13.4 [ 7.3,21.4]    9.6 [ 6.0,13.9]   63.9 [44.3,80.6]   71.2 [51.9,82.9]

=== public ===
period    repos           self_merged           ai_of_selfm          ai_of_otherm       humrev_selfm_ai      humrev_selfm_non
Q1-2024     174   52.3 [44.0,61.0]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]                   n/a   75.6 [64.2,83.7]
Q4-2025     271   52.8 [48.2,57.4]    0.3 [ 0.1, 0.5]    1.7 [ 0.9, 2.6]   55.6 [ 0.0,100.0]   72.5 [65.2,79.7]
Q1-2026     305   51.6 [46.6,56.3]    4.1 [ 3.1, 5.4]    6.4 [ 4.6, 8.3]   85.4 [72.8,93.7]   74.9 [68.0,80.8]
Q2-2026     343   52.9 [48.6,56.9]   12.7 [ 9.9,15.8]   11.5 [ 9.3,13.7]   80.7 [72.6,87.2]   71.9 [64.7,77.7]

```

## Balanced-panel sensitivity
```
balanced panel: 332 repos qualify in all 4 quarters
period        panel ai_involved         cross-section
Q1-2024      0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]
Q4-2025      2.8 [ 2.1, 3.7]    2.9 [ 2.3, 3.5]
Q1-2026      9.4 [ 8.0,11.2]   10.0 [ 8.8,11.5]
Q2-2026     15.3 [13.1,17.6]   16.6 [14.6,18.7]

```

## Reviewer profile of merged PRs (unmerged = implicitly rejected)
```

=== repo-scoped ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     147   70.2 [54.5,84.2]    0.3 [ 0.0, 1.2]    0.1 [ 0.0, 0.3]   29.4 [17.3,45.9]
Q4-2025     178   55.3 [42.9,66.5]    3.3 [ 1.7, 5.4]   19.2 [ 8.8,31.1]   22.2 [13.2,34.2]
Q1-2026     196   49.8 [39.0,61.5]    6.7 [ 2.3,13.8]   24.0 [15.2,33.8]   19.5 [13.3,26.7]
Q2-2026     210   52.2 [43.1,60.4]    4.7 [ 2.5, 7.7]   23.6 [16.5,32.7]   19.5 [14.4,26.2]

=== AI-heavy ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      77   57.0 [41.6,72.9]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   43.0 [28.3,57.0]
Q4-2025     119   51.8 [42.9,59.2]    4.9 [ 2.2,10.7]    6.6 [ 3.0,13.5]   36.8 [24.9,44.6]
Q1-2026     144   54.6 [39.3,64.8]    5.4 [ 2.4,10.8]    6.1 [ 2.7,12.3]   33.9 [27.3,45.7]
Q2-2026     162   55.8 [35.7,70.3]   11.4 [ 5.5,22.0]   10.3 [ 7.7,14.0]   22.5 [13.0,36.2]

=== AI-majority ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     241   71.4 [60.3,80.6]    0.6 [ 0.0, 2.2]    0.3 [ 0.0, 0.8]   27.7 [18.9,38.6]
Q4-2025     528   53.3 [45.6,61.1]    4.7 [ 2.8, 7.0]   25.4 [17.0,33.8]   16.6 [12.6,22.3]
Q1-2026     668   46.3 [39.1,53.3]    5.9 [ 3.8, 8.9]   28.0 [20.4,35.5]   19.8 [15.5,25.7]
Q2-2026     782   48.2 [43.0,53.8]    4.8 [ 3.4, 6.2]   25.2 [19.0,31.0]   21.7 [17.7,26.7]

=== private ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     223   62.0 [51.6,69.3]    1.0 [ 0.0, 3.4]    0.4 [ 0.0, 1.1]   36.5 [28.0,46.6]
Q4-2025     444   49.2 [41.9,57.5]    5.1 [ 3.6, 7.2]   20.6 [12.0,29.8]   25.0 [18.5,32.6]
Q1-2026     565   42.1 [35.8,48.9]    8.0 [ 4.9,12.2]   21.4 [13.5,29.6]   28.5 [22.4,36.0]
Q2-2026     665   43.7 [37.3,50.3]    7.3 [ 5.4, 9.4]   20.8 [13.8,28.1]   28.2 [22.9,35.7]

=== community ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024      68   75.1 [56.1,91.2]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.1]   24.8 [10.0,43.7]
Q4-2025     110   54.8 [40.1,72.1]    4.2 [ 1.0, 9.2]   24.5 [ 9.2,41.6]   16.4 [ 7.9,26.2]
Q1-2026     138   53.4 [38.7,68.1]    4.6 [ 1.3, 8.5]   26.2 [11.5,45.7]   15.8 [10.2,20.6]
Q2-2026     146   58.7 [44.5,70.6]    5.1 [ 2.4, 9.2]   23.6 [14.1,35.2]   12.7 [ 8.7,18.4]

=== public ===
period    repos            m_hum_only             m_ai_only                m_both             m_neither
Q1-2024     174   77.1 [67.4,85.0]    0.0 [ 0.0, 0.0]    0.0 [ 0.0, 0.0]   22.9 [14.5,33.0]
Q4-2025     271   59.8 [52.4,66.1]    3.7 [ 2.4, 5.4]   19.9 [13.7,27.2]   16.6 [13.0,21.5]
Q1-2026     305   53.6 [47.1,59.8]    3.5 [ 2.4, 4.9]   27.7 [21.5,33.8]   15.3 [11.5,20.1]
Q2-2026     343   52.3 [46.7,58.0]    3.4 [ 2.4, 4.6]   26.1 [19.8,32.4]   18.2 [14.5,23.0]

```

## Two-sided bound (weak-prefix indeterminates)
```
headline ai_involved: two-sided bound (CW)
period       upper (reported)    lower (strict C)  delta pp
Q1-2024                 0.00%               0.00%     0.00
Q4-2025                 2.89%               2.89%     0.01
Q1-2026                10.05%              10.03%     0.01
Q2-2026                16.62%              16.56%     0.05

```

## Productivity decomposition (authors vs output/author)
```
balanced repo panel: 397 repos (pooled)
period        PRs  authors PRs/auth merged/auth klines/auth
Q1-2024     63455    10918     5.81        4.42        1.63
Q4-2025     81629    13854     5.89        4.20        2.03
Q1-2026    101859    18811     5.41        3.43        1.92
Q2-2026    118550    23114     5.13        2.87        1.74

```

## Persistent-author productivity (same person, same repo)
```
persistent same-repo authors (active Q1-2024 AND Q2-2026): 1411
  PRs/quarter            2024 mean  18.92 median  7.0 | 2026 mean  22.31 median  7.0
  merged/quarter         2024 mean  14.96 median  5.0 | 2026 mean  15.94 median  4.0
  AI-using in 2026       n=  429  merged/q 22.70->30.37 (1.34x)  klines/q 9.09->21.92 (2.41x)
  non-AI in 2026         n=  982  merged/q 11.57->9.64 (0.83x)  klines/q 4.36->5.43 (1.25x)
  (adopter selection caveat: AI-users were already ~2x heavier contributors in 2024; descriptive, not causal)

```

## Core-contributor merged LOC (CW)
```
period    repos  CW merged kLOC / core author
Q1-2024     251                          6.45
Q4-2025     469                         10.04
Q1-2026     532                         10.72
Q2-2026     582                         17.62

```

## Core-contributor merged LOC split by AI involvement (CW, 95% CI)
```
core-contributor merged (w8) kLOC split by AI involvement (CW, bootstrap 95% CI; floors: undetected AI counts as nonAI)
AI-user columns are per AI-USING core author and sum to their total; noAI-author LOC never enters them
period    repos AI-user repos      noAI-author kLOC    AI-user AI-PR kLOC  AI-user nonAI-PR kLOC
Q1-2024     251             0    6.45 [ 4.62, 8.68]         (no AI users)          (no AI users)
Q4-2025     463            82    6.80 [ 5.46, 8.24]    4.07 [ 1.34, 8.48]    34.13 [ 9.26,76.66]
Q1-2026     513           317    6.50 [ 5.01, 8.52]    4.13 [ 2.91, 5.67]    17.50 [12.42,23.32]
Q2-2026     520           439    5.49 [ 4.35, 6.73]    9.26 [ 5.36,14.84]    20.88 [15.06,28.09]

```

## Figure 4: Merged LOC per core author by adoption cohort (pooled, 95% CI on total)
```
merged (w8) kLOC per CORE author by fixed adoption cohort (pooled author-level means over quarter-active members; bootstrap 95% CI on total)
  early: first AI-tracked PR by 2026-02
  medium: first AI-tracked PR 2026-03..2026-04
  late: first AI-tracked PR 2026-05 or later
  never: no AI-tracked PR through 2026-06
  fleet: >=300 merged PRs in one quarter (fleet/automation operators; assigned before the AI-timing cohorts)
Q2-2026 w8-deflated for May/June PRs; undetected AI counts as nonAI (floors)

period   cohort   authors  AI kLOC nonAI kLOC total kLOC          95% CI  median
Q1-2024  early        184     0.00      10.95      10.95   [ 7.73, 14.54]    2.08
Q1-2024  medium       134     0.00       9.24       9.24   [ 5.71, 13.66]    2.15
Q1-2024  late         101     0.00       8.79       8.79   [ 4.60, 14.10]    1.42
Q1-2024  never       1003     0.00       3.96       3.96   [ 3.34,  4.64]    0.48
Q1-2024  fleet         11     0.00      41.14      41.14   [19.63, 66.76]   34.68
Q4-2025  early        490     1.19      15.72      16.92   [14.37, 19.81]    4.88
Q4-2025  medium       399     0.00       9.83       9.83   [ 7.87, 11.94]    2.72
Q4-2025  late         252     0.00       7.54       7.54   [ 5.53,  9.84]    1.44
Q4-2025  never       1825     0.00       5.58       5.58   [ 4.61,  6.88]    0.71
Q4-2025  fleet         21    10.72     106.35     117.07   [71.13,170.01]   68.18
Q1-2026  early        561     6.26      16.62      22.87   [19.90, 26.23]    8.24
Q1-2026  medium       561     1.16      11.18      12.34   [10.25, 14.82]    3.24
Q1-2026  late         306     0.00      10.49      10.49   [ 8.37, 12.95]    2.42
Q1-2026  never       1853     0.00       6.18       6.18   [ 5.27,  7.34]    0.91
Q1-2026  fleet         32    32.98     123.67     156.64   [100.42,221.77]  106.36
Q2-2026  early        487     9.37      16.73      26.10   [22.11, 30.63]    7.36
Q2-2026  medium       603     6.06      14.85      20.91   [17.99, 24.05]    6.64
Q2-2026  late         519     3.71      11.05      14.76   [12.65, 16.99]    3.44
Q2-2026  never       1854     0.00       6.03       6.03   [ 5.31,  6.86]    0.80
Q2-2026  fleet         33   220.73     302.21     522.94   [210.44,1008.45]  202.28

```

## Merged LOC by approval channel
```
period    merged MLOC humanRev% botOnly% selfUnrev% otherUnrev%
Q1-2024          19.4     72.9%     0.7%      20.0%        6.1%
Q4-2025          47.8     70.9%     9.4%      15.2%        3.9%
Q1-2026          72.5     69.4%    11.4%      15.6%        3.2%
Q2-2026         100.0     59.2%    15.0%      22.0%        3.7%

```

## Attention per line (comments/kLOC primary, bot-clean)
```
attention per line — merged, human-reviewed PRs (pooled)
cohort             PRs     kLOC comments/kLOC window h/kLOC
Q1-2024 all      38712   14,138          3.98         220.7
Q1-2024 ins      12316    4,960          3.52         165.4
Q1-2024 ext      26396    9,178          4.22         250.6
Q4-2025 all      69637   33,857          2.68         192.6
Q4-2025 ins      27634   14,439          2.08         149.4
Q4-2025 ext      42003   19,418          3.12         224.7
Q1-2026 all      84244   50,337          2.03         154.6
Q1-2026 ins      33363   21,767          1.59         114.5
Q1-2026 ext      50881   28,570          2.36         185.1
Q2-2026 all      95866   59,167          1.72         129.0
Q2-2026 ins      37654   26,428          1.36          93.4
Q2-2026 ext      58212   32,740          2.01         157.7

comments/kLOC within FIXED size bands (composition-controlled)
band         Q1-2024    Q4-2025    Q1-2026    Q2-2026
<=10           39.74      33.25      29.13      23.98
11-100         19.58      15.39      12.99       9.13
101-1k          8.38       6.14       5.03       3.85
>1k             1.18       1.03       0.85       0.84

```

## PR fates at matched horizons (w8 primary, w26 sensitivity)
```
--- fates at w8 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        67020    76.4%     17.5%    6.1%
Q1-2024 ins        21879    83.0%     13.4%    3.6%
Q1-2024 ext        45141    73.2%     19.5%    7.3%
Q1-2024 nonAI      67020    76.4%     17.5%    6.1%
Q4-2025 all       122585    72.8%     17.7%    9.5%
Q4-2025 ins        47846    81.4%     13.3%    5.2%
Q4-2025 ext        74739    67.3%     20.4%   12.3%
Q4-2025 AI          3518    56.5%     29.8%   13.7%
Q4-2025 nonAI     119067    73.3%     17.3%    9.4%
Q1-2026 all       179101    64.4%     23.6%   12.0%
Q1-2026 ins        63802    79.8%     14.7%    5.4%
Q1-2026 ext       115299    55.8%     28.5%   15.6%
Q1-2026 AI         20058    57.8%     27.4%   14.8%
Q1-2026 nonAI     159043    65.2%     23.1%   11.7%
Q2-2026 all        93094    57.5%     26.7%   15.9%
Q2-2026 ins        29579    78.4%     16.1%    5.4%
Q2-2026 ext        63515    47.7%     31.6%   20.7%
Q2-2026 AI         14944    57.3%     27.1%   15.6%
Q2-2026 nonAI      78150    57.5%     26.6%   15.9%

--- fates at w26 (matched horizon; immature PRs excluded) ---
cohort                 n  merged% rejected%  limbo%
Q1-2024 all        67020    77.2%     20.0%    2.8%
Q1-2024 ins        21879    83.6%     15.1%    1.3%
Q1-2024 ext        45141    74.1%     22.4%    3.5%
Q1-2024 nonAI      67020    77.2%     20.0%    2.8%
Q4-2025 all       121710    73.8%     22.1%    4.1%
Q4-2025 ins        47515    82.1%     15.8%    2.0%
Q4-2025 ext        74195    68.5%     26.1%    5.4%
Q4-2025 AI          3479    57.8%     35.4%    6.8%
Q4-2025 nonAI     118231    74.3%     21.7%    4.0%


```

## Responsiveness to human asks (clean lane identified)
```
conditional responsiveness to HUMAN ASKS (changes-requested or inline comments)
CLEAN lane = no AI-reviewer activity (identified); mixed = descriptive; all-cause = companion only
HT inclusion-probability weighted (PPS sample -> population estimands): responded% is PR-weighted; LOC share% is the population post-ask LOC ratio
lane                     PRs responded% post-ask LOC share%
Q1-2024 CLEAN            516      68.9%               53.9%
Q1-2024 CLEAN+nonAI      516      68.9%               53.9%
Q1-2024 all-cause        953      31.4%               39.7%
Q4-2025 CLEAN            292      82.8%               61.9%
Q4-2025 CLEAN+nonAI      284      83.2%               62.5%
Q4-2025 mixed            217      77.9%               65.0%
Q4-2025 all-cause       1071      47.2%               47.5%
Q1-2026 CLEAN            234      63.5%               57.2%
Q1-2026 CLEAN+AI          26      23.0%               61.1%
Q1-2026 CLEAN+nonAI      208      79.2%               56.4%
Q1-2026 mixed            237      73.4%               83.3%
Q1-2026 all-cause       1098      28.2%               58.4%
Q2-2026 CLEAN            251      83.7%               41.9%
Q2-2026 CLEAN+AI          44      90.0%               44.9%
Q2-2026 CLEAN+nonAI      207      82.3%               41.5%
Q2-2026 mixed            233      91.2%               65.6%
Q2-2026 all-cause       1111      45.9%               40.4%

```

## Adoption event-study (merged kLOC w8 + submitted kLOC in event time)
```
alignable adopters (core, clean pre-period): 1688
outcome A = MERGED kLOC (w8); months after 2026-04 (w8-immature) excluded. outcome B = SUBMITTED kLOC; full window.

=== outcome A: MERGED kLOC (w8) ===

ALL alignable adopters (unbalanced event panel)
event month  authors mean kLOC/mo  median
t-4             1450         2.76    0.00
t-3             1586         2.69    0.00
t-2             1634         3.17    0.01
t-1             1466         4.51    0.15
t+0             1167         9.58    1.97
t+1              839         8.63    1.31
t+2              513         8.73    0.95
t+3              238         7.90    0.95
t+4              102         7.38    0.40

BALANCED cohort (observed at every offset in [-2..+2]; post-t0 offsets past 2026-04 excluded)
event month  authors mean kLOC/mo  median
t-4              929         3.31    0.00
t-3             1065         2.99    0.01
t-2             1113         3.12    0.03
t-1             1113         4.36    0.19
t+0             1113         9.50    1.94
t+1              785         8.68    1.38
t+2              459         8.51    1.10
t+3              184         7.17    1.26
t+4               48         6.72    0.08

FULLY-MATURE balanced cohort (t0 <= 2026-02: every offset in [-2..+2] w8-mature)
event month  authors mean kLOC/mo  median
t-4              275         5.76    0.07
t-3              411         3.90    0.09
t-2              459         4.18    0.14
t-1              459         4.96    0.44
t+0              459         9.63    2.17
t+1              459         7.97    1.24
t+2              459         8.51    1.10
t+3              184         7.17    1.26
t+4               48         6.72    0.08

=== outcome B: SUBMITTED kLOC (all PRs created in the month; no censoring, full window through 2026-06) ===

ALL alignable adopters (unbalanced event panel)
event month  authors mean kLOC/mo  median
t-4             1450         3.72    0.00
t-3             1586         3.90    0.01
t-2             1634         4.61    0.09
t-1             1688         6.07    0.32
t+0             1688        13.93    4.15
t+1             1466        14.14    2.33
t+2             1167        16.93    1.79
t+3              839        13.95    1.97
t+4              513        11.16    1.15

BALANCED cohort (observed at every offset in [-2..+2])
event month  authors mean kLOC/mo  median
t-4              929         4.39    0.03
t-3             1065         4.40    0.05
t-2             1113         4.60    0.13
t-1             1113         6.09    0.42
t+0             1113        14.79    4.44
t+1             1113        15.43    2.63
t+2             1113        17.08    1.85
t+3              785        13.88    2.07
t+4              459        10.82    1.04

t0 <= 2026-02 cohort (same authors as fully-mature merged panel)
event month  authors mean kLOC/mo  median
t-4              275         7.23    0.20
t-3              411         5.41    0.30
t-2              459         6.16    0.27
t-1              459         7.20    0.70
t+0              459        15.49    4.75
t+1              459        12.93    2.82
t+2              459        12.61    2.33
t+3              459        11.74    2.43
t+4              459        10.82    1.04

```

