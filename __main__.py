#!/usr/bin/env python
"""python bbob_pproc should run through smoothly from a system command shell. 

this test can and should become much more sophisticated 

"""


if __name__ == "__main__": 
    import os
    os.system('python bbob_pproc/rungeneric.py test_bbob_pproc_input_data/DIRECT')
    os.system('python bbob_pproc/rungeneric.py --omit-single' +
                    ' test_bbob_pproc_input_data/DIRECT ' + 
                    ' test_bbob_pproc_input_data/Cauchy-EDA') 
