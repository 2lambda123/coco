#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Generate performance scaling figures.

The figures show the scaling of the performance in terms of ERT w.r.t.
dimensionality on a log-log scale. On the y-axis, data is represented as
a number of function evaluations divided by dimension, this is in order
to compare at a glance with a linear scaling for which ERT is
proportional to the dimension and would therefore be represented by a
horizontal line in the figure.

Crosses (+) give the median number of function evaluations of successful
trials divided by dimension for the smallest *reached* target function
value.
Numbers indicate the number of succesfull runs for the smallest
*reached* target.
If the smallest target function value (1e-8) is not reached for a given
dimension, crosses (x) give the average number of overall conducted
function evaluations divided by the dimension.

Horizontal lines indicate linear scaling with the dimension, additional
grid lines show quadratic and cubic scaling.
The thick light line with diamond markers shows the single best results
from BBOB-2009 for df = 1e-8.

**Example**

.. plot::
    :width: 50%
    
    import urllib
    import tarfile
    import glob
    from pylab import *
    
    import bbob_pproc as bb
    
    # Collect and unarchive data (3.4MB)
    dataurl = 'http://coco.lri.fr/BBOB2009/pythondata/BIPOP-CMA-ES.tar.gz'
    filename, headers = urllib.urlretrieve(dataurl)
    archivefile = tarfile.open(filename)
    archivefile.extractall()
    
    # Scaling figure
    ds = bb.load(glob.glob('BBOB2009pythondata/BIPOP-CMA-ES/ppdata_f002_*.pickle'))
    figure()
    bb.ppfigdim.plot(ds)
    bb.ppfigdim.beautify()
    bb.ppfigdim.plotBest2009(2) # plot BBOB 2009 best algorithm on fun 2

