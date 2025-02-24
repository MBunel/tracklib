"""
This module contains an algorithm of Analytical Features calculation and 
some utility functions.
"""

# For type annotation
from __future__ import annotations
from typing import Any, Iterable, Optional, Union

import numpy as np

from tracklib.core.Coords import GeoCoords
from tracklib.core.Coords import ENUCoords
from tracklib.core.Coords import ECEFCoords

import matplotlib.colors as mcolors

from heapq import heapify, heappush, heappop


# =============================================================================
#   Gestion des valeurs non renseignées et non calculées
# =============================================================================

NAN = float("nan")


def isnan(number: Union[int, float]) -> bool:
    """Check if two numbers are different"""
    return number != number


def isfloat(value: Any) -> bool:
    """Check is a value is a float"""
    try:
        float(value)
        return True
    except ValueError:
        return False


def listify(input) -> list[Any]:
    """Make to list if needed"""
    if not isinstance(input, list):
        input = [input]
    return input


def unlistify(input):
    """Remove list if needed

    :param input: TODO
    :return: TODO
    """
    if len(input) == 1:
        input = input[0]
    return input


# LIKE comparisons
def compLike(s1, s2) -> bool:
    """TODO

    :param s1: TODO
    :param s2: TODO
    :return: TODO
    """
    tokens = s2.split("%")
    if len(tokens) == 1:
        return s1 in s2  # 'in' or 'equal' yet to be decided
    occ = []
    s = s1
    d = len(s)
    for tok in tokens:
        id = s.find(tok)
        if id < 0:
            return False
        occ.append(id)
        s = s[id + len(tok) : len(s)]
    return True


def makeCoords(
    x: float, y: float, z: float, srid: int
) -> Union[ENUCoords, ECEFCoords, GeoCoords]:
    """Function to form coords object from (x,y,z) data

    :param x: 1st coordinate (X, lon or E)
    :param y: 2nd coordinate (Y, lat or N)
    :param z: 3rd coordinate (Z, hgt or U)
    :param srid: Id of coord system (ECEF, GEO or ENU)

    :return: Coords object in the proper srid
    """
    if srid.upper() in ["ENUCOORDS", "ENU"]:
        return ENUCoords(x, y, z)
    if srid.upper() in ["GEOCOORDS", "GEO"]:
        return GeoCoords(x, y, z)
    if srid.upper() in ["ECEFCOORDS", "ECEF"]:
        return ECEFCoords(x, y, z)


def makeDistanceMatrix(
    T1: list[tuple[float, float]], T2: list[tuple[float, float]]
) -> np.float32:
    """Function to form distance matrix

    :param T1: A list of points
    :param T2: A list of points
    :return: numpy distance matrix between T1 and T2
    """
    T1 = np.array(T1)
    T2 = np.array(T2)

    # Signal stationnarity
    base = min(np.concatenate((T1, T2)))
    T1 = T1 - base
    T2 = T2 - base
    T1 = T1.T
    T2 = T2.T

    return np.sqrt(
        (T1 ** 2).reshape(-1, 1) + (T2 ** 2) - 2 * (T1.reshape(-1, 1) * T2.T)
    )


def makeCovarianceMatrixFromKernel(
    kernel,
    T1: list[tuple[float, float]],
    T2: list[tuple[float, float]],
    factor: float = 1.0,
):
    """Function to form covariance matrix from kernel

    :param kernel: A function describing statistical similarity between points
    :param T1: A list of points
    :param T2: A list of points
    :param factor: Unit factor of std dev (default 1.0)
    """

    D = makeDistanceMatrix(T1, T2)
    kfunc = np.vectorize(kernel.getFunction())

    return factor ** 2 * kfunc(D)


def rgbToHex(color: list[float, float, float, Optional[float]]) -> str:
    """Function to convert RGBA color to hexadecimal

    :param color: A 3 or 4-element array R, G, B [,alpha]. Each color and transparency
        channel is in [0,1]
    :return: A string containing color in hexadecimal
    """
    if len(color) == 3:
        color.append(1)
    R = hex((int)(color[0] * 255))[2:]
    G = hex((int)(color[1] * 255))[2:]
    B = hex((int)(color[2] * 255))[2:]
    A = hex((int)(color[3] * 255))[2:]
    if len(R) < 2:
        R = "0" + R
    if len(G) < 2:
        G = "0" + G
    if len(B) < 2:
        B = "0" + B
    if len(A) < 2:
        A = "0" + A
    return "0x" + A + B + G + R


