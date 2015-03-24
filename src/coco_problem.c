#include <float.h>
#include "coco.h"

#include "coco_utilities.c"

/***********************************
 * Global definitions in this file
 *
 * TODO: are these really needed? 
 * Only if they would need to be used from
 * outside. Benchmarks that are included in
 * coco_benchmark.c can include coco_problem.c
 * directly due to the amalgamate magic.
 * 
 ***********************************/

coco_problem_t *
coco_allocate_problem(const size_t number_of_variables,
                      const size_t number_of_objectives,
                      const size_t number_of_constraints); 
coco_problem_t *
coco_duplicate_problem(coco_problem_t *other);
typedef void (*coco_transform_free_data_t)(void *data);

/* typedef coco_transform_data_t; */
coco_problem_t *
coco_allocate_transformed_problem(coco_problem_t *inner_problem, void *userdata,
                                  coco_transform_free_data_t free_data);
void *coco_get_transform_data(coco_problem_t *self);
coco_problem_t *
coco_get_transform_inner_problem(coco_problem_t *self);

/* typedef coco_stacked_problem_data_t; */
coco_problem_t *
coco_stacked_problem_allocate(coco_problem_t *problem1_to_be_stacked,
                              coco_problem_t *problem2_to_be_stacked);

/***********************************/

/**
 * coco_allocate_problem(number_of_variables):
 *
 * Allocate and pre-populate a new coco_problem_t for a problem with
 * ${number_of_variables}.
 */
coco_problem_t *
coco_allocate_problem(const size_t number_of_variables,
                      const size_t number_of_objectives,
                      const size_t number_of_constraints) {
  coco_problem_t *problem;
  problem = (coco_problem_t *)coco_allocate_memory(sizeof(coco_problem_t));
  /* Initialize fields to sane/safe defaults */
  problem->initial_solution = NULL;
  problem->evaluate_function = NULL;
  problem->evaluate_constraint = NULL;
  problem->recommend_solutions = NULL;
  problem->free_problem = NULL;
  problem->number_of_variables = number_of_variables;
  problem->number_of_objectives = number_of_objectives;
  problem->number_of_constraints = number_of_constraints;
  problem->smallest_values_of_interest =
      coco_allocate_vector(number_of_variables);
  problem->largest_values_of_interest =
      coco_allocate_vector(number_of_variables);
  problem->best_parameter = coco_allocate_vector(number_of_variables);
  problem->best_value = coco_allocate_vector(number_of_objectives);
  problem->problem_name = NULL;
  problem->problem_id = NULL;
  problem->evaluations = 0;
  problem->final_target_delta[0] = 1e-8; /* in case to be modified by the benchmark */
  problem->best_observed_fvalue[0] = DBL_MAX; 
  problem->best_observed_evaluation[0] = 0;
  problem->data = NULL;
  return problem;
}

coco_problem_t *
coco_duplicate_problem(coco_problem_t *other) {
  size_t i;
  coco_problem_t *problem;
  problem = coco_allocate_problem(other->number_of_variables,
                                  other->number_of_objectives,
                                  other->number_of_constraints);

  problem->evaluate_function = other->evaluate_function;
  problem->evaluate_constraint = other->evaluate_constraint;
  problem->recommend_solutions = other->recommend_solutions;
  problem->free_problem = NULL;

  for (i = 0; i < problem->number_of_variables; ++i) {
    problem->smallest_values_of_interest[i] =
        other->smallest_values_of_interest[i];
    problem->largest_values_of_interest[i] =
        other->largest_values_of_interest[i];
    problem->best_parameter[i] = other->best_parameter[i];
  }

  for (i = 0; i < problem->number_of_objectives; ++i) {
    problem->best_value[i] = other->best_value[i];
  }

  problem->problem_name = coco_strdup(other->problem_name);
  problem->problem_id = coco_strdup(other->problem_id);
  return problem;
}

/**
 * Generic data member of a transformed (or "outer") coco_problem_t.
 */
typedef struct {
  coco_problem_t *inner_problem;
  void *data;
  coco_transform_free_data_t free_data;
} coco_transform_data_t;

