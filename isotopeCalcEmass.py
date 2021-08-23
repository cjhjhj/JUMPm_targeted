#!/usr/bin/python

"""
Based on an algorithm in
Rockwood, A.L. and Haimi, P.: "Efficent calculation of accurate masses of isotopic peaks",
Journal of The American Society for Mass Spectrometry
"""

import re, os, sys, numpy as np, pandas as pd
from pyteomics import mass
from collections import namedtuple
from datetime import datetime

####################
# Global variables #
####################
ELECTRONMASS = 0.00054857990946
PROTONMASS = 1.007276466812
DUMMYMASS = -1000000
isotope = namedtuple('isotope', ('mass', 'abundance'))
# masterIsotope = {'H': [isotope(1.00782503224, 0.999885), isotope(2.01410177811, 0.000115)],
#                  'C': [isotope(12.0000000, 0.9893), isotope(13.00335483521, 0.0107)],
#                  'N': [isotope(14.00307400446, 0.99636), isotope(15.0001088989, 0.00364)],
#                  'O': [isotope(15.99491461960, 0.99757), isotope(16.9991317566, 0.00038), isotope(17.9991596128, 0.00205)],
#                  'S': [isotope(31.9720711744, 0.9499), isotope(32.9714589099, 0.0075),
#                        isotope(33.96786701, 0.0425), isotope(35.96708070, 0.0001)],
#                  'P': [isotope(30.9737619986, 1)]}


#############
# Functions #
#############
# Merge two patterns to one
def convoluteBasic(g, f):
    h = []
    gn = len(g)
    fn = len(f)
    if gn == 0 or fn == 0:
        return
    for k in range(0, (gn + fn)):
        sumWeight, sumMass = 0, 0
        start = max(0, k - fn + 1)
        end = min(gn - 1, k)
        for i in range(start, end + 1):
            weight = g[i].abundance * f[k - i].abundance
            mass = g[i].mass + f[k - i].mass
            sumWeight += weight
            sumMass += weight * mass
        if sumWeight == 0:
            p = isotope(DUMMYMASS, sumWeight)
        else:
            p = isotope(sumMass / sumWeight, sumWeight)
        h.append(p)

    return h


# Prune the small peaks
def prune(f, limit):
    prune = []
    counter = 0
    for i in f:
        if i.abundance > limit:
            break
        prune.append(counter)
        counter += 1
    counter = len(f) - 1
    for i in reversed(f):
        if i.abundance > limit:
            break
        prune.append(counter)
        counter -= 1
    for i in reversed(sorted(list(set(prune)))):
        del f[i]

    return f


# Calculate isotopic peaks
def calculate(comp, masterIsotope, charge, limit):
    # Initialization
    res = [isotope(0, 1)]

    # Calculation of isotopic peaks
    for i in comp:    # For each element in formula, fm
        sal = [masterIsotope[i]]  # Deepcopy?
        n = int(comp[i])
        j = 0
        # This while loop grows the superatom
        while n > 0:
            sz = len(sal)
            if j == sz:
                # Double the elemental superatom
                sal.append([])
                sal[j] = convoluteBasic(sal[j - 1], sal[j - 1])
                prune(sal[j], limit)
            if n & 1:
                # Grow the molecular superatom (convolute the result) when n ends with 1
                tmp = convoluteBasic(res, sal[j])
                prune(tmp, limit)
                tmp, res = res, tmp
            n = n >> 1
            j += 1

    # Take charge into account
    for i in range(len(res)):
        res[i] = res[i]._replace(mass=(res[i].mass + PROTONMASS * charge) / abs(charge))

    return res


def getParams(paramFile):
    parameters = dict()
    with open(paramFile, 'r') as file:
        for line in file:
            if re.search(r'^#', line) or re.search(r'^\s', line):
                continue
            line = re.sub(r'#.*', '', line)  # Remove comments (start from '#')
            line = re.sub(r'\s*', '', line)  # Remove all whitespaces

            # Exception for "feature_files" parameter
            if "feature_files" in parameters and line.endswith("feature"):
                parameters["feature_files"].append(line)
            else:
                key = line.split('=')[0]
                val = line.split('=')[1]
                if key == "feature_files":
                    parameters[key] = [val]
                else:
                    parameters[key] = val
    return parameters


