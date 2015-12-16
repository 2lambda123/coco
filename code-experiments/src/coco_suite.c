#include "coco.h"
#include "coco_internal.h"

#include "suite_bbob.c"
#include "suite_biobj.c"
#include "suite_toy.c"

/**
 * TODO: Add instructions on how to implement a new suite!
 * TODO: Add asserts regarding input values!
 * TODO: Write getters!
 * TODO: Implement encode/decode problem_index functions!
 */

static coco_suite_t *coco_suite_allocate(const char *suite_name,
                                         const size_t number_of_functions,
                                         const size_t number_of_dimensions,
                                         const size_t *dimensions,
                                         const char *default_instances) {

  coco_suite_t *suite;
  size_t i;

  suite = (coco_suite_t *) coco_allocate_memory(sizeof(*suite));

  suite->suite_name = coco_strdup(suite_name);

  suite->number_of_dimensions = number_of_dimensions;
  suite->dimensions = coco_allocate_memory(suite->number_of_dimensions * sizeof(size_t));
  for (i = 0; i < suite->number_of_dimensions; i++) {
    suite->dimensions[i] = dimensions[i];
  }

  suite->number_of_functions = number_of_functions;
  suite->functions = coco_allocate_memory(suite->number_of_functions * sizeof(size_t));
  for (i = 0; i < suite->number_of_functions; i++) {
    suite->functions[i] = i + 1;
  }

  suite->default_instances = coco_strdup(default_instances);

  suite->current_dimension_id = -1;
  suite->current_function_id = -1;
  suite->current_instance_id = -1;

  suite->current_problem = NULL;

  /* To be set in coco_suite_set_instance() */
  suite->number_of_instances = 0;
  suite->instances = NULL;

  return suite;
}

static void coco_suite_set_instance(coco_suite_t *suite,
                                    const size_t *instance_numbers) {

  size_t i;

  if (!instance_numbers) {
    coco_error("coco_suite_set_instance(): no instance given");
    return;
  }

  suite->number_of_instances = coco_numbers_count(instance_numbers, "suite instance numbers");
  suite->instances = coco_allocate_memory(suite->number_of_instances * sizeof(size_t));
  for (i = 0; i < suite->number_of_instances; i++) {
    suite->instances[i] = instance_numbers[i];
  }

}

static void coco_suite_filter_ids(size_t *items, const size_t number_of_items, const size_t *indices, const char *name) {

  size_t i, j;
  size_t count = coco_numbers_count(indices, name);
  int found;

  for (i = 0; i < number_of_items; i++) {
    found = 0;
    for (j = 0; j < count; j++) {
      if (i == indices[j])
        found = 1;
    }
    if (!found)
      items[i] = 0;
  }

}

static void coco_suite_filter_dimensions(coco_suite_t *suite, const size_t *dims) {

  size_t i, j;
  size_t count = coco_numbers_count(dims, "dimensions");
  int found;

  for (i = 0; i < suite->number_of_dimensions; i++) {
    found = 0;
    for (j = 0; j < count; j++) {
      if (suite->dimensions[i] == dims[j])
        found = 1;
    }
    if (!found)
      suite->dimensions[i] = 0;
  }

}

void coco_suite_free(coco_suite_t *suite) {

  if (suite->suite_name) {
    coco_free_memory(suite->suite_name);
    suite->suite_name = NULL;
  }
  if (suite->dimensions) {
    coco_free_memory(suite->dimensions);
    suite->dimensions = NULL;
  }
  if (suite->functions) {
    coco_free_memory(suite->functions);
    suite->functions = NULL;
  }
  if (suite->instances) {
    coco_free_memory(suite->instances);
    suite->instances = NULL;
  }

  if (suite->current_problem) {
    coco_problem_free(suite->current_problem);
    suite->current_problem = NULL;
  }

  coco_free_memory(suite);
}

