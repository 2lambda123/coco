import java.util.Random;
import javacoco.*;

/* Draft: determine native methods to declare */

public class demo {
    public static void my_optimizer(Problem problem, double[] lower_bounds, double[] upper_bounds, double budget) {
        System.out.println("In optimizer...");
        int n = lower_bounds.length;
        int i, j;
        double[] x = new double[n];
        double[] y;
        for (i = 0; i < budget; i++){
            Random r = new Random();
            for (j = 0; j < n; j++){
                x[j] = lower_bounds[j] + (upper_bounds[j] - lower_bounds[j]) * r.nextDouble();
            }
            JNIinterface my_interface = new JNIinterface();
            y = my_interface.coco_evaluate_function(problem, x);
        }
        
        
        
        
    }
    
    public static void main(String[] args) {
        // TODO Auto-generated method stub
    	JNIinterface my_interface = new JNIinterface();
        Benchmark my_benchmark = new Benchmark("bbob2009", "bbob_observer", "random_search"); // parameters to be defined
        int i;
        for (i = 0; i < 500; i++) {
            Problem problem = my_interface.next_problem(my_benchmark);
            JNIinterface.coco_evaluate_function(problem, {1., 2.});
            System.out.println("Optimizing " + problem.toString());
            my_optimizer(problem, JNIinterface.coco_get_smallest_values_of_interest(problem), JNIinterface.coco_get_largest_values_of_interest(problem), 10000);
        }
        
        
    }
    
}