def interpColors(
    v: float,
    vmin: float,
    vmax: float,
    cmin: list[float, float, float, Optional[float]],
    cmax: list[float, float, float, Optional[float]],
) -> list[float, float, float, float]:
    """
    Function to interpolate RGBA (or RGB) color between two values

    :param v: a float value
    :param vmin: minimal value of v (color cmin)
    :param vmax: maximal value of v (color cmin)
    :param cmin: a 3 or 4-element array R, G, B [,alpha]
    :param cmax: a 3 or 4-element array R, G, B [,alpha]

    :return: A 4-element array
    """
    # norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
    O = []
    O.append(((vmax - v) * cmin[0] + (v - vmin) * cmax[0]) / (vmax - vmin))
    O.append(((vmax - v) * cmin[1] + (v - vmin) * cmax[1]) / (vmax - vmin))
    O.append(((vmax - v) * cmin[2] + (v - vmin) * cmax[2]) / (vmax - vmin))
    if len(cmin) == 4:
        O.append(((vmax - v) * cmin[3] + (v - vmin) * cmax[3]) / (vmax - vmin))
    return O


def getColorMap(cmin, cmax):
    """TODO

    :param cmin: TODO
    :param cmax: TODO
    :return: TODO
    """

    # On définit la map color
    cdict = {"red": [], "green": [], "blue": []}
    cdict["red"].append([0.0, None, cmin[0] / 255])
    cdict["red"].append([1.0, cmax[0] / 255, None])
    cdict["green"].append([0.0, None, cmin[1] / 255])
    cdict["green"].append([1.0, cmax[1] / 255, None])
    cdict["blue"].append([0.0, None, cmin[2] / 255])
    cdict["blue"].append([1.0, cmax[2] / 255, None])

    cmap = mcolors.LinearSegmentedColormap("CustomMap", cdict)

    return cmap


def getOffsetColorMap(cmin, cmax, part):
    """TODO

    :param cmin: TODO
    :param cmax: TODO
    :param part: TODO
    :return: TODO
    """

    # On définit la map color
    cdict = {"red": [], "green": [], "blue": []}
    cdict["red"].append([0.0, None, cmin[0] / 255])
    cdict["red"].append([part, cmin[0] / 255, cmin[0] / 255])
    cdict["red"].append([1.0, cmax[0] / 255, None])

    cdict["green"].append([0.0, None, cmin[1] / 255])
    cdict["green"].append([part, cmin[1] / 255, cmin[1] / 255])
    cdict["green"].append([1.0, cmax[1] / 255, None])

    cdict["blue"].append([0.0, None, cmin[2] / 255])
    cdict["blue"].append([part, cmin[2] / 255, cmin[2] / 255])
    cdict["blue"].append([1.0, cmax[2] / 255, None])

    cmap = mcolors.LinearSegmentedColormap("CustomMap", cdict)

    return cmap


# --------------------------------------------------------------------------
# Priority heap
# --------------------------------------------------------------------------
# Source code from Matteo Dell'Amico
# https://gist.github.com/matteodellamico/4451520
# --------------------------------------------------------------------------
class priority_dict(dict):
    """Dictionary that can be used as a priority queue.

    Keys of the dictionary are items to be put into the queue, and values
    are their respective priorities. All dictionary methods work as expected.
    The advantage over a standard heapq-based priority queue is
    that priorities of items can be efficiently updated (amortized O(1))
    using code as 'thedict[item] = new_priority.'

    The 'smallest' method can be used to return the object with lowest
    priority, and 'pop_smallest' also removes it.

    The 'sorted_iter' method provides a destructive sorted iterator.
    """

    def __init__(self, *args, **kwargs):
        super(priority_dict, self).__init__(*args, **kwargs)
        self._rebuild_heap()

    def _rebuild_heap(self):
        self._heap = [(v, k) for k, v in self.items()]
        heapify(self._heap)

    def smallest(self):
        """Return the item with the lowest priority.

        Raises IndexError if the object is empty.
        """

        heap = self._heap
        v, k = heap[0]
        while k not in self or self[k] != v:
            heappop(heap)
            v, k = heap[0]
        return k

    def pop_smallest(self):
        """Return the item with the lowest priority and remove it.

        Raises IndexError if the object is empty.
        """

        heap = self._heap
        v, k = heappop(heap)
        while k not in self or self[k] != v:
            v, k = heappop(heap)
        del self[k]
        return k

    def __setitem__(self, key, val):
        # We are not going to remove the previous value from the heap,
        # since this would have a cost O(n).
        super(priority_dict, self).__setitem__(key, val)
        if len(self._heap) < 2 * len(self):
            heappush(self._heap, (val, key))
        else:
            # When the heap grows larger than 2 * len(self), we rebuild it
            # from scratch to avoid wasting too much memory.
            self._rebuild_heap()

    def setdefault(self, key, val):
        if key not in self:
            self[key] = val
            return val
        return self[key]

    def update(self, *args, **kwargs):
        # Reimplementing dict.update is tricky -- see e.g.
        # http://mail.python.org/pipermail/python-ideas/2007-May/000744.html
        # We just rebuild the heap from scratch after passing to super.

        super(priority_dict, self).update(*args, **kwargs)
        self._rebuild_heap()

    def sorted_iter(self):
        """Sorted iterator of the priority dictionary items.

        Beware: this will destroy elements as they are returned.
        """

        while self:
            yield self.pop_smallest()