static coco_suite_t *coco_suite_intialize(const char *suite_name) {

  coco_suite_t *suite;

  if (strcmp(suite_name, "suite_toy") == 0) {
    suite = suite_toy_allocate();
  } else if (strcmp(suite_name, "suite_bbob") == 0) {
    suite = suite_bbob_allocate();
  } else if (strcmp(suite_name, "suite_biobj") == 0) {
    suite = suite_biobj_allocate();
  } else {
    coco_error("coco_suite(): unknown problem suite");
    return NULL;
  }

  return suite;
}

static char *coco_suite_get_instances_by_year(coco_suite_t *suite, const int year) {

  char *year_string;

  if (strcmp(suite->suite_name, "suite_bbob") == 0) {
    year_string = suite_bbob_get_instances_by_year(year);
  } else if (strcmp(suite->suite_name, "suite_biobj") == 0) {
    year_string = suite_biobj_get_instances_by_year(year);
  } else {
    coco_error("coco_suite_get_instances_by_year(): suite '%s' has no years defined", suite->suite_name);
    return NULL;
  }

  return year_string;
}

coco_problem_t *coco_suite_get_problem(coco_suite_t *suite,
                                       size_t function,
                                       size_t dimension,
                                       size_t instance) {

  coco_problem_t *problem;

  if (strcmp(suite->suite_name, "suite_toy") == 0) {
    problem = suite_toy_get_problem(function, dimension, instance);
  } else if (strcmp(suite->suite_name, "suite_bbob") == 0) {
    problem = suite_bbob_get_problem(function, dimension, instance);
  } else if (strcmp(suite->suite_name, "suite_biobj") == 0) {
    problem = suite_biobj_get_problem(function, dimension, instance);
  } else {
    coco_error("coco_suite_get_problem(): unknown problem suite");
    return NULL;
  }

  return problem;
}

static size_t *coco_suite_get_instance_indices(coco_suite_t *suite, const char *suite_instance) {

  int year = -1;
  char *instances = NULL;
  char *year_string = NULL;
  long year_found, instances_found;
  size_t *result;

  if (suite_instance == NULL)
    return NULL;

  year_found = coco_strfind(suite_instance, "year");
  instances_found = coco_strfind(suite_instance, "instances");

  if ((year_found < 0) && (instances_found < 0))
    return NULL;

  if ((year_found < instances_found) && (year_found >= 0)) {
    /* Stores the year */
    if (coco_options_read_int(suite_instance, "year", &(year)) != 0) {
      if (instances_found >= 0) {
        instances = NULL;
        coco_warning("coco_suite_parse_instance_string(): only the 'year' suite_instance option is taken into account, 'instances' is ignored");
      }
    } else {
      year = -1;
      coco_warning("coco_suite_parse_instance_string(): problems parsing the 'year' suite_instance option, ignored");
    }
  }
  else {
    /* Stores the instances */
    instances = coco_allocate_memory(COCO_PATH_MAX * sizeof(char));
    if (coco_options_read_string(suite_instance, "instances", instances) != 0) {
      if (year_found >= 0) {
        year = -1;
        coco_warning("coco_suite_parse_instance_string(): only the 'instances' suite_instance option is taken into account, 'year' is ignored");
      }
    } else {
      coco_free_memory(instances);
      instances = NULL;
      coco_warning("coco_suite_parse_instance_string(): problems parsing the 'instance' suite_instance option, ignored");
    }
  }

  if (year > 0) {
    year_string = coco_suite_get_instances_by_year(suite, year);
    result = coco_string_get_numbers_from_ranges(year_string, "instances", 1, 0);
    coco_free_memory(year_string);
  }
  else if (instances != NULL) {
    result = coco_string_get_numbers_from_ranges(instances, "instances", 1, 0);
    coco_free_memory(instances);
  }
  else {
    /* This should never happen */
    coco_warning("coco_suite_parse_instance_string(): a problem occurred when parsing suite_instance options, ignored");
    result = NULL;
  }

  return result;
}

