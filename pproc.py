#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Raw post-processing routines.

This module implements class :py:class:`DataSet`, unit element in the
post-processing and class :py:class:`DataSetList`, sequence of instances
of :py:class:`DataSet`.

Futhermore it implements methods for dealing with a third data structure
which is a dictionary of :py:class:`DataSetList` which is handy when
dealing with :py:class:`DataSetList` instances from multiple algorithms
for comparisons.

"""

from __future__ import absolute_import

import sys
import os
import ast
import re
import pickle
import warnings
from pdb import set_trace
import numpy, numpy as np
from bbob_pproc import findfiles, toolsstats, toolsdivers
from bbob_pproc.readalign import split, alignData, HMultiReader, VMultiReader
from bbob_pproc.readalign import HArrayMultiReader, VArrayMultiReader, alignArrayData
from bbob_pproc.ppfig import consecutiveNumbers

do_assertion = False  # expensive assertions
dataSetTargets = [10, 1., 1e-1, 1e-3, 1e-5, 1e-8]

# CLASS DEFINITIONS
class DataSet:
    """Unit element for the COCO post-processing.

    An instance of this class is created from one unit element of
    experimental data. One unit element would correspond to data for a
    given algorithm (a given :py:attr:`algId` and a :py:attr:`comment`
    line) and a given problem (:py:attr:`funcId` and
    :py:attr:`dimension`).

    Class attributes:

      - *funcId* -- function Id (integer)
      - *dim* -- dimension (integer)
      - *indexFiles* -- associated index files (list of strings)
      - *dataFiles* -- associated data files (list of strings)
      - *comment* -- comment for the setting (string)
      - *targetFuncValue* -- final target function value (float), might be missing
      - *precision* -- final ftarget - fopt (float), data with 
                       target[idat] < precision are optional and possibly nan.  
      - *algId* -- algorithm name (string)
      - *evals* -- data aligned by function values (array)
      - *funvals* -- data aligned by function evaluations (array)
      - *maxevals* -- maximum number of function evaluations (array)
      - *finalfunvals* -- final function values (array)
      - *readmaxevals* -- maximum number of function evaluations read
                          from index file (array)
      - *readfinalFminusFtarget* -- final function values - ftarget read
                                    from index file (array)
      - *pickleFile* -- associated pickle file name (string)
      - *target* -- target function values attained (array)
      - *ert* -- ert for reaching the target values in target (array)
      - *instancenumbers* -- list of numbers corresponding to the instances of
                     the test function considered (list of int)
      - *isFinalized* -- list of bool for if runs were properly finalized

    :py:attr:`evals` and :py:attr:`funvals` are arrays of data collected
    from :py:data:`N` data sets.

    Both have the same format: zero-th column is the value on which the
    data of a row is aligned, the :py:data:`N` subsequent columns are
    either the numbers of function evaluations for :py:attr:`evals` or
    function values for :py:attr:`funvals`.
    
        >>> import sys
        >>> sys.path.append('path_to_bbob_proc')
        >>> import bbob_proc as bb
        >>> dslist = bb.load('BIPOP-CMA-ES_hansen_noiseless/bbobexp_f2.info')[0]
        >>> dslist
        [DataSet(cmaes V3.30.beta on f2 2-D),
         DataSet(cmaes V3.30.beta on f2 3-D),
         DataSet(cmaes V3.30.beta on f2 5-D),
         DataSet(cmaes V3.30.beta on f2 10-D),
         DataSet(cmaes V3.30.beta on f2 20-D),
         DataSet(cmaes V3.30.beta on f2 40-D)]
        >>> ds = dslist[3]
        >>> ds
        DataSet(cmaes V3.30.beta on f2 10-D)
        >>> ds.evals[(0,10,30,-1),:]  # first 10th 30th and last row, each first element is ftarget
        array([[  3.98107171e+07,   1.00000000e+00,   1.00000000e+00,
                  1.00000000e+00,   1.00000000e+00,   1.00000000e+00,
                  1.00000000e+00,   1.00000000e+00,   1.00000000e+00,
                  1.00000000e+00,   1.00000000e+00,   1.00000000e+00,
                  1.00000000e+00,   1.00000000e+00,   1.00000000e+00,
                  1.00000000e+00],
               [  3.98107171e+05,   3.70000000e+01,   9.80000000e+01,
                  4.10000000e+01,   3.50000000e+01,   2.00000000e+01,
                  8.40000000e+01,   9.70000000e+01,   4.70000000e+01,
                  2.00000000e+01,   2.00000000e+00,   2.90000000e+01,
                  7.20000000e+01,   1.76000000e+02,   1.40000000e+02,
                  2.10000000e+01],
               [  3.98107171e+01,   4.30500000e+03,   2.53200000e+03,
                  3.25800000e+03,   3.58800000e+03,   3.04400000e+03,
                  3.21000000e+03,   1.96000000e+03,   3.35600000e+03,
                  2.81900000e+03,   3.11400000e+03,   2.20700000e+03,
                  2.58700000e+03,   2.96200000e+03,   3.67000000e+03,
                  3.46600000e+03],
               [  1.58489319e-09,              nan,              nan,
                             nan,              nan,              nan,
                             nan,              nan,              nan,
                             nan,              nan,              nan,
                             nan,              nan,   6.12200000e+03,
                             nan]])
        >>> import numpy as np
        >>> idx = range(0, 50, 10)
        >>> np.array([idx, ds.target[idx], ds.ert[idx]]).T  # ERT expected runtime for some targets and all trials
        array([[  0.00000000e+00,   3.98107171e+07,   1.00000000e+00],
               [  1.00000000e+01,   3.98107171e+05,   6.12666667e+01],
               [  2.00000000e+01,   3.98107171e+03,   1.13626667e+03],
               [  3.00000000e+01,   3.98107171e+01,   3.07186667e+03],
               [  4.00000000e+01,   3.98107171e-01,   4.81333333e+03]])
        
    """

    # TODO: unit element of the post-processing: one algorithm, one problem
    # TODO: if this class was to evolve, how do we make previous data
    # compatible?

    # Private attribute used for the parsing of info files.
    _attributes = {'funcId': ('funcId', int), 'DIM': ('dim',int),
                    'Precision': ('precision', float), 'Fopt': ('fopt', float),
                    'targetFuncValue': ('targetFuncValue', float),
                    'algId': ('algId', str)}

    def __init__(self, header, comment, data, indexfile, verbose=True):
        """Instantiate a DataSet.

        The first three input argument corresponds to three consecutive
        lines of an index file (info extension).

        :keyword string header: information of the experiment
        :keyword string comment: more information on the experiment
        :keyword string data: information on the runs of the experiment
        :keyword string indexfile: string for the file name from where
                                   the information come
        :keyword bool verbose: controls verbosity

        """
        # Extract information from the header line.
        self._extra_attr = []
        self.__parseHeader(header)

        # Read in second line of entry (comment line). The information
        # is only stored if the line starts with "%", else it is ignored.
        if comment.startswith('%'):
            self.comment = comment.strip()
        else:
            #raise Exception()
            warnings.warn('Comment line: %s is skipped,' % (comment) +
                          'it does not start with \%.')
            self.comment = ''

        filepath = os.path.split(indexfile)[0]
        self.indexFiles = [indexfile]
        self.dataFiles = []
        self.instancenumbers = []
        self.evals = []
        self.isFinalized = []
        self.readmaxevals = []
        self.readfinalFminusFtarget = []

        # Split line in data file name(s) and run time information.
        parts = data.split(', ')
        for elem in parts:
            if elem.endswith('dat'):
                #Windows data to Linux processing
                filename = elem.replace('\\', os.sep)
                #Linux data to Windows processing
                filename = filename.replace('/', os.sep)
                self.dataFiles.append(filename)
            else:
                if not ':' in elem:
                    # if elem does not have ':' it means the run was not
                    # finalized properly.
                    self.instancenumbers.append(ast.literal_eval(elem))
                    # In this case, what should we do? Either we try to process
                    # the corresponding data anyway or we leave it out.
                    # For now we leave it in.
                    self.isFinalized.append(False)
                    warnings.warn('Caught an ill-finalized run in %s for %s'
                                  % (indexfile,
                                     os.path.join(filepath, self.dataFiles[-1])))
                    self.readmaxevals.append(0)
                    self.readfinalFminusFtarget.append(numpy.inf)
                else:
                    itrial, info = elem.split(':', 1)
                    self.instancenumbers.append(ast.literal_eval(itrial))
                    self.isFinalized.append(True)
                    readmaxevals, readfinalf = info.split('|', 1)
                    self.readmaxevals.append(int(readmaxevals))
                    self.readfinalFminusFtarget.append(float(readfinalf))

        if verbose:
            print "%s" % self.__repr__()

        # Treat successively the data in dat and tdat files:
        # put into variable dataFiles the files where to look for data
        dataFiles = list(os.path.join(filepath, os.path.splitext(i)[0] + '.dat')
                         for i in self.dataFiles)
        data = HMultiReader(split(dataFiles))
        if verbose:
            print ("Processing %s: %d/%d trials found."
                   % (dataFiles, len(data), len(self.instancenumbers)))
        (adata, maxevals, finalfunvals) = alignData(data)
        self.evals = adata
        try:
            for i in range(len(maxevals)):
                self.maxevals[i] = max(maxevals[i], self.maxevals[i])
                self.finalfunvals[i] = min(finalfunvals[i], self.finalfunvals[i])
        except AttributeError:
            self.maxevals = maxevals
            self.finalfunvals = finalfunvals

        dataFiles = list(os.path.join(filepath, os.path.splitext(i)[0] + '.tdat')
                         for i in self.dataFiles)
        data = VMultiReader(split(dataFiles))
        if verbose:
            print ("Processing %s: %d/%d trials found."
                   % (dataFiles, len(data), len(self.instancenumbers)))
        (adata, maxevals, finalfunvals) = alignData(data)
        self.funvals = adata
        try:
            for i in range(len(maxevals)):
                self.maxevals[i] = max(maxevals[i], self.maxevals[i])
                self.finalfunvals[i] = min(finalfunvals[i], self.finalfunvals[i])
        except AttributeError:
            self.maxevals = maxevals
            self.finalfunvals = finalfunvals
        #TODO: take for maxevals the max for each trial, for finalfunvals the min...

        #extensions = {'.dat':(HMultiReader, 'evals'), '.tdat':(VMultiReader, 'funvals')}
        #for ext, info in extensions.iteritems(): # ext is defined as global
            ## put into variable dataFiles the files where to look for data
            ## basically append 
            #dataFiles = list(i.rsplit('.', 1)[0] + ext for i in self.dataFiles)
            #data = info[0](split(dataFiles))
            ## split is a method from readalign, info[0] is a method of readalign
            #if verbose:
                #print ("Processing %s: %d/%d trials found."
                       #% (dataFiles, len(data), len(self.itrials)))
            #(adata, maxevals, finalfunvals) = alignData(data)
            #setattr(self, info[1], adata)
            #try:
                #if all(maxevals > self.maxevals):
                    #self.maxevals = maxevals
                    #self.finalfunvals = finalfunvals
            #except AttributeError:
                #self.maxevals = maxevals
                #self.finalfunvals = finalfunvals
        #CHECKING PROCEDURE
        tmp = []
        for i in range(len(maxevals)):
            tmp.append(self.maxevals[i] == self.readmaxevals[i])
        if not all(tmp):
            warnings.warn('There is a difference between the maxevals in the '
                          '*.info file and in the data files.')

        # Compute ERT
        self.computeERTfromEvals()

    def computeERTfromEvals(self):
        """Sets the attributes ert and target from the attribute evals."""
        self.ert = []
        self.target = []
        for i in self.evals:
            data = i.copy()
            data = data[1:]
            succ = (numpy.isnan(data)==False)
            if any(numpy.isnan(data)):
                data[numpy.isnan(data)] = self.maxevals[numpy.isnan(data)]
            self.ert.append(toolsstats.sp(data, issuccessful=succ)[0])
            self.target.append(i[0])

        self.ert = numpy.array(self.ert)
        self.target = numpy.array(self.target)

    def __eq__(self, other):
        """Compare indexEntry instances."""
        res = (self.__class__ is other.__class__ and
               self.funcId == other.funcId and
               self.dim == other.dim and
               self.precision == other.precision and
               self.algId == other.algId and
               self.comment == other.comment)
        if hasattr(self, '_extra_attr'): # Backward compatibility
            for i in self._extra_attr:
                res = (res and hasattr(other, i) and
                       getattr(other, i) == getattr(self, i))
                if not res:
                    break
        return res

    def __ne__(self,other):
        return not self.__eq__(other)

    def __repr__(self):
        res = ('DataSet(%s on f%s %d-D'
               % (self.algId, str(self.funcId), self.dim))
        for i in getattr(self, '_extra_attr', ()):
            res += ', %s = %s' % (i, getattr(self, i))
        res += ')'
        return res

    def info(self):
        """Return some text info to display onscreen."""
        pass

    def mMaxEvals(self):
        """Returns the maximum number of function evaluations."""
        return max(self.maxevals)

    def nbRuns(self):
        """Returns the number of runs."""
        return numpy.shape(self.evals)[1]-1

    def __parseHeader(self, header):
        """Extract data from a header line in an index entry."""
        
        # Split header into a list of key-value
        for attrname, attrvalue in parseinfo(header):
            try:
                setattr(self, self._attributes[attrname][0], attrvalue)
            except KeyError:
                warnings.warn('%s is an additional attribute.' % (attrname))
                setattr(self, attrname, attrvalue)
                self._extra_attr.append(attrname)
                # the attribute is set anyway, this might lead to some errors.
                continue
        #TODO: check that no compulsory attributes is missing:
        #dim, funcId, algId, precision
        return

    def pickle(self, outputdir=None, verbose=True):
        """Save this instance to a pickle file.

        Saves this instance to a pickle file. If not specified
        by argument outputdir, the location of the pickle is given by
        the location of the first index file associated to this
        instance.

        This method will overwrite existing files.

        """
        # the associated pickle file does not exist
        if not getattr(self, 'pickleFile', False):
            if outputdir is None:
                outputdir = os.path.split(self.indexFiles[0])[0] + '-pickle'
                if not os.path.isdir(outputdir):
                    try:
                        os.mkdir(outputdir)
                    except OSError:
                        print ('Could not create output directory % for pickle files'
                               % outputdir)
                        raise

            self.pickleFile = os.path.join(outputdir,
                                           'ppdata_f%03d_%02d.pickle'
                                            %(self.funcId, self.dim))

        if getattr(self, 'modsFromPickleVersion', True):
            try:
                f = open(self.pickleFile, 'w') # TODO: what if file already exist?
                pickle.dump(self, f)
                f.close()
                if verbose:
                    print 'Saved pickle in %s.' %(self.pickleFile)
            except IOError, (errno, strerror):
                print "I/O error(%s): %s" % (errno, strerror)
            except pickle.PicklingError:
                print "Could not pickle %s" %(self)

    def createDictInstance(self):
        """Returns a dictionary of the instances.

        The key is the instance Id, the value is a list of index.

        """
        dictinstance = {}
        for i in range(len(self.instancenumbers)):
            dictinstance.setdefault(self.instancenumbers[i], []).append(i)

        return dictinstance

    def createDictInstanceCount(self):
        """Returns a dictionary of the instances and their count.
        
        The keys are instance id and the values are the number of
        repetitions of such instance.
        
        """
        return dict((j, self.instancenumbers.count(j)) for j in set(self.instancenumbers))

    def splitByTrials(self, whichdata=None):
        """Splits the post-processed data arrays by trials.

        :keyword string whichdata: either 'evals' or 'funvals'
                                   determines the output
        :returns: this method returns dictionaries of arrays,
                  the key of the dictionaries being the instance id, the
                  value being a smaller post-processed data array
                  corresponding to the instance Id.
                  If whichdata is 'evals' then the array contains
                  function evaluations (1st column is alignment
                  targets).
                  Else if whichdata is 'funvals' then the output data
                  contains function values (1st column is alignment
                  budgets).
                  Otherwise this method returns a tuple of these two
                  arrays in this order.

        """
        dictinstance = self.createDictInstance()
        evals = {}
        funvals = {}

        for instanceid, idx in dictinstance.iteritems():
            evals[instanceid] = self.evals[:,
                                           numpy.ix_(list(i + 1 for i in idx))]
            funvals[instanceid] = self.funvals[:,
                                           numpy.ix_(list(i + 1 for i in idx))]

        if whichdata :
            if whichdata == 'evals':
                return evals
            elif whichdata == 'funvals':
                return funvals

        return (evals, funvals)

    def generateRLData(self, targets):
        """Determine the running lengths for reaching the target values.

        :keyword list targets: target function values of interest

        :returns: dict of arrays, one array for each target. Each array
                  are copied from attribute :py:attr:`evals` of
                  :py:class:`DataSetList`: first element is a target
                  function value smaller or equal to the element of
                  targets considered and has for other consecutive
                  elements the corresponding number of function
                  evaluations.

        """
        res = {}
        # expect evals to be sorted by decreasing function values
        it = reversed(self.evals)
        prevline = numpy.array([-numpy.inf] + [numpy.nan] * self.nbRuns())
        try:
            line = it.next()
        except StopIteration:
            # evals is an empty array
            return res #list()

        for t in sorted(targets):
            while line[0] <= t:
                prevline = line
                try:
                    line = it.next()
                except StopIteration:
                    break
            res[t] = prevline.copy()

        return res
        # return list(res[i] for i in targets)
        # alternative output sorted by targets
        
    def detAverageEvals(self, targets):
        """Determine the average number of f-evals for each target 
        in ``targets`` list. If a target is not reached within trial
        itrail, self.maxevals[itrial] contributes to the average. 
        
        Equals to sum(evals(target)) / nbruns. If ERT is finite 
        this equals to ERT * psucc == (sum(evals) / ntrials / psucc) * psucc, 
        where ERT, psucc, and evals are a function of target.  
          
        """
        assert not any(np.isnan(self.evals[:][0]))  # target value cannot be nan

        evalsums = []
        for evalrow in self.detEvals(targets):
            idxnan = np.isnan(evalrow)
            evalsums.append(sum(evalrow[idxnan==False]) + sum(self.maxevals[idxnan]))
        
        averages = np.array(evalsums, copy=False) / self.nbRuns()
            
        if do_assertion:
            assert all([(ert == np.inf and ps == 0) or toolsdivers.equals_approximately(ert,  averages[i] / ps)
                            for i, (ert, ps) in enumerate(zip(self.detERT(targets), self.detSuccessRates(targets)))]) 
        
        return averages
    
    def detSuccesses(self, targets):
        """Determine for each target in targets the number of 
        successful runs, keeping in return list the order in targets. 
        
            dset.SuccessRates(targets) == np.array(dset.detNbSuccesses(targets)) / dset.nbRuns()
            
        are the respective success rates. 
        
        """
        succ = []
        for evalrow in self.detEvals(targets, copy=False):
            assert len(evalrow) == self.nbRuns()
            succ.append(self.nbRuns() - sum(np.isnan(evalrow)))
        return succ

    def detSuccessRates(self, targets):
        """return a np.array with the success rate for each target 
        in targets, easiest target first
        
        """
        return np.array(self.detSuccesses(targets)) / float(self.nbRuns())

    def detERT(self, targets):
        """Determine the expected running time to reach target values.
        The value is numpy.inf, if the target was never reached. 

        :keyword list targets: target function values of interest

        :returns: list of expected running times (# f-evals) for the
                  respective targets.

        """
        res = {}
        tmparray = numpy.vstack((self.target, self.ert)).transpose()
        it = reversed(tmparray)
        # expect this array to be sorted by decreasing function values

        prevline = numpy.array([-numpy.inf, numpy.inf])
        try:
            line = it.next()
        except StopIteration:
            # evals is an empty array
            return list()

        for t in sorted(targets):
            while line[0] <= t:
                prevline = line
                try:
                    line = it.next()
                except StopIteration:
                    break
            res[t] = prevline.copy() # is copy necessary? Yes. 

        # Return a list of ERT corresponding to the input targets in
        # targets, sorted along targets
        return list(res[i][1] for i in targets)

    def detEvals(self, targets, copy=True):
        """returns len(targets) data rows self.evals[idata, 1:] each row with 
        the closest but not larger target such that self.evals[idata, 0] <= target, 
        and self.evals[idata-1, 0] > target or in the "limit" cases the
        idata==0 line or the line np.array(self.nbRuns() * [np.nan]). 
        
        Makes by default a copy of the data, however this might change in future. 
        
        """
        evalsrows = {}  # data rows, easiest target first
        idata = self.evals.shape[0] - 1  # current data line index 
        for target in sorted(targets):  # smallest most difficult target first
            if self.evals[-1, 0] > target:  # last entry is worse than target
                evalsrows[target] = np.array(self.nbRuns() * [np.nan])
                continue
            while idata > 0 and self.evals[idata - 1, 0] <= target:  # idata-1 line is good enough
                idata -= 1  # move up
            assert self.evals[idata, 0] <= target and (idata == 0 or self.evals[idata - 1, 0] > target)
            evalsrows[target] = self.evals[idata, 1:].copy() if copy else self.evals[idata, 1:]
            
        if do_assertion:
            assert all([all((np.isnan(evalsrows[target]) + (evalsrows[target] == self._detEvals2(targets)[i]))) for i, target in enumerate(targets)])
    
        return [evalsrows[t] for t in targets]
        
    def _detEvals2(self, targets):
        """Determine the number of evaluations to reach target values.

        :keyword seq or float targets: target precisions
        :returns: list of len(targets) values, each being an array of nbRuns FEs values

        """
        tmp = {}  # dict of eval-arrays (of size Ntrials), each entry for a given target
        # expect evals to be sorted by decreasing function values
        it = reversed(self.evals)
        prevline = numpy.array([-numpy.inf] + [numpy.nan] * self.nbRuns())
        try:
            line = it.next()
        except StopIteration:
            # evals is an empty array
            return tmp #list()

        for t in sorted(targets):
            while line[0] <= t:
                prevline = line
                try:
                    line = it.next()
                except StopIteration:
                    break
            tmp[t] = prevline.copy()

        return list(tmp[i][1:] for i in targets)

class DataSetList(list):
    """List of instances of :py:class:`DataSet`.

    This class implements some useful slicing functions.

    Also it will merge data of DataSet instances that are identical
    (according to function __eq__ of DataSet).

    """
    #Do not inherit from set because DataSet instances are mutable which means
    #they might change over time.

    def __init__(self, args=[], verbose=False):
        """Instantiate self from a list of inputs.

        :keyword list args: strings being either info file names, folder
                            containing info files or pickled data files.
        :keyword bool verbose: controls verbosity.

        Exceptions:
        Warning -- Unexpected user input.
        pickle.UnpicklingError

        """

        # TODO: initialize a DataSetList from a sequence of DataSet

        if not args:
            super(DataSetList, self).__init__()
            return

        if isinstance(args, basestring):
            args = [args]

        fnames = []
        for name in args:
            if os.path.isdir(name):
                fnames.extend(findfiles.main(name, verbose))
            else:
                fnames.append(name)

        for name in fnames: 
            if name.endswith('.info'):
                self.processIndexFile(name, verbose)
            elif name.endswith('.pickle'):
                try:
                    f = open(name,'r')
                    try:
                        entry = pickle.load(f)
                    except pickle.UnpicklingError:
                        print '%s could not be unpickled.' %(name)
                    f.close()
                    if verbose:
                        print 'Unpickled %s.' % (name)
                    if not hasattr(entry, 'instancenumbers'):
                        entry.instancenumbers = entry.itrials
                    # if not hasattr(entry, 'detAverageEvals')
                    self.append(entry)
                    #set_trace()
                except IOError, (errno, strerror):
                    print "I/O error(%s): %s" % (errno, strerror)

            else:
                warnings.warn('File or folder ' + name + ' not found. ' +
                              'Expecting as input argument either .info ' +
                              'file(s), .pickle file(s) or a folder ' +
                              'containing .info file(s).')

    def processIndexFile(self, indexFile, verbose=True):
        """Reads in an index file information on the different runs."""

        try:
            f = open(indexFile)
            if verbose:
                print 'Processing %s.' % indexFile

            # Read all data sets within one index file.
            nbLine = 1
            while True:
                try:
                    header = f.next()
                    while not header.strip(): # remove blank lines
                        header = f.next()
                        nbLine += 1
                    comment = f.next()
                    if not comment.startswith('%'):
                        warnings.warn('Entry in file %s at line %d is faulty: '
                                      % (indexFile, nbLine) +
                                      'it will be skipped.')
                        nbLine += 2
                        continue
                    data = f.next()
                    nbLine += 3
                    #TODO: check that something is not wrong with the 3 lines.
                    self.append(DataSet(header, comment, data, indexFile,
                                        verbose))
                except StopIteration:
                    break
            # Close index file
            f.close()

        except IOError:
            print 'Could not open %s.' % indexFile

    def append(self, o):
        """Redefines the append method to check for unicity."""

        if not isinstance(o, DataSet):
            raise Exception('Expect DataSet instance.')
        isFound = False
        for i in self:
            if i == o:
                isFound = True
                tmp = set(i.dataFiles).symmetric_difference(set(o.dataFiles))
                #Check if there are new data considered.
                if tmp:
                    i.dataFiles.extend(tmp)
                    i.indexFiles.extend(o.indexFiles)
                    i.funvals = alignArrayData(VArrayMultiReader([i.funvals, o.funvals]))
                    i.finalfunvals = numpy.r_[i.finalfunvals, o.finalfunvals]
                    i.evals = alignArrayData(HArrayMultiReader([i.evals, o.evals]))
                    i.maxevals = numpy.r_[i.maxevals, o.maxevals]
                    i.computeERTfromEvals()
                    if getattr(i, 'pickleFile', False):
                        i.modsFromPickleVersion = True

                    for j in dir(i):
                        if isinstance(getattr(i, j), list):
                            getattr(i, j).extend(getattr(o, j))

                else:
                    if getattr(i, 'pickleFile', False):
                        i.modsFromPickleVersion = False
                    elif getattr(o, 'pickleFile', False):
                        i.modsFromPickleVersion = False
                        i.pickleFile = o.pickleFile
                break
        if not isFound:
            list.append(self, o)

    def extend(self, o):
        """Extend with elements.

        This method is implemented to prevent problems since append was
        superseded. This method could be the origin of efficiency issue.

        """
        for i in o:
            self.append(i)

    def pickle(self, outputdir=None, verbose=True):
        """Loop over self to pickle each elements."""
        for i in self:
            i.pickle(outputdir, verbose)

    def dictByAlg(self):
        """Returns a dictionary of instances of this class by algorithm.

        The resulting dict uses algId and comment as keys and the
        corresponding slices as values.

        """
        d = {}
        for i in self:
            d.setdefault((i.algId, i.comment), DataSetList()).append(i)
        return d

    def dictByDim(self):
        """Returns a dictionary of instances of this class by dimensions.

        Returns a dictionary with dimension as keys and the
        corresponding slices as values.

        """
        d = {}
        for i in self:
            d.setdefault(i.dim, DataSetList()).append(i)
        return d

    def dictByFunc(self):
        """Returns a dictionary of instances of this class by functions.

        Returns a dictionary with the function id as keys and the
        corresponding slices as values.

        """
        d = {}
        for i in self:
            d.setdefault(i.funcId, DataSetList()).append(i)
        return d

    def dictByNoise(self):
        """Returns a dictionary splitting noisy and non-noisy entries."""
        sorted = {}
        for i in self:
            if i.funcId in range(1, 25):
                sorted.setdefault('noiselessall', DataSetList()).append(i)
            elif i.funcId in range(101, 131):
                sorted.setdefault('nzall', DataSetList()).append(i)
            else:
                warnings.warn('Unknown function id.')

        return sorted

    def dictByFuncGroup(self):
        """Returns a dictionary of instances of this class by function groups.

        The output dictionary has function group names as keys and the
        corresponding slices as values.

        """
        sorted = {}
        for i in self:
            if i.funcId in range(1, 6):
                sorted.setdefault('separ', DataSetList()).append(i)
            elif i.funcId in range(6, 10):
                sorted.setdefault('lcond', DataSetList()).append(i)
            elif i.funcId in range(10, 15):
                sorted.setdefault('hcond', DataSetList()).append(i)
            elif i.funcId in range(15, 20):
                sorted.setdefault('multi', DataSetList()).append(i)
            elif i.funcId in range(20, 25):
                sorted.setdefault('mult2', DataSetList()).append(i)
            elif i.funcId in range(101, 107):
                sorted.setdefault('nzmod', DataSetList()).append(i)
            elif i.funcId in range(107, 122):
                sorted.setdefault('nzsev', DataSetList()).append(i)
            elif i.funcId in range(122, 131):
                sorted.setdefault('nzsmm', DataSetList()).append(i)
            else:
                warnings.warn('Unknown function id.')

        return sorted

    def dictByParam(self, param):
        """Returns a dictionary of DataSetList by parameter values.

        :returns: a dictionary with values of parameter param as keys and
                  the corresponding slices of DataSetList as values.

        """

        d = {}
        for i in self:
            d.setdefault(getattr(i, param, None), DataSetList()).append(i)
        return d

    def info(self, opt='all'):
        """Display some information onscreen.

        :keyword string opt: changes size of output, can be 'all'
                             (default), 'short'

        """
        #TODO: do not integrate over dimension!!!

        if len(self) > 0:
            print '%d data set(s)' % (len(self))
            dictAlg = self.dictByAlg()
            algs = dictAlg.keys()
            algs.sort()
            sys.stdout.write('Algorithm(s): %s' % (algs[0][0]))
            for i in range(1, len(algs)):
                sys.stdout.write(', %s' % (algs[0][0]))
            sys.stdout.write('\n')
            dictDim = self.dictByDim()
            dimensions = dictDim.keys()
            dimensions.sort()
            sys.stdout.write('Dimension(s): %d' % (dimensions[0]))
            for i in range(1, len(dimensions)):
                sys.stdout.write(', %d' % (dimensions[i]))
            sys.stdout.write('\n')
            dictFun = self.dictByFunc()
            functions = dictFun.keys()
            functions.sort()
            print 'Function(s): %s' % (consecutiveNumbers(functions))
            maxevals = 0
            for i in self:
                maxevals = max(i.mMaxEvals(), maxevals)
            print 'Max evals: %d' % (maxevals)

            if opt == 'all':
                print 'Df      |     min       10      med       90      max'
                print '--------|--------------------------------------------'
                evals = list([] for i in dataSetTargets)
                for i in self:
                    tmpevals = i.detEvals(dataSetTargets)
                    for j in range(len(dataSetTargets)):
                        evals[j].extend(tmpevals[j])
                for i, j in enumerate(dataSetTargets): # never aggregate over dim...
                    tmp = toolsstats.prctile(evals[i], [0, 10, 50, 90, 100])
                    tmp2 = []
                    for k in tmp:
                        if not numpy.isfinite(k):
                            tmp2.append('%8f' % k)
                        else:
                            tmp2.append('%8d' % k)
                    print '%2.1e |%s' % (j, ' '.join(tmp2))

            # display distributions of final values
        else:
            print self

        # interested in algorithms, number of datasets, functions, dimensions
        # maxevals?, funvals?, success rate?


def parseinfoold(s):
    """Deprecated: Extract data from a header line in an index entry.

    Older but verified version of :py:meth:`parseinfo`

    The header line should be a string of comma-separated pairs of
    key=value, for instance: key = value, key = 'value'

    Keys should not use comma or quote characters.

    """
    # TODO should raise some kind of error...
    # Split header into a list of key-value
    list_kv = s.split(', ')

    # Loop over all elements in the list and extract the relevant data.
    # We loop backward to make sure that we did not split inside quotes.
    # It could happen when the key algId and the value is a string.
    p = re.compile('([^,=]+)=(.*)')
    list_kv.reverse()
    it = iter(list_kv)
    res = []
    while True:
        try:
            elem = it.next()
            tmp = p.match(elem)
            while not tmp:
                elem = it.next() + elem
                # add up elements of list_kv until we have a whole key = value

            elem0, elem1 = tmp.groups()
            elem0 = elem0.strip()
            elem1 = elem1.strip()
            if elem1.startswith('\'') and elem1.endswith('\''): # HACK
                elem1 = ('\'' + re.sub('([\'])', r'\\\1', elem1[1:-1]) + '\'')
            elem1 = ast.literal_eval(elem1)
            res.append((elem0, elem1))
        except StopIteration:
            break

    return res

def parseinfo(s):
    """Extract data from a header line in an index entry.

    Use a 'smarter' regular expression than :py:meth:`parseinfoold`.
    The header line should be a string of comma-separated pairs of
    key=value, for instance: key = value, key = 'value'

    Keys should not use comma or quote characters.

    """
    p = re.compile('\ *([^,=]+?)\ *=\ *(".+?"|\'.+?\'|[^,]+)\ *(?=,|$)')
    res = []
    for elem0, elem1 in p.findall(s):
        if elem1.startswith('\'') and elem1.endswith('\''): # HACK
            elem1 = ('\'' + re.sub(r'(?<!\\)(\')', r'\\\1', elem1[1:-1]) + '\'')
        elem1 = ast.literal_eval(elem1)
        res.append((elem0, elem1))
    return res

def processInputArgs(args, verbose=True):
    """Process command line arguments.

    Returns an instance of :py:class:`DataSetList`, a list of algorithms
    from a list of strings representing file and folder names. This
    command will operate folder-wise: one folder will correspond to an
    algorithm.

    It is recommended that if a folder listed in args contain both
    :file:`info` files and the associated :file:`pickle` files, they be
    kept in different locations for efficiency reasons.

    :keyword list args: string arguments for folder names
    :keyword bool verbose: controlling verbosity

    :returns (dsList, sortedAlgs, dictAlg):
      dsList
        is a list containing all DataSet instances, this is to
        prevent the regrouping done in instances of DataSetList
      dictAlg
        is a dictionary which associates algorithms to an instance
        of DataSetList,
      sortedAlgs
        is the sorted list of keys of dictAlg, the sorting is
        given by the input argument args.

    """
    dsList = list()
    sortedAlgs = list()
    dictAlg = {}
    for i in args:
        if os.path.isfile(i):
            txt = ('The post-processing cannot operate on the single file'
                   + ' %s.' % i)
            warnings.warn(txt)
            continue
        elif os.path.isdir(i):
            filelist = findfiles.main(i, verbose)
            #Do here any sorting or filtering necessary.
            #filelist = list(i for i in filelist if i.count('ppdata_f005'))
            tmpDsList = DataSetList(filelist, verbose)
            #Nota: findfiles will find all info AND pickle files in folder i.
            #No problem should arise if the info and pickle files have
            #redundant information. Only, the process could be more efficient
            #if pickle files were in a whole other location.
            dsList.extend(tmpDsList)
            #alg = os.path.split(i.rstrip(os.sep))[1]  # trailing slash or backslash
            #if alg == '':
            #    alg = os.path.split(os.path.split(i)[0])[1]
            alg = i
            print '  using:', alg

            # Prevent duplicates
            if all(i != alg for i in sortedAlgs):
                sortedAlgs.append(alg)
                dictAlg[alg] = tmpDsList
        else:
            txt = 'Input folder %s could not be found.' % i
            raise Exception(txt)

    return dsList, sortedAlgs, dictAlg

def dictAlgByDim(dictAlg):
    """Returns a dictionary with problem dimension as key.

    This method is meant to be used with an input argument which is a
    dictionary with algorithm names as keys and which has list of
    :py:class:`DataSet` instances as values.
    The resulting dictionary will have dimension as key and as values
    dictionaries with algorithm names as keys.

    """
    res = {}

    # get the set of problem dimensions
    dims = set()
    tmpdictAlg = {} # will store DataSet by alg and dim
    for alg, dsList in dictAlg.iteritems():
        tmp = dsList.dictByDim()
        tmpdictAlg[alg] = tmp
        dims |= set(tmp.keys())

    for d in dims:
        for alg in dictAlg:
            tmp = DataSetList()
            try:
                tmp = tmpdictAlg[alg][d]
            except KeyError:
                txt = ('No data for algorithm %s in %d-D.'
                       % (alg, d))
                warnings.warn(txt)

            if res.setdefault(d, {}).has_key(alg):
                txt = ('Duplicate data for algorithm %s in %d-D.'
                       % (alg, d))
                warnings.warn(txt)

            res.setdefault(d, {}).setdefault(alg, tmp)
            # Only the first data for a given algorithm in a given dimension

    #for alg, dsList in dictAlg.iteritems():
        #for i in dsList:
            #res.setdefault(i.dim, {}).setdefault(alg, DataSetList()).append(i)

    return res

def dictAlgByDim2(dictAlg):
    """Returns a dictionary with problem dimension as key.

    The difference with :py:func:`dictAlgByDim` is that there is an
    entry for each algorithms even if the resulting
    :py:class:`DataSetList` is empty.

    This function is meant to be used with an input argument which is a
    dictionary with algorithm names as keys and which has list of
    :py:class:`DataSet` instances as values.
    The resulting dictionary will have dimension as key and as values
    dictionaries with algorithm names as keys.

    """
    res = {}

    for alg, dsList in dictAlg.iteritems():
        for i in dsList:
            res.setdefault(i.dim, {}).setdefault(alg, DataSetList()).append(i)

    return res

def dictAlgByFun(dictAlg):
    """Returns a dictionary with function id as key.

    This method is meant to be used with an input argument which is a
    dictionary with algorithm names as keys and which has list of
    :py:class:`DataSet` instances as values.
    The resulting dictionary will have function id as key and as values
    dictionaries with algorithm names as keys.

    """
    res = {}
    funcs = set()
    tmpdictAlg = {}
    for alg, dsList in dictAlg.iteritems():
        tmp = dsList.dictByFunc()
        tmpdictAlg[alg] = tmp
        funcs |= set(tmp.keys())

    for f in funcs:
        for alg in dictAlg:
            tmp = DataSetList()
            try:
                tmp = tmpdictAlg[alg][f]
            except KeyError:
                txt = ('No data for algorithm %s on function %d.'
                       % (alg, f)) # This message is misleading.
                warnings.warn(txt)

            if res.setdefault(f, {}).has_key(alg):
                txt = ('Duplicate data for algorithm %s on function %d-D.'
                       % (alg, f))
                warnings.warn(txt)

            res.setdefault(f, {}).setdefault(alg, tmp)
            # Only the first data for a given algorithm in a given dimension

    return res

def dictAlgByNoi(dictAlg):
    """Returns a dictionary with noise group as key.

    This method is meant to be used with an input argument which is a
    dictionary with algorithm names as keys and which has list of
    :py:class:`DataSet` instances as values.
    The resulting dictionary will have a string denoting the noise group
    ('noiselessall' or 'nzall') and as values dictionaries with
    algorithm names as keys.

    """
    res = {}
    ng = set()
    tmpdictAlg = {}
    for alg, dsList in dictAlg.iteritems():
        tmp = dsList.dictByNoise()
        tmpdictAlg[alg] = tmp
        ng |= set(tmp.keys())

    for n in ng:
        stmp = ''
        if n == 'nzall':
            stmp = 'noisy'
        elif n == 'noiselessall':
            stmp = 'noiseless'

        for alg in dictAlg:
            tmp = DataSetList()
            try:
                tmp = tmpdictAlg[alg][n]
            except KeyError:
                txt = ('No data for algorithm %s on %s function.'
                       % (alg, stmp))
                warnings.warn(txt)

            if res.setdefault(n, {}).has_key(alg):
                txt = ('Duplicate data for algorithm %s on %s functions.'
                       % (alg, stmp))
                warnings.warn(txt)

            res.setdefault(n, {}).setdefault(alg, tmp)
            # Only the first data for a given algorithm in a given dimension

    return res

def dictAlgByFuncGroup(dictAlg):
    """Returns a dictionary with function group as key.

    This method is meant to be used with an input argument which is a
    dictionary with algorithm names as keys and which has list of
    :py:class:`DataSet` instances as values.
    The resulting dictionary will have a string denoting the function
    group and as values dictionaries with algorithm names as keys.

    """
    res = {}
    fg = set()
    tmpdictAlg = {}
    for alg, dsList in dictAlg.iteritems():
        tmp = dsList.dictByFuncGroup()
        tmpdictAlg[alg] = tmp
        fg |= set(tmp.keys())

    for g in fg:
        for alg in dictAlg:
            tmp = DataSetList()
            try:
                tmp = tmpdictAlg[alg][g]
            except KeyError:
                txt = ('No data for algorithm %s on %s functions.'
                       % (alg, g))
                warnings.warn(txt)

            if res.setdefault(g, {}).has_key(alg):
                txt = ('Duplicate data for algorithm %s on %s functions.'
                       % (alg, g))
                warnings.warn(txt)

            res.setdefault(g, {}).setdefault(alg, tmp)
            # Only the first data for a given algorithm in a given dimension

    return res

# TODO: these functions should go to different modules. E.g. tools.py and toolsstats.py renamed as stats.py

