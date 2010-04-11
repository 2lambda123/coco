#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Rank-sum tests table on "Final Data Points".
that is, for example, using 1/#fevals(ftarget) if ftarget was reached and
-f_final otherwise as input for the rank-sum test, where obviously the larger
the better.
One table per function and dimension."""

from __future__ import absolute_import

import os
import numpy
import matplotlib.pyplot as plt
from bbob_pproc import bestalg
from bbob_pproc.pptex import tableLaTeX, tableLaTeXStar, writeFEvals2, writeFEvalsMaxPrec
from bbob_pproc.pproc import significancetest
from bbob_pproc.bootstrap import ranksums

#try:
    #supersede this module own ranksums method
    #from scipy.stats import ranksums as ranksums
#except ImportError:
    #from bbob_pproc.bootstrap import ranksums
    #pass

from pdb import set_trace

targetsOfInterest = (10., 1., 1e-1, 1e-3, 1e-5, 1e-7) # Needs to be sorted
targetf = 1e-8 # value for determining the success ratio

#Get benchmark short infos: put this part in a function?
funInfos = {}
isBenchmarkinfosFound = False
infofile = os.path.join(os.path.split(__file__)[0], '..',
                        'benchmarkshortinfos.txt')

try:
    f = open(infofile,'r')
    for line in f:
        if len(line) == 0 or line.startswith('%') or line.isspace() :
            continue
        funcId, funcInfo = line[0:-1].split(None,1)
        funInfos[int(funcId)] = funcId + ' ' + funcInfo
    f.close()
    isBenchmarkinfosFound = True
except IOError, (errno, strerror):
    print "I/O error(%s): %s" % (errno, strerror)
    print 'Could not find file', infofile, \
          'Titles in scaling figures will not be displayed.'

def mainnew(dsList0, dsList1, dimsOfInterest, outputdir, info='', verbose=True):
    """Still in shambles: new cleaned up version.
    One table per dimension...
    """

    dictDim0 = dsList0.dictByDim()
    dictDim1 = dsList1.dictByDim()

    alg0 = set(i[0] for i in dsList0.dictByAlg().keys()).pop()[0:3]
    alg1 = set(i[0] for i in dsList1.dictByAlg().keys()).pop()[0:3]

    if info:
        info = '_' + info

    dims = set.intersection(set(dictDim0.keys()), set(dictDim1.keys()))
    if not bestalg.bestalgentries:
        bestalg.loadBBOB2009()

    header = [r'$\Delta f$']
    for i in targetsOfInterest:
        #header.append(r'\multicolumn{2}{@{}c@{}}{$10^{%d}$}' % (int(numpy.log10(i))))
        header.append(r'\multicolumn{2}{@{}c@{}}{1e%+d}' % (int(numpy.log10(i))))
    header.append(r'\multicolumn{2}{|@{}r@{}}{\#succ}')

    for d in dimsOfInterest: # TODO set as input arguments
        table = [header]
        extraeol = [r'\hline']
        try:
            dictFunc0 = dictDim0[d].dictByFunc()
            dictFunc1 = dictDim1[d].dictByFunc()
        except KeyError:
            continue
        funcs = set.union(set(dictFunc0.keys()), set(dictFunc1.keys()))

        nbtests = len(funcs) * 2. #len(dimsOfInterest)

        for f in sorted(funcs):
            bestalgentry = bestalg.bestalgentries[(d, f)]
            curline = [r'${\bf f_{%d}}$' % f]
            bestalgdata = bestalgentry.detERT(targetsOfInterest)
            bestalgevals, bestalgalgs = bestalgentry.detEvals(targetsOfInterest)

            #for i in bestalgdata[:-1]:
            #    curline.append(r'\multicolumn{2}{@{}c@{}}{%s}' % writeFEvals2(i, 2))
            #curline.append(r'\multicolumn{2}{@{}c@{}|}{%s}' % writeFEvals2(bestalgdata[-1], 2))
            for i in bestalgdata[:-1]:
                curline.append(r'\multicolumn{2}{c}{%s}' % writeFEvalsMaxPrec(i, 2))
            curline.append(r'\multicolumn{2}{c|}{%s}' % writeFEvalsMaxPrec(bestalgdata[-1], 2))

            tmp = bestalgentry.detEvals([targetf])[0][0]
            tmp2 = numpy.sum(numpy.isnan(tmp) == False)
            curline.append('%d' % (tmp2))
            if tmp2 > 0:
                curline.append('/%d' % len(tmp))

            table.append(curline[:])
            extraeol.append('')

            rankdata0 = []

            # generate all data from ranksum test
            entries = []
            ertdata = {}
            for nb, dsList in enumerate((dictFunc0, dictFunc1)):
                try:
                    entry = dsList[f][0] # take the first element
                except KeyError:
                    continue # TODO: problem here!
                ertdata[nb] = entry.detERT(targetsOfInterest)
                entries.append(entry)

            testres0vs1 = significancetest(entries[0], entries[1], targetsOfInterest)
            testresbestvs1 = significancetest(bestalgentry, entries[1], targetsOfInterest)

            for nb, entry in enumerate(entries):
                if nb == 0:
                    curline = [r'0:\:\algzeroshort\hspace*{\fill}']
                else:
                    curline = [r'1:\:\algoneshort\hspace*{\fill}']

                #curline = [r'\alg%sshort' % tmp]
                #curline = [r'Alg%d' % nb]
                #curline = [r'%.3s%d' % (entry.algId, nb)]

                data = entry.detERT(targetsOfInterest)

                if nb == 0:
                    assert not isinstance(data, numpy.ndarray)
                    data0 = data[:] # check if it is not an array

                for i, j in enumerate(data):  # is j an appropriate identifier here?
                    #if numpy.isnan(float(j)/bestalgdata[i]):
                    #    set_trace()

                    z, p = testres0vs1[i] #TODO: there is something with the sign that I don't get
                    # assign significance flag
                    significance0vs1 = 0
                    if nb == 0:
                        istat0 = 0
                        istat1 = 1
                    else:
                        z = -z
                        istat0 = 1
                        istat1 = 0
                    # TODO: I don't understand the thing with the sign of significance0vs1
                    if (nbtests * p < 0.05
                        and z > 0 and not numpy.isinf(ertdata[istat0][i]) and 
                        z * (ertdata[istat1][i] - ertdata[istat0][i]) > 0):  # z-value and ERT-ratio must agree
                        significance0vs1 = -int(numpy.ceil(numpy.log10(nbtests * p)))
                    elif nbtests * p < 0.05 and z < 0 and z * (ertdata[istat1][i] - ertdata[istat0][i]) > 0:
                        significance0vs1 = int(numpy.ceil(numpy.log10(nbtests * p)))

                    alignment = 'c'
                    if i == len(data) - 1: # last element
                        alignment = 'c|'
                    if numpy.isinf(bestalgdata[i]): # if the 2009 best did not solve the problem
                        isBold = False
                        if significance0vs1 > 0:
                           isBold = True

                        tmp = writeFEvals2(float(j), 2, isscientific=True)
                        if not numpy.isinf(j):
                            tmp = tmp.rsplit('e', 1)
                            if len(tmp) > 1:
                                tmp[0] = tmp[0].replace('.', '', 1)
                                tmp[-1] = str(int(tmp[-1]) - 1)
                            tmp = r'\textit{%s}' % ('e'.join(tmp))
                            if isBold:
                                tmp = r'\textbf{%s}' % tmp

                        tableentry = (r'\multicolumn{2}{@{}%s@{}}{%s}'
                                      % (alignment, tmp))
                        # TODO: is this the desired behaviour?
                    else:
                        # Formatting
                        tmp = float(j)/bestalgdata[i]
                        assert not numpy.isnan(tmp)
                        #isscientific = False
                        #if tmp >= 1000:
                            #isscientific = True
                        #tableentry = writeFEvals2(tmp, 2, isscientific=isscientific)
                        tableentry = writeFEvalsMaxPrec(tmp, 2)

                        isBold = False
                        if significance0vs1 > 0:
                           isBold = True

                        if numpy.isinf(tmp) and i == len(data)-1:
                            tableentry = (tableentry 
                                          + r'\textit{%s}' % writeFEvals2(numpy.median(entry.maxevals), 2))
                            if isBold:
                                tableentry = r'\textbf{%s}' % tableentry
                            elif 11 < 3 and significance0vs1 < 0:
                                tableentry = r'\textit{%s}' % tableentry
                            tableentry = (r'\multicolumn{2}{@{}%s@{}}{%s}'
                                          % (alignment, tableentry))
                        elif tableentry.find('e') > -1 or (numpy.isinf(tmp) and i != len(data) - 1):
                            if isBold:
                                tableentry = r'\textbf{%s}' % tableentry
                            elif 11 < 3 and significance0vs1 < 0:
                                tableentry = r'\textit{%s}' % tableentry
                            tableentry = (r'\multicolumn{2}{@{}%s@{}}{%s}'
                                          % (alignment, tableentry))
                        else:
                            tmp = tableentry.split('.', 1)
                            if isBold:
                                tmp = list(r'\textbf{%s}' % i for i in tmp)
                            elif 11 < 3 and significance0vs1 < 0:
                                tmp = list(r'\textit{%s}' % i for i in tmp)
                            tableentry = ' & .'.join(tmp)
                            if len(tmp) == 1:
                                tableentry += '&'

                    superscript = ''

                    z, p = testresbestvs1[i]
                    #z, p = ranksums(rankdatabest[i], currankdata)
                    #if ((nbtests * p) < 0.05
                    #    and ((numpy.isinf(bestalgdata[i]) and numpy.isinf(j))
                    #         or z * (j - bestalgdata[i]) > 0)):  # z-value and ERT-ratio must agree
                    #The conditions are now that ERT < ERT_best and 
                    # all(sorted(FEvals_best) > sorted(FEvals_current)).
                    if j - bestalgdata[i] < 0. and not numpy.isinf(bestalgdata[i]):
                        evals = entry.detEvals([targetsOfInterest[i]])[0]
                        evals[numpy.isnan(evals)] = entry.maxevals[numpy.isnan(evals)]
                        bestevals = bestalgentry.detEvals([targetsOfInterest[i]])
                        bestevals, bestalgalg = (bestevals[0][0], bestevals[1][0])
                        bestevals[numpy.isnan(bestevals)] = bestalgentry.maxevals[bestalgalg][numpy.isnan(bestevals)]
                        evals = numpy.array(sorted(evals))[0:min(len(evals), len(bestevals))]
                        bestevals = numpy.array(sorted(bestevals))[0:min(len(evals), len(bestevals))]

                    #The conditions are now that ERT < ERT_best and
                    # all(sorted(FEvals_best) > sorted(FEvals_current)).
                    if ((nbtests * p) < 0.05 and j - bestalgdata[i] < 0.
                        and z < 0.
                        and (numpy.isinf(bestalgdata[i])
                             or all(evals < bestevals))):
                        nbstars = -numpy.ceil(numpy.log10(nbtests * p))
                        #tmp = '\hspace{-.5ex}'.join(nbstars * [r'\star'])
                        if z > 0:
                            superscript = r'\uparrow' #* nbstars
                        else:
                            superscript = r'\downarrow' #* nbstars
                            # print z, linebest[i], line1
                        if nbstars > 1:
                            superscript += str(int(nbstars))

                    addition = '' 
                    if superscript or significance0vs1:
                        s = ''
                        if significance0vs1 > 0:
                           s = '\star'
                        if significance0vs1 > 1:
                           s += str(significance0vs1)
                        s = r'$^{' + s + superscript + r'}$'

                        if tableentry.endswith('}'):
                            tableentry = tableentry[:-1] + s + r'}'
                        else:
                            tableentry += s

                    curline.append(tableentry)

                # Two cases: both tabular give an overfull hbox
                # AND generate a LaTeX Warning: Float too large for page by 16.9236pt on input line 421. (noisy)
                # OR  generate a LaTeX Warning: Float too large for page by 33.57658pt on input line 421. (noisy)

                tmp = entry.evals[entry.evals[:, 0] <= targetf, 1:]
                try:
                    tmp = tmp[0]
                    curline.append('%d' % numpy.sum(numpy.isnan(tmp) == False))
                except IndexError:
                    curline.append('%d' % 0)
                curline.append('/%d' % entry.nbRuns())

                table.append(curline[:])
                extraeol.append('')

            extraeol[-1] = r'\hline'
        extraeol[-1] = ''

        outputfile = os.path.join(outputdir, 'cmptable_%02dD%s.tex' % (d, info))
        spec = r'@{}c@{}|' + '*{%d}{@{}r@{}@{}l@{}}' % len(targetsOfInterest) + '|@{}r@{}@{}l@{}'
        res = r'\providecommand{\algzeroshort}{%s}' % alg0 + '\n'
        res += r'\providecommand{\algoneshort}{%s}' % alg1 + '\n'
        #res += tableLaTeXStar(table, width=r'0.45\textwidth', spec=spec,
                              #extraeol=extraeol)
        res += tableLaTeX(table, spec=spec, extraeol=extraeol)
        f = open(outputfile, 'w')
        f.write(res)
        f.close()
        if verbose:
            print "Table written in %s" % outputfile
