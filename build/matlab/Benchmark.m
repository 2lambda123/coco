classdef Benchmark < handle
  
    properties
        problem_suit
        observer
        options
        function_index
    end
    
    methods
        function B = Benchmark(problem_suit, observer, options)
            B.problem_suit = problem_suit;
            B.observer = observer;
            B.options = options;
            B.function_index = 0;
        end
    end
    
end