static void _tfp_evaluate_function(coco_problem_t *self, const double *x, double *y) {
  coco_transform_data_t *data;
  assert(self != NULL);
  assert(self->data != NULL);
  data = self->data;
  assert(data->inner_problem != NULL);

  coco_evaluate_function(data->inner_problem, x, y);
}

static void _tfp_evaluate_constraint(coco_problem_t *self, const double *x,
                                     double *y) {
  coco_transform_data_t *data;
  assert(self != NULL);
  assert(self->data != NULL);
  data = self->data;
  assert(data->inner_problem != NULL);

  coco_evaluate_constraint(data->inner_problem, x, y);
}

static void _tfp_recommend_solutions(coco_problem_t *self, const double *x,
                                     size_t number_of_solutions) {
  coco_transform_data_t *data;
  assert(self != NULL);
  assert(self->data != NULL);
  data = self->data;
  assert(data->inner_problem != NULL);

  coco_recommend_solutions(data->inner_problem, x, number_of_solutions);
}

static void _tfp_free_problem(coco_problem_t *self) {
  coco_transform_data_t *data;
  assert(self != NULL);
  assert(self->data != NULL);
  data = self->data;
  assert(data->inner_problem != NULL);

  if (data->inner_problem != NULL) {
    coco_free_problem(data->inner_problem);
    data->inner_problem = NULL;
  }
  if (data->data != NULL) {
    if (data->free_data != NULL) {
      data->free_data(data->data);
      data->free_data = NULL;
    }
    coco_free_memory(data->data);
    data->data = NULL;
  }
  /* Let the generic free problem code deal with the rest of the
   * fields. For this we clear the free_problem function pointer and
   * recall the generic function.
   */
  self->free_problem = NULL;
  coco_free_problem(self);
}

/**
 * coco_allocate_transformed_problem(inner_problem):
 *
 * Allocate a transformed problem that wraps ${inner_problem}. By
 * default all methods will dispatch to the ${inner_problem} method.
 *
 */
coco_problem_t *
coco_allocate_transformed_problem(coco_problem_t *inner_problem, void *userdata,
                                  coco_transform_free_data_t free_data) {
  coco_transform_data_t *data;
  coco_problem_t *self;

  data = coco_allocate_memory(sizeof(*data));
  data->inner_problem = inner_problem;
  data->data = userdata;
  data->free_data = free_data;

  self = coco_duplicate_problem(inner_problem);
  self->evaluate_function = _tfp_evaluate_function;
  self->evaluate_constraint = _tfp_evaluate_constraint;
  self->recommend_solutions = _tfp_recommend_solutions;
  self->free_problem = _tfp_free_problem;
  self->data = data;
  return self;
}

void *coco_get_transform_data(coco_problem_t *self) {
  assert(self != NULL);
  assert(self->data != NULL);
  assert(((coco_transform_data_t *)self->data)->data != NULL);

  return ((coco_transform_data_t *)self->data)->data;
}

coco_problem_t *
coco_get_transform_inner_problem(coco_problem_t *self) {
  assert(self != NULL);
  assert(self->data != NULL);
  assert(((coco_transform_data_t *)self->data)->inner_problem != NULL);

  return ((coco_transform_data_t *)self->data)->inner_problem;
}

/** type provided coco problem data for a stacked coco problem
 */
typedef struct {
  coco_problem_t *problem1;
  coco_problem_t *problem2;
} coco_stacked_problem_data_t;

static void stacked_problem_evaluate(coco_problem_t *self, const double *x, double *y) {
  coco_stacked_problem_data_t* data = (coco_stacked_problem_data_t*)self->data; 

  assert(coco_get_number_of_objectives(self) ==
           coco_get_number_of_objectives(data->problem1) + coco_get_number_of_objectives(data->problem2));

  coco_evaluate_function(data->problem1, x, &y[0]);
  coco_evaluate_function(data->problem2, x, &y[coco_get_number_of_objectives(data->problem1)]);
}

static void stacked_problem_evaluate_constraint(coco_problem_t *self, const double *x, double *y) {
  coco_stacked_problem_data_t* data = (coco_stacked_problem_data_t*)self->data;

  assert(coco_get_number_of_constraints(self) ==
           coco_get_number_of_constraints(data->problem1) + coco_get_number_of_constraints(data->problem2));

  if (coco_get_number_of_constraints(data->problem1) > 0)
    coco_evaluate_constraint(data->problem1, x, y);
  if (coco_get_number_of_constraints(data->problem2) > 0)
    coco_evaluate_constraint(data->problem2, x, &y[coco_get_number_of_constraints(data->problem1)]);  
}

