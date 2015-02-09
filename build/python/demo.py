#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import coco
import numpy as np

def my_optimizer(f, lower_bounds, upper_bounds, budget):
    print("In optimizer...")
    n = len(lower_bounds)
    delta = upper_bounds - lower_bounds
    x = lower_bounds + np.random.rand(n) * delta
    for i in range(budget):
        y = f(x)

for problem in coco.Benchmark("bbob2009", "bbob2009_observer", "random_search"):
    print("Optimizing '%s' ... " % str(problem))
    my_optimizer(problem,
                 problem.lower_bounds,
                 problem.upper_bounds,
                 10000)
    problem.free()