"""

import os
import sys
import matplotlib.pyplot as plt
import numpy
from pdb import set_trace
from bbob_pproc import bootstrap, bestalg
from bbob_pproc.ppfig import saveFigure, groupByRange

colors = ('k', 'b', 'c', 'g', 'y', 'm', 'r', 'k', 'k', 'c', 'r', 'm')  # sort of rainbow style
styles = [{'color': 'k', 'marker': 'o', 'markeredgecolor': 'k'},
          {'color': 'b'},
          {'color': 'c', 'marker': 'v', 'markeredgecolor': 'c'},
          {'color': 'g'},
          {'color': 'y', 'marker': '^', 'markeredgecolor': 'y'},
          {'color': 'm'},
          {'color': 'r', 'marker': 's', 'markeredgecolor': 'r'}] # sort of rainbow style
refcolor = 'wheat'

# should correspond with the colors in pprldistr.
dimsBBOB = (2, 3, 5, 10, 20, 40)

#Get benchmark short infos.
funInfos = {}
figformat = ('eps', 'pdf') # Controls the output when using the main method
isBenchmarkinfosFound = True
infofile = os.path.join(os.path.split(__file__)[0], 'benchmarkshortinfos.txt')

try:
    f = open(infofile,'r')
    for line in f:
        if len(line) == 0 or line.startswith('%') or line.isspace() :
            continue
        funcId, funcInfo = line[0:-1].split(None,1)
        funInfos[int(funcId)] = funcId + ' ' + funcInfo
    f.close()
except IOError, (errno, strerror):
    print "I/O error(%s): %s" % (errno, strerror)
    isBenchmarkinfosFound = False
    print 'Could not find file', infofile, \
          'Titles in figures will not be displayed.'


def beautify(axesLabel=True):
    """Customize figure presentation.
    
    Uses information from :file:`benchmarkshortinfos.txt` for figure
    title. 
    
    """

    # Input checking

    # Get axis handle and set scale for each axis
    axisHandle = plt.gca()
    axisHandle.set_xscale("log")
    axisHandle.set_yscale("log")

    # Grid options
    axisHandle.grid(True)

    ymin, ymax = plt.ylim()

    # linear and quadratic "grid"
    #plt.plot((2,200), (1,1e2), 'k:')    # TODO: this should be done before the real lines are plotted? 
    #plt.plot((2,200), (1,1e4), 'k:')
    #plt.plot((2,200), (1e3,1e5), 'k:')  
    #plt.plot((2,200), (1e3,1e7), 'k:')
    #plt.plot((2,200), (1e6,1e8), 'k:')  
    #plt.plot((2,200), (1e6,1e10), 'k:')

    # quadratic and cubic "grid"
    plt.plot((2,200), (1, 1e2), 'k:')    # TODO: this should be done before the real lines are plotted? 
    plt.plot((2,200), (1, 1e4), 'k:')
    plt.plot((2,200), (1e3, 1e5), 'k:')  
    plt.plot((2,200), (1e3, 1e7), 'k:')
    plt.plot((2,200), (1e6, 1e8), 'k:')  
    plt.plot((2,200), (1e6, 1e10), 'k:')

    # axes limites
    plt.xlim(1.8, 45)                # TODO should become input arg?
    plt.ylim(ymin=10**-0.2, ymax=ymax) # Set back the default maximum.

    # ticks on axes
    #axisHandle.invert_xaxis()
    dimticklist = (2, 3, 4, 5, 10, 20, 40)  # TODO: should become input arg at some point? 
    dimannlist = (2, 3, '', 5, 10, 20, 40)  # TODO: should become input arg at some point? 
    # TODO: All these should depend on one given input (xlim, ylim)

    axisHandle.set_xticks(dimticklist)
    axisHandle.set_xticklabels([str(n) for n in dimannlist])

    tmp = axisHandle.get_yticks()
    tmp2 = []
    for i in tmp:
        tmp2.append('%d' % round(numpy.log10(i)))
    axisHandle.set_yticklabels(tmp2)
    if axesLabel:
        plt.xlabel('Dimension')
        plt.ylabel('Run Lengths / Dimension')

def generateData(dataSet, targetFuncValue):
    """Computes an array of results to be plotted.
    
    :returns: (ert, number of success, success rate, total number of
               function evaluations, median of successful runs).

    """
    res = []
    data = []

    it = iter(reversed(dataSet.evals))
    i = it.next()
    prev = numpy.array([numpy.nan] * len(i))

    while i[0] <= targetFuncValue:
        prev = i
        try:
            i = it.next()
        except StopIteration:
            break

    data = prev[1:].copy() # keep only the number of function evaluations.
    succ = (numpy.isnan(data) == False)
    if succ.any():
        med = bootstrap.prctile(data[succ], 50)[0]
        #Line above was modified at rev 3050 to make sure that we consider only
        #successful trials in the median
    else:
        med = numpy.nan

    data[numpy.isnan(data)] = dataSet.maxevals[numpy.isnan(data)]

    res = []
    res.extend(bootstrap.sp(data, issuccessful=succ, allowinf=False))
    res.append(numpy.mean(data)) #mean(FE)
    res.append(med)

    return numpy.array(res)

def plot(dsList, _valuesOfInterest=(10, 1, 1e-1, 1e-2, 1e-3, 1e-5, 1e-8)):
    """From a DataSetList, plot a figure of ERT/dim vs dim.
    
    There will be one set of graphs per function represented in the
    input data sets. Most usually the data sets of different functions
    will be represented separately.
    
    :param DataSetList dsList: data sets
    :param seq _valuesOfInterest: target precisions, there might be as
                                  many graphs as there are elements in
                                  this input
    :returns: handles

    """
    dictFunc = dsList.dictByFunc()
    res = []

    for func in dictFunc:
        dictFunc[func] = dictFunc[func].dictByDim()
        dimensions = sorted(dictFunc[func])

        #legend = []
        line = []
        try:
            valuesOfInterest = list(j[func] for j in _valuesOfInterest)
        except TypeError:
            valuesOfInterest = list(_valuesOfInterest)
        valuesOfInterest.sort(reverse=True)
        mediandata = {}
        for i in range(len(valuesOfInterest)):
            succ = []
            unsucc = []
            displaynumber = []
            data = []
            #Collect data that have the same function and different dimension.
            for dim in dimensions:
                tmp = generateData(dictFunc[func][dim][0],
                                   valuesOfInterest[i])
                #data.append(numpy.append(dim, tmp))
                if tmp[2] > 0: #Number of success is larger than 0
                    succ.append(numpy.append(dim, tmp))
                    if tmp[2] < dictFunc[func][dim][0].nbRuns():
                        displaynumber.append((dim, tmp[0], tmp[2]))
                    mediandata[dim] = (i, tmp[-1])
                    unsucc.append(numpy.append(dim, numpy.nan))
                else:
                    unsucc.append(numpy.append(dim, tmp[-2]))

            if succ:
                tmp = numpy.vstack(succ)
                #ERT
                res.extend(plt.plot(tmp[:, 0], tmp[:, 1]/tmp[:, 0],
                           markersize=20, **styles[i]))

            # To have the legend displayed whatever happens with the data.
            res.extend(plt.plot([], [], markersize=10,
                                label=' %+d' % (numpy.log10(valuesOfInterest[i])),
                                **styles[i]))

        #Only for the last target function value
        if unsucc:
            tmp = numpy.vstack(unsucc) # tmp[:, 0] needs to be sorted!
            res.extend(plt.plot(tmp[:, 0], tmp[:, 1]/tmp[:, 0],
                       color=styles[len(valuesOfInterest)-1]['color'],
                       marker='x', markersize=20))

        #median
        if mediandata:
            for i, tm in mediandata.iteritems():
                plt.plot((i, ), (tm[1]/i, ), color=styles[tm[0]]['color'],
                         linestyle='', marker='+', markersize=30,
                         markeredgewidth=5, zorder=-1)

        a = plt.gca()
        # the displaynumber is emptied for each new target precision
        # therefore the displaynumber displayed below correspond to the
        # last target (must be the hardest)
        if displaynumber: #displayed only for the smallest valuesOfInterest
            for j in displaynumber:
                # the 1.85 factor is a shift up for the digits 
                plt.text(j[0], j[1] * 1.85 / j[0], "%.0f" % j[2], axes=a,
                         horizontalalignment="center",
                         verticalalignment="bottom")

    return res

def plotBest2009(func, target=1e-8):
    """Add graph of the BBOB-2009 virtual best algorithm."""
    if not bestalg.bestalgentries2009:
        bestalg.loadBBOB2009()
    bestalgdata = []
    for d in dimsBBOB:
        entry = bestalg.bestalgentries2009[(d, func)]
        tmp = entry.detERT([target])[0]
        if not numpy.isinf(tmp):
            bestalgdata.append(tmp / d)
        else:
            bestalgdata.append(None)
    res = plt.plot(dimsBBOB, bestalgdata, color=refcolor, linewidth=10,
                   marker='d', markersize=25, markeredgecolor=refcolor,
                   zorder=-2)
    return res

def main(dsList, _valuesOfInterest, outputdir, verbose=True):
    """From a DataSetList, returns a convergence and ERT/dim figure vs dim.
    
    Uses data of BBOB 2009 (:py:mod:`bbob_pproc.bestalg`).
    
    :param DataSetList dsList: data sets
    :param seq _valuesOfInterest: target precisions, there might be as
                                  many graphs as there are elements in
                                  this input
    :param string outputdir: output directory
    :param bool verbose: controls verbosity
    
    """

    #plt.rc("axes", labelsize=20, titlesize=24)
    #plt.rc("xtick", labelsize=20)
    #plt.rc("ytick", labelsize=20)
    #plt.rc("font", size=20)
    #plt.rc("legend", fontsize=20)

    if not bestalg.bestalgentries2009:
        bestalg.loadBBOB2009()

    dictFunc = dsList.dictByFunc()

    for func in dictFunc:
        plot(dictFunc[func], _valuesOfInterest)        
        beautify(axesLabel=False)
        if func in (1, 24, 101, 130):
            plt.legend(loc="best")
        if isBenchmarkinfosFound:
            plt.gca().set_title(funInfos[func])
        plotBest2009(func)
        filename = os.path.join(outputdir,'ppfigdim_f%03d' % (func))
        saveFigure(filename, figFormat=figformat, verbose=verbose)
        plt.close()