def getMasterIsotope(comp):
    res = {}
    for elem in comp.keys():
        res[elem] = []
        nist = mass.nist_mass[elem]
        for k, v in nist.items():
            if k > 0 and v[1] > 0:
                res[elem].append(isotope(v[0], v[1]))

    return res


def getTemplates(formula, params):
    comp = mass.Composition(formula)    # A dictionary of the formula
    masterIsotope = getMasterIsotope(comp)  # Isotopes of the elements in 'comp'

    # Update the masterIsotope and formula dictionaries by user-defined parameters
    if 'Tracer_1' in params:
        if params['Tracer_1'] == '13C':
            comp["XX"] = 0
            masterIsotope.update({'XX': [isotope(12, 1 - float(params['Tracer_1_purity'])),
                                        isotope(13.00335483521, float(params['Tracer_1_purity']))]})
        elif params['Tracer_1'] == '15N':
            comp["YY"] = 0
            masterIsotope.update({'YY': [isotope(14.00307400446, 1 - float(params['Tracer_1_purity'])),
                                        isotope(15.0001088989, float(params['Tracer_1_purity']))]})
        else:
            sys.exit("\n Information for parameter \"Tracer_1\" is not properly defined\n ")

    if 'Tracer_2' in params:
        if params['Tracer_1'] == '13C':
            comp["XX"] = 0
            masterIsotope.update({'XX': [isotope(12, 1 - float(params['Tracer_1_purity'])),
                                        isotope(13.00335483521, float(params['Tracer_1_purity']))]})
        elif params['Tracer_1'] == '15N':
            comp["YY"] = 0
            masterIsotope.update({'YY': [isotope(14.00307400446, 1 - float(params['Tracer_1_purity'])),
                                        isotope(15.0001088989, float(params['Tracer_1_purity']))]})
        else:
            sys.exit("\n Information for parameter \"Tracer_2\" is not properly defined\n ")

    return comp, masterIsotope


def truncate(array):
    res = []
    n = len(array)
    for i in range(n):
        res_i = pd.DataFrame(0, index=np.arange(0, n), columns=["mz", "intensity"])
        df = pd.DataFrame(array[i])
        df.abundance = df.abundance / max(df.abundance)
        df.abundance[df.abundance < 0.01] = 0
        df.abundance = df.abundance / sum(df.abundance) * 100
        df = df.drop(df[df.abundance == 0].index)
        # df = df.sort_values("abundance", ascending=False)

        repMz = df.mass[df.abundance.idxmax()]
        if len(df[df.mass >= repMz]) > (n - i):
            res_i.loc[i: i - 1 + len(df[df.mass >= repMz]), :] = df[df.mass >= repMz].values[:(n - i)]
        else:
            res_i.loc[i: i - 1 + len(df[df.mass >= repMz]), :] = df[df.mass >= repMz].values
        res_i.loc[i - len(df[df.mass < repMz]): i - 1, :] = df[df.mass < repMz].values

        res.append({"isotopologues": "M" + str(i),
                    "isotope_m/z": ";".join([str(v) for v in res_i.mz.values]),
                    "isotope_intensity": ";".join([str(v) for v in res_i.intensity.values])})

    res = pd.DataFrame(res)
    return res


def getIsotopologues(formula, charge, params):
    comp, masterIsotope = getTemplates(formula, params)
    limit = 1e-10   # This limit should be included in parameters

    if "C" in comp:
        nIsotopologues = comp["C"] + 1
    else:
        nIsotopologues = 1

    isotopologues = []
    for i in range(nIsotopologues):
        if i > 0:
            if params["Tracer_1"] == "13C":
                comp["C"] -= 1
                comp["XX"] += 1
            elif params["Tracer_1"] == "15N":
                comp["N"] -= 1
                comp["YY"] += 1

        isotopologue = calculate(comp, masterIsotope, charge, limit)
        isotopologues.append(isotopologue)

    # Truncate small isotopic peaks, convert abundances to a relative scale and change to a dataframe
    isotopologues = truncate(isotopologues)
    return isotopologues



if __name__ == "__main__":
    paramFile = r"C:\Users\jcho\OneDrive - St. Jude Children's Research Hospital\UDrive\Research\Projects\7Metabolomics\Dev\Targeted\jumpm_targeted.params"
    params = getParams(paramFile)
    formula = "C10H16N5O13P3"
    charge = -1
    res = getIsotopologues(formula, charge, params)
    print()
