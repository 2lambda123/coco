cmake_minimum_required(VERSION 3.19)
project(ExampleExperiment
  DESCRIPTION "Example COCO experiment"
  LANGUAGES C)

find_library(MATH_LIBRARY m)

## Add core coco experiment library to build
add_library(coco STATIC coco.c coco.h)
target_include_directories(coco PUBLIC .)
if(MATH_LIBRARY)
    target_link_libraries(coco PUBLIC ${MATH_LIBRARY})
endif()

## Add example experiment and link agains the coco library
## defined above.
add_executable(example_experiment example_experiment.c)
target_link_libraries(example_experiment PUBLIC coco)
#if(MATH_LIBRARY)
#    target_link_libraries(example_experiment PUBLIC ${MATH_LIBRARY})
#endif()