/**
 * Iterates through the items from the current_item_id position on in search for the next positive item.
 * If such an item is found, current_item_id points to this item and the method returns 1. If such an
 * item cannot be found, current_item_id points to the first positive item and the method returns 0.
 */
static int coco_suite_is_next_item_found(const size_t number_of_items, const size_t *items, int *current_item_id) {

  /* Iterate through items */
  do {
    (*current_item_id)++;
  } while ((*current_item_id < number_of_items - 1) && (items[*current_item_id] == 0));

  if (items[*current_item_id] != 0) {
    /* Next item is found, return true */
    return 1;
  } else {
    /* Next item cannot be found, move to the first good item and return false */
    *current_item_id = -1;
    do {
      (*current_item_id)++;
    } while ((*current_item_id < number_of_items - 1) && (items[*current_item_id] == 0));
    if (items[*current_item_id] == 0)
      coco_error("coco_suite_is_next_item_found(): the chosen suite has no valid (positive) items");
    return 0;
  }
}

/**
 * Iterates through the instances of the given suite from the current_instance_id position on in search for
 * the next positive instance. If such an instance is found, current_instance_id points to this instance and
 * the method returns 1. If such an instance cannot be found, current_instance_id points to the first
 * positive instance and the method returns 0.
 */
static int coco_suite_is_next_instance_found(coco_suite_t *suite) {

  return coco_suite_is_next_item_found(suite->number_of_instances, suite->instances,
      &suite->current_instance_id);
}

/**
 * Iterates through the functions of the given suite from the current_function_id position on in search for
 * the next positive function. If such a function is found, current_function_id points to this function and
 * the method returns 1. If such a function cannot be found, current_function_id points to the first
 * positive function, current_instance_id points to the first positive instance and the method returns 0.
 */
static int coco_suite_is_next_function_found(coco_suite_t *suite) {

  int result = coco_suite_is_next_item_found(suite->number_of_functions, suite->functions,
      &suite->current_function_id);
  if (!result) {
    /* Reset the instances */
    suite->current_instance_id = -1;
    coco_suite_is_next_instance_found(suite);
  }
  return result;
}

/**
 * Iterates through the dimensions of the given suite from the current_dimension_id position on in search for
 * the next positive dimension. If such a dimension is found, current_dimension_id points to this dimension
 * and the method returns 1. If such a dimension cannot be found, current_dimension_id points to the first
 * positive dimension and the method returns 0.
 */
static int coco_suite_is_next_dimension_found(coco_suite_t *suite) {

  return coco_suite_is_next_item_found(suite->number_of_dimensions, suite->dimensions,
      &suite->current_dimension_id);
}

