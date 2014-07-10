#include <stdlib.h>
#include <stdio.h>

#include "numbbo.h"

void my_optimizer(numbbo_problem_t *problem) {
    static const int budget = 100000;
    const size_t number_of_variables = numbbo_get_number_of_variables(problem);
    numbbo_random_state_t *rng = numbbo_new_random(0xdeadbeef);
    double *x = numbbo_allocate_vector(number_of_variables);
    const double *lower = numbbo_get_smallest_values_of_interest(problem);
    const double *upper = numbbo_get_largest_values_of_interest(problem);
    double y;

    /* Skip any problems with more than 20 variables */
    if (number_of_variables > 20) 
        return;
    for (int i = 0; i < budget; ++i) {
        for (size_t j = 0; j < number_of_variables; ++j) {
            const double range = upper[j] - lower[j];
            x[j] = lower[j] + numbbo_uniform_random(rng) * range;
        }
        numbbo_evaluate_function(problem, x, &y);
    }
    numbbo_free_random(rng);
    numbbo_free_memory(x);
}

int main(int argc, char **argv) {
    numbbo_benchmark("toy_suit", "logger_observer",//"toy_observer",
                     "random_search", my_optimizer);
}
