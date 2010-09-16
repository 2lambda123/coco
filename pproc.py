#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Helper routines for read index files.
   Defines class DataSet, unit element in the post-processing and the list
   of instances of DataSet: DataSetList.

"""

from __future__ import absolute_import

import os
import re
import pickle
import warnings
from pdb import set_trace
import numpy
from bbob_pproc import findfiles, bootstrap
from bbob_pproc.readalign import split, alignData, HMultiReader, VMultiReader
from bbob_pproc.readalign import HArrayMultiReader, VArrayMultiReader, alignArrayData

# CLASS DEFINITIONS
class DataSet:
    """Unit element for the BBOB post-processing.

    One unit element corresponds to data with given algId and comment, a
    funcId, and dimension.

    Class attributes:
        funcId -- function Id (integer)
        dim -- dimension (integer)
        indexFiles -- associated index files (list of strings)
        dataFiles -- associated data files (list of strings)
        comment -- comment for the setting (string)
        targetFuncValue -- target function value (float)
        algId -- algorithm name (string)
        evals -- collected data aligned by function values (array)
        funvals -- collected data aligned by function evaluations (array)
        nbRuns -- number of runs (integer)
        maxevals -- maximum number of function evaluations (array)
        finalfunvals -- final function values (array)
        readmaxevals -- maximum number of function evaluations read from index
                        file (array)
        readfinalFminusFtarget -- final function values - ftarget read from
                                  index file (array)
        pickleFile -- associated pickle file name (string)
        target -- target function values attained at least by one trial (array)
        ert -- ert for reaching the target function values in target (array)
        itrials -- list of numbers corresponding to the instances of the test
           function considered (list of int)
        isFinalized -- list of bool for if runs were properly finalized

    evals and funvals are arrays of data collected from N data sets. Both have
    the same format: zero-th column is the value on which the data of a row is
    aligned, the N subsequent columns are either the numbers of function
    evaluations for evals or function values for funvals.
    """

    # TODO: unit element of the post-processing: one algorithm, one problem

    # Private attribute used for the parsing of info files.
    __attributes = {'funcId': ('funcId', int), 'DIM': ('dim',int),
                    'Precision': ('precision', float), 'Fopt': ('fopt', float),
                    'targetFuncValue': ('targetFuncValue', float),
                    'algId': ('algId', str)}

    def __init__(self, header, comment, data, indexfile, verbose=True):
        """Instantiate a DataSet.

        The first three input argument corresponds to three consecutive lines
        of an index file (info extension).

        Keyword argument:
        header -- string presenting the information of the experiment
        comment -- more information on the experiment
        data -- information on the runs of the experiment
        indexfile -- string for the file name from where the information come
        verbose -- controls verbosity
        """

        # Extract information from the header line.
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

        self.indexFiles = [indexfile]
        self.dataFiles = []
        self.itrials = []
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
                    self.itrials.append(int(elem))
                    # In this case, what should we do? Either we try to process
                    # the corresponding data anyway or we leave it out.
                    # For now we leave it in.
                    self.isFinalized.append(False)
                    warnings.warn('Caught an ill-finalized run in %s for %s'
                                  % (indexfile, self.dataFiles[-1]))
                    self.readmaxevals.append(0)
                    self.readfinalFminusFtarget.append(numpy.inf)
                else:
                    itrial, info = elem.split(':', 1)
                    self.itrials.append(int(itrial))
                    self.isFinalized.append(True)
                    readmaxevals, readfinalf = info.split('|', 1)
                    self.readmaxevals.append(int(readmaxevals))
                    self.readfinalFminusFtarget.append(float(readfinalf))

        if verbose:
            print "%s" % self.__repr__()

        # Treat successively the data in dat and tdat files:
        # put into variable dataFiles the files where to look for data
        dataFiles = list(i.rsplit('.', 1)[0] + '.dat' for i in self.dataFiles)
        data = HMultiReader(split(dataFiles))
        if verbose:
            print ("Processing %s: %d/%d trials found."
                   % (dataFiles, len(data), len(self.itrials)))
        (adata, maxevals, finalfunvals) = alignData(data)
        self.evals = adata
        try:
            for i in range(len(maxevals)):
                self.maxevals[i] = max(maxevals[i], self.maxevals[i])
                self.finalfunvals[i] = min(finalfunvals[i], self.finalfunvals[i])
        except AttributeError:
            self.maxevals = maxevals
            self.finalfunvals = finalfunvals

        dataFiles = list(i.rsplit('.', 1)[0] + '.tdat' for i in self.dataFiles)
        data = VMultiReader(split(dataFiles))
        if verbose:
            print ("Processing %s: %d/%d trials found."
                   % (dataFiles, len(data), len(self.itrials)))
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
            txt = ("There is a difference between the maxevals in the *.info "
                   + "file and in the data files.")
            warnings.warn(txt)

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
            self.ert.append(bootstrap.sp(data, issuccessful=succ)[0])
            self.target.append(i[0])

        self.ert = numpy.array(self.ert)
        self.target = numpy.array(self.target)

    def __eq__(self, other):
        """Compare indexEntry instances."""
        return (self.__class__ is other.__class__ and
                self.funcId == other.funcId and
                self.dim == other.dim and
                #self.precision == other.precision and
                self.algId == other.algId and
                self.comment == other.comment)

    def __ne__(self,other):
        return not self.__eq__(other)

    def __repr__(self):
        return ('{alg: %s, F%d, dim: %d}'
                % (self.algId, self.funcId, self.dim))

    def mMaxEvals(self):
        """Returns the maximum number of function evaluations."""
        return max(self.maxevals)

    def nbRuns(self):
        """Returns the number of runs."""
        return numpy.shape(self.funvals)[1]-1

    def __parseHeader(self, header):
        """Extract data from a header line in an index entry."""

        # Split header into a list of key-value
        headerList = header.split(', ')

        # Loop over all elements in the list and extract the relevant data.
        # We loop backward to make sure that we did not split inside quotes.
        # It could happen when the key algId and the value is a string.
        p = re.compile('[^,=]+ = .*')
        headerList.reverse()
        it = iter(headerList)
        while True:
            try:
                elem = it.next()
                while not p.match(elem):
                    elem = it.next() + elem

                elemList = elem.split('=')
                #A key name is not expected to contain the string '='
                elemFirst = elemList[0].strip()
                elemSecond = ''.join(elemList[1:]).strip().strip('\'')
                #Here we strip quotes instead of using them to differentiate
                #between data types.

                try:
                    setattr(self, self.__attributes[elemFirst][0],
                            self.__attributes[elemFirst][1](elemSecond))
                except KeyError:
                    warnings.warn('%s is not an expected ' % (elemFirst) +
                                  'attribute.')
                    continue

            except StopIteration:
                break

        #TODO: check that no compulsory attributes is missing:
        #dim, funcId, algId, precision

        return

    def pickle(self, outputdir=None, verbose=True):
        """Save DataSet instance to a pickle file.

        Saves the instance of DataSet to a pickle file. If not specified by
        argument outputdir, the location of the pickle is given by the location
        of the first index file associated to the DataSet.
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

        The key is the instance id, the value is a list of index.
        """

        dictinstance = {}
        for i in range(len(self.itrials)):
            dictinstance.setdefault(self.itrials[i], []).append(i)

        return dictinstance


    def splitByTrials(self, whichdata=None):
        """Splits the post-processed data arrays by trials.

        Returns a two-element list of dictionaries of arrays, the key of the
        dictionary being the instance id, the value being a smaller
        post-processed data array corresponding to the instance id.
        """

        dictinstance = self.createDictInstance()
        evals = {}
        funvals = {}

        for instanceid, idx in iteritems(dictinstance):
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

        Keyword arguments:
        targets -- list of target function values of interest

        Output:
        dict of arrays, one array has for first element a target function value
        smaller or equal to the element of inputtargets considered and has for
        other consecutive elements the corresponding number of function
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

    def detERT(self, targets):
        """Determine the expected running time for reaching target values.

        Keyword arguments:
        targets -- list of target function values of interest

        Output:
        list of expected running times corresponding to the targets
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
            res[t] = prevline.copy() # is copy necessary?

        # Return a list of ERT corresponding to the input targets in
        # targets, sorted along targets
        return list(res[i][1] for i in targets)

    def detEvals(self, targets):
        """Determine the number of evaluations for reaching target values.

        Keyword arguments:
        targets -- list of target function values of interest

        Output:
        list of arrays each corresponding to one value in targets
        """

        tmp = {}
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
    """List of instances of DataSet objects with some useful slicing functions.

    Will merge data of DataSet instances that are identical (according to
    function __eq__ of DataSet).
    """

    #Do not inherit from set because DataSet instances are mutable which means
    #they might change over time.

    def __init__(self, args=[], verbose=True):
        """Instantiate self from a list of inputs.

        Keyword arguments:
        args -- list of strings being either info file names, folder containing
                info files or pickled data files.
        verbose -- controls verbosity.

        Exception:
        Warning -- Unexpected user input.
        pickle.UnpicklingError
        """

        # TODO: initialize a DataSetList from a sequence of DataSet

        if not args:
            super(DataSetList, self).__init__()
            return

        if isinstance(args, basestring):
            args = [args]

        tmp = []
        for i in args:
            if os.path.isdir(i):
                tmp.extend(findfiles.main(i, verbose))
            else:
                tmp.append(i)

        for i in tmp:
            if i.endswith('.info'):
                self.processIndexFile(i, verbose)
            elif i.endswith('.pickle'):
                try:
                    f = open(i,'r')
                    try:
                        entry = pickle.load(f)
                    except pickle.UnpicklingError:
                        print '%s could not be unpickled.' %(i)
                    f.close()
                    if verbose:
                        print 'Unpickled %s.' % (i)
                    self.append(entry)
                    #set_trace()
                except IOError, (errno, strerror):
                    print "I/O error(%s): %s" % (errno, strerror)

            else:
                warnings.warn('File or folder ' + i + ' not found. ' +
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
            indexpath = os.path.split(indexFile)[0]
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
                    tmpline = f.next()
                    nbLine += 3
                    #TODO: check that something is not wrong with the 3 lines.

                    # Add the path to the index file to the file names
                    data = []
                    for i in tmpline.split(', '):
                        if i.endswith('dat'): #filenames
                            data.append(os.path.join(indexpath, i))
                        else: #other information
                            data.append(i)
                    data = ', '.join(data)
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
            raise Exception()
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
        """Extend a DataSetList with elements.

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
        """Returns a dictionary of DataSetList instances by algorithm.

        The resulting dict uses algId and comment as keys and the corresponding
        slices of DataSetList as values.
        """

        d = {}
        for i in self:
            d.setdefault((i.algId, i.comment), DataSetList()).append(i)
        return d

    def dictByDim(self):
        """Returns a dictionary of DataSetList instances by dimensions.

        Returns a dictionary with dimension as keys and the corresponding
        slices of DataSetList as values.
        """

        d = {}
        for i in self:
            d.setdefault(i.dim, DataSetList()).append(i)
        return d

    def dictByFunc(self):
        """Returns a dictionary of DataSetList instances by functions.

        Returns a dictionary with the function id as keys and the
        corresponding slices of DataSetList as values.
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
        """Returns a dictionary of DataSetList instances by function groups.

        Returns a dictionary with function group names as keys and the
        corresponding slices of DataSetList as values.
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

def processInputArgs(args, verbose=True):
    """Process command line arguments into data useable by bbob_pproc scripts.

    Returns an instance of DataSetList, a list of algorithms from
    a list of strings representing file and folder names.
    This command will operate folder-wise: one folder will correspond to an
    algorithm.
    It is recommended that if a folder listed in args contain both info files
    and the associated pickle files, they be kept in different locations for
    efficiency reasons.

    Keyword arguments:
      args -- list of string arguments for folder names
      verbose -- bool controlling verbosity

    Returns: (dsList, sortedAlgs, dictAlg), where
      dsList is a list containing all DataSet instances, this is to prevent the
        regrouping done in instances of DataSetList
      dictAlg is a dictionary which associates algorithms to an instance of
        DataSetList,
      sortedAlgs is the sorted list of keys of dictAlg, the sorting is given
        by the input argument args.
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
    dictionary with algorithm names as keys and which has list of DataSet
    instances as values.
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

    This method is meant to be used with an input argument which is a
    dictionary with algorithm names as keys and which has list of DataSet
    instances as values.
    The resulting dictionary will have dimension as key and as values
    dictionaries with algorithm names as keys.
    The difference with dictAlgByDim is that there is an entry for each
    algorithms even if the resulting DataSetList is empty...
    """

    res = {}

    for alg, dsList in dictAlg.iteritems():
        for i in dsList:
            res.setdefault(i.dim, {}).setdefault(alg, DataSetList()).append(i)

    return res

def dictAlgByFun(dictAlg):
    """Returns a dictionary with function id as key.

    This method is meant to be used with an input argument which is a
    dictionary with algorithm names as keys and which has list of DataSet
    instances as values.
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
    dictionary with algorithm names as keys and which has list of DataSet
    instances as values.
    The resulting dictionary will have a string denoting the noise group
    ('noiselessall' or 'nzall') and as values dictionaries with algorithm names
    as keys.
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
    dictionary with algorithm names as keys and which has list of DataSet
    instances as values.
    The resulting dictionary will have a string denoting the function group
    and as values dictionaries with algorithm names as keys.
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

def significancetest(entry0, entry1, targets):
    """Compute the rank sum test between two data sets for given target values.

    For a given target function value, the performances of two algorithms
    are compared. The result of a significance test is computed on the number
    of function evaluations for reaching the target and/or function values.

    Keyword arguments:
      entry0 -- data set 0
      entry1 -- data set 1
      targets -- list of target function values

    Returns:
    list of (z, p) for each target function values in input argument targets.
    z and p are values returned by the ranksums method.
    """

    res = []
    evals = []
    bestalgs = []
    isBestAlg = False
    # one of the entry is an instance of BestAlgDataSet
    for entry in (entry0, entry1):
        tmp = entry.detEvals(targets)
        if not entry.__dict__.has_key('funvals'):
            #for i, j in enumerate(tmp[0]):
                #if numpy.isnan(j).all():
                    #tmp[0][i] = numpy.array([numpy.nan]*len(entry.bestfinalfunvals))
            #Make sure that the length of elements of tmp[0] is the same as
            #that of the associated function values
            evals.append(tmp[0])
            bestalgs.append(tmp[1])
            isBestAlg = True
        else:
            evals.append(tmp)
            bestalgs.append(None)

    for i in range(len(targets)):
        # 1. Determine FE_umin
        FE_umin = numpy.inf

        # if there is at least one unsuccessful run
        if (numpy.isnan(evals[0][i]).any() or numpy.isnan(evals[1][i]).any()):
            fvalues = []
            if isBestAlg:
                for j, entry in enumerate((entry0, entry1)):
                    # if best alg entry
                    if isinstance(entry.finalfunvals, dict):
                        alg = bestalgs[j][i]
                        if alg is None:
                            tmpfvalues = entry.bestfinalfunvals
                        else:
                            tmpfvalues = entry.finalfunvals[alg]
                    else:
                        unsucc = numpy.isnan(evals[j][i])
                        if unsucc.any():
                            FE_umin = min(entry.maxevals[unsucc])
                        else:
                            FE_umin = numpy.inf
                        # Determine the function values for FE_umin
                        tmpfvalues = numpy.array([numpy.inf] * entry.nbRuns())
                        for curline in entry.funvals:
                            # only works because the funvals are monotonous
                            if curline[0] > FE_umin:
                                break
                            prevline = curline[1:]
                        tmpfvalues = prevline.copy()
                        #tmpfvalues = entry.finalfunvals
                        #if (tmpfvalues != entry.finalfunvals).any():
                            #set_trace()
                    fvalues.append(tmpfvalues)
            else:
                # 1) find min_{both algorithms}(conducted FEvals in
                # unsuccessful trials) =: FE_umin
                FE_umin = numpy.inf
                if numpy.isnan(evals[0][i]).any() or numpy.isnan(evals[1][i]).any():
                    FE = []
                    for j, entry in enumerate((entry0, entry1)):
                        unsucc = numpy.isnan(evals[j][i])
                        if unsucc.any():
                            tmpfe = min(entry.maxevals[unsucc])
                        else:
                            tmpfe = numpy.inf
                        FE.append(tmpfe)
                    FE_umin = min(FE)

                    # Determine the function values for FE_umin
                    fvalues = []
                    for j, entry in enumerate((entry0, entry1)):
                        prevline = numpy.array([numpy.inf] * entry.nbRuns())
                        for curline in entry.funvals:
                            # only works because the funvals are monotonous
                            if curline[0] > FE_umin:
                                break
                            prevline = curline[1:]
                        fvalues.append(prevline)

        # 2. 3. 4. Collect data for the significance test:
        curdata = []
        for j, entry in enumerate((entry0, entry1)):
            tmp = evals[j][i].copy()
            idx = numpy.isnan(tmp) + (tmp > FE_umin)
            tmp = numpy.power(tmp, -1.)
            if idx.any():
                tmp[idx] = -fvalues[j][idx]
            curdata.append(tmp)

        tmpres = bootstrap.ranksums(curdata[0], curdata[1])
        if isBestAlg:
            tmpres = list(tmpres)
            tmpres[1] /= 2.

        res.append(tmpres)

    return res