coco_suite_t *coco_suite(const char *suite_name, const char *suite_instance, const char *suite_options) {

  coco_suite_t *suite;
  size_t *instances;
  char *option_string = NULL;
  char *ptr;
  size_t *indices = NULL;
  size_t *dimensions = NULL;
  long dim_found, dim_id_found;

  /* Initialize the suite */
  suite = coco_suite_intialize(suite_name);

  /* Set the instance */
  if ((!suite_instance) || (strlen(suite_instance) == 0))
    instances = coco_suite_get_instance_indices(suite, suite->default_instances);
  else
    instances = coco_suite_get_instance_indices(suite, suite_instance);
  coco_suite_set_instance(suite, instances);

  /* Apply filter if any given by the suite_options */
  if (coco_options_read_string(suite_options, "function_ids", option_string) > 0) {
    indices = coco_string_get_numbers_from_ranges(option_string, "function_ids", 1, suite->number_of_functions);
    if (indices != NULL) {
      coco_suite_filter_ids(suite->functions, suite->number_of_functions, indices, "function_ids");
      coco_free_memory(option_string);
      coco_free_memory(indices);
    }
  }

  if (coco_options_read_string(suite_options, "instance_ids", option_string) > 0) {
    indices = coco_string_get_numbers_from_ranges(option_string, "instance_ids", 1, suite->number_of_instances);
    if (indices != NULL) {
      coco_suite_filter_ids(suite->instances, suite->number_of_instances, indices, "instance_ids");
      coco_free_memory(option_string);
      coco_free_memory(indices);
    }
  }

  dim_found = coco_strfind(suite_options, "dimensions");
  dim_id_found = coco_strfind(suite_options, "dimension_ids");

  if ((dim_found > 0) && (dim_id_found > 0)) {
    if (dim_found < dim_id_found)
      coco_warning("coco_suite(): 'dimension_ids' suite options ignored because it follows 'dimensions'");
    else
      coco_warning("coco_suite(): 'dimensions' suite options ignored because it follows 'dimension_ids'");
  }

  if ((coco_options_read_string(suite_options, "dimension_ids", option_string) > 0) && (dim_id_found < dim_found)) {
    indices = coco_string_get_numbers_from_ranges(option_string, "dimension_ids", 1, suite->number_of_dimensions);
    if (indices != NULL) {
      coco_suite_filter_ids(suite->dimensions, suite->number_of_dimensions, indices, "dimension_ids");
      coco_free_memory(option_string);
      coco_free_memory(indices);
    }
  }

  if ((coco_options_read_string(suite_options, "dimensions", option_string) > 0) && (dim_found < dim_id_found)) {
    ptr = option_string;
    /* Check for disallowed characters */
    while (*ptr != '\0') {
      if ((*ptr != ',') && !isdigit((unsigned char )*ptr)) {
        coco_warning("coco_suite(): 'dimensions' suite options ignored because of disallowed characters");
        return NULL;
      } else
        ptr++;
    }
    dimensions = coco_string_get_numbers_from_ranges(option_string, "dimensions", suite->dimensions[0],
        suite->dimensions[suite->number_of_dimensions - 1]);
    if (dimensions != NULL) {
      coco_suite_filter_dimensions(suite, dimensions);
      coco_free_memory(option_string);
      coco_free_memory(dimensions);
    }
  }

  /* Check that there are enough dimensions, functions and instances left */
  if ((suite->number_of_dimensions < 1)
      || (suite->number_of_functions < 1)
      || (suite->number_of_instances < 1)) {
    coco_error("coco_suite(): the suite does not contain at least one dimension, function and instance");
    return NULL;
  }

  return suite;
}

/**
 * Returns next problem of the suite by iterating first through available instances, then functions and
 * lastly dimensions. The problem is wrapped with the observer's logger. If there is no next problem,
 * returns NULL.
 */
coco_problem_t *coco_suite_get_next_problem(coco_suite_t *suite, coco_observer_t *observer) {

  size_t function, dimension, instance;

  if (!coco_suite_is_next_instance_found(suite)
      && !coco_suite_is_next_function_found(suite)
      && !coco_suite_is_next_dimension_found(suite))
    return NULL;

  function = suite->functions[suite->current_function_id];
  dimension = suite->dimensions[suite->current_dimension_id];
  instance = suite->instances[suite->current_instance_id];

  if (suite->current_problem)
    coco_problem_free(suite->current_problem);

  suite->current_problem = coco_suite_get_problem(suite, function, dimension, instance);

  return coco_problem_add_observer(suite->current_problem, observer);
}

void coco_benchmark(const char *suite_name,
                    const char *suite_instance,
                    const char *suite_options,
                    const char *observer_name,
                    const char *observer_options,
                    coco_optimizer_t optimizer) {

  coco_suite_t *suite;
  coco_observer_t *observer;
  coco_problem_t *problem;

  suite = coco_suite(suite_name, suite_instance, suite_options);
  observer = coco_observer(observer_name, observer_options);

  while ((problem = coco_suite_get_next_problem(suite, observer)) != NULL) {

    optimizer(problem);

  }

  coco_observer_free(observer);
  coco_suite_free(suite);

}
