#include <stdbool.h>
#include <assert.h>

#include "numbbo.h"
#include "numbbo_problem.c"

typedef struct {
    double *offset;
    double *shifted_x;
    numbbo_free_function_t old_free_problem;
} shift_variables_state_t;

static void _sv_evaluate_function(numbbo_problem_t *self, double *x, double *y) {
    numbbo_transformed_problem_t *problem = (numbbo_transformed_problem_t *)self;
    assert(problem->inner_problem != NULL);
    assert(problem->state != NULL);
    shift_variables_state_t *state = (shift_variables_state_t *)problem->state;

    for (int i = 0; i < self->number_of_parameters; ++i) {
        state->shifted_x[i] = x[i] - state->offset[i];
    }
    numbbo_evaluate_function(problem->inner_problem, state->shifted_x, y);
}

static void _sv_free_problem(numbbo_problem_t *self) {
    numbbo_transformed_problem_t *problem = (numbbo_transformed_problem_t *)self;
    assert(problem->inner_problem != NULL);
    assert(problem->state != NULL);
    shift_variables_state_t *state = (shift_variables_state_t *)problem->state;
    
    numbbo_free_memory(state->shifted_x);
    numbbo_free_memory(state->offset);
    state->old_free_problem(self);
}

/* Shift all variables of ${inner_problem} by ${amount}.
 */
numbbo_problem_t *shift_variables(numbbo_problem_t *inner_problem,
                                  const double *offset,
                                  const bool shift_bounds) {
    assert(inner_problem != NULL);
    assert(offset != NULL);

    size_t number_of_parameters = inner_problem->number_of_parameters;
    numbbo_transformed_problem_t *obj =
        numbbo_allocate_transformed_problem(inner_problem);
    numbbo_problem_t *problem = (numbbo_problem_t *)obj;

    shift_variables_state_t *state = numbbo_allocate_memory(sizeof(*state));
    state->offset = numbbo_duplicate_vector(offset, number_of_parameters);
    state->shifted_x = numbbo_allocate_vector(number_of_parameters);
    state->old_free_problem = problem->free_problem;

    obj->state = state;

    problem->evaluate_function = _sv_evaluate_function;
    problem->free_problem = _sv_free_problem;
    return problem;
}
