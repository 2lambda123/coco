---
layout: default
permalink: /testsuites/bbob-biobj
parent: Test Suites
nav_order: 3
title: bbob-biobj
has_toc: false
---


# The bbob-biobj Test Suite

|   | &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
|---|---|
| The [biobjective bbob-biobj test suite](https://hal.inria.fr/hal-01296987) from 2016 is COCO's first multiobjective test suite with 55 noiseless, scalable bi-objective functions that utilize 10 of the original 24 <a href="bbob">bbob</a> test functions. Each function is provided in various dimensions (2, 3, 5, 10, 20, 40, and scalable to any dimension). Hypervolume reference values and thus the postprocessing by COCO are available for the first 15 function instances in the provided dimensions.| <img align="top" position="relative" src="https://numbbo.github.io/ppdata-archive/bbob-biobj/2016/pprldmany_10D_noiselessall.svg" alt="ECDF of runtimes for 16 algorithms on the bbob-biobj suite in dimension 10" width="100%"/>|

- The paper [_Using Well-Understood Single-Objective Functions_][1] [_in Multiobjective Black-Box Optimization Test Suites_][1] describes the suite construction in detail (accepted for publication in ECJ).
- More details about the test functions, including visualizations of search and objective space, can be found on <a href="https://numbbo.github.io/bbob-biobj/">this supplementary material webpage</a> and specificities of the performance assessment for the bi-objective testbeds are <a href="https://arxiv.org/abs/1605.01746">documented here</a>.
- A list of all so-far benchmarked algorithms on the bbob-biobj suite together with their links to papers describing the experiment can be found in our <a href="https://numbbo.github.io/data-archive/bbob-biobj/">bbob-biobj data archive</a>.
- Postprocessed data can be found <a href="https://numbbo.github.io/ppdata-archive">here</a>.
- For detailed explanations of how to use the functions in a COCO benchmarking experiment, see the <a href="https://github.com/numbbo/coco">COCO code page</a> on Github. 

[1]: https://hal.inria.fr/hal-01296987

<link rel="stylesheet" href="{{ '/assets/css/custom.css' | relative_url }}"/>