static void stacked_problem_free(coco_problem_t *self) {
  coco_stacked_problem_data_t *data;
  assert(self != NULL);
  assert(self->data != NULL);
  data = self->data;

  if (data->problem1 != NULL) {
    coco_free_problem(data->problem1);
    data->problem1 = NULL;
  }
  if (data->problem2 != NULL) {
    coco_free_problem(data->problem2);
    data->problem2 = NULL;
  }
  /* Let the generic free problem code deal with the rest of the
   * fields. For this we clear the free_problem function pointer and
   * recall the generic function.
   */
  self->free_problem = NULL;
  coco_free_problem(self);
}

/**
 * Return a problem that stacks the output of two problems, namely
 * of coco_evaluate_function and coco_evaluate_constraint. The accepted
 * input remains the same and must be identical for the stacked
 * problems. 
 * 
 * This is particularly useful to generate multiobjective problems,
 * e.g. a biobjective problem from two single objective problems.
 *
 * Details: regions of interest must either agree or at least one
 * of them must be NULL. Best parameter becomes somewhat meaningless. 
 */
coco_problem_t *coco_stacked_problem_allocate(coco_problem_t *problem1, coco_problem_t *problem2) {
  const size_t number_of_variables = coco_get_number_of_variables(problem1); 
  const size_t number_of_objectives =
      coco_get_number_of_objectives(problem1) + coco_get_number_of_objectives(problem2);
  const size_t number_of_constraints =
      coco_get_number_of_constraints(problem1) + coco_get_number_of_constraints(problem2);
  size_t i;
  char *s;
  const double *smallest, *largest;
  coco_stacked_problem_data_t *data;
  coco_problem_t *problem; /* the new coco problem */

  assert(coco_get_number_of_variables(problem1) == coco_get_number_of_variables(problem2));

  problem = coco_allocate_problem(number_of_variables, number_of_objectives, number_of_constraints);

  s = coco_strconcat(coco_get_problem_id(problem1), "_-_");
  problem->problem_id = coco_strconcat(s, coco_get_problem_id(problem2));
  coco_free_memory(s);
  s = coco_strconcat(coco_get_problem_name(problem1), " + ");
  problem->problem_name = coco_strconcat(s, coco_get_problem_name(problem2));
  coco_free_memory(s);
             
  problem->evaluate_function = stacked_problem_evaluate;
  if (number_of_constraints > 0)
    problem->evaluate_constraint = stacked_problem_evaluate_constraint;
  
  /* set/copy "boundaries" and best_parameter */
  smallest = problem1->smallest_values_of_interest;
  if (smallest == NULL)
    smallest = problem2->smallest_values_of_interest;
    
  largest = problem1->largest_values_of_interest;
  if (largest == NULL)
    largest = problem2->largest_values_of_interest;
    
  for (i = 0; i < number_of_variables; ++i) {
    if (problem2->smallest_values_of_interest != NULL)
      assert(smallest[i] == problem2->smallest_values_of_interest[i]);
    if (problem2->largest_values_of_interest != NULL)
      assert(largest[i] == problem2->largest_values_of_interest[i]);
      
    if (smallest != NULL)
      problem->smallest_values_of_interest[i] = smallest[i];
    if (largest != NULL)
      problem->largest_values_of_interest[i] = largest[i];
      
    if (problem->best_parameter) /* bbob2009 logger doesn't work then anymore */
      coco_free_memory(problem->best_parameter);
    problem->best_parameter = NULL;
    if (problem->best_value)
      coco_free_memory(problem->best_value);
    problem->best_value = NULL;  /* bbob2009 logger doesn't work */
  }
  
  /* setup data holder */
  data = coco_allocate_memory(sizeof(*data));
  data->problem1 = problem1;
  data->problem2 = problem2;

  problem->data = data;
  problem->free_problem = stacked_problem_free; /* free self->data and coco_free_problem(self) */

  return problem;
}
