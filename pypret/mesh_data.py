""" This module implements a simple mesh-data handler.

Disclaimer
----------

THIS CODE IS FOR EDUCATIONAL PURPOSES ONLY! The code in this package was not
optimized for accuracy or performance. Rather it aims to provide a simple
implementation of the basic algorithms.

Author: Nils Geib, nils.geib@uni-jena.de
"""
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from . import lib
from . import io


class MeshData(io.IO):
    _io_store = ["data", "axes", "labels", "units"]

    def __init__(self, data,  *axes, labels=None, units=None):
        ''' Creates a MeshData instance.

        Parameter
        ---------
        data : ndarray
            A at least two-dimensional array containing the data.
        *axes : ndarray
            Arrays specifying the coordinates of the data axes. Must be given
            in indexing order.
        labels : list of str, optional
            A list of strings labeling the axes. The last element labels the
            data itself, e.g. ``labels'' must have one more element than the
            number of axes.
        units : list of str, optional
            A list of unit strings.
        '''
        self.data = data.copy()
        self.axes = [np.array(a).copy() for a in axes]
        if self.ndim != len(axes):
            raise ValueError("Number of supplied axes is wrong!")
        if self.shape != tuple(ax.size for ax in self.axes):
            raise ValueError("Shape of supplied axes is wrong!")
        self.labels = labels
        if self.labels is None:
            self.labels = ["" for ax in self.axes]
        self.units = units
        if self.units is None:
            self.units = ["" for ax in self.axes]

    @property
    def shape(self):
        return self.data.shape

    @property
    def ndim(self):
        return self.data.ndim

    def copy(self):
        ''' Creates a copy of the MeshData instance. '''
        return MeshData(self.data, *self.axes, labels=self.labels,
                        units=self.units)

    def marginals(self, axis=None):
        ''' Calculates the marginals of the data.
        '''
        return lib.marginals(self.data)

    def normalize(self):
        self.data /= self.data.max()

    def autolimit(self, *axes, threshold=1e-2, padding=0.25):
        """ Limits the data based on the marginals.
        """
        if len(axes) == 0:
            # default: operate on all axes
            axes = list(range(self.ndim))
        marginals = lib.marginals(self.data, axes=axes)
        limits = []
        for i, j in enumerate(axes):
            limit = lib.limit(self.axes[j], marginals[i],
                              threshold=threshold, padding=padding)
            limits.append(limit)
        self.limit(*limits, axes=axes)

    def limit(self, *limits, axes=None):
        if axes is None:
            # default: operate on all axes
            axes = list(range(self.ndim))
        axes = lib.as_list(axes)
        if len(axes) != len(limits):
            raise ValueError("Number of limits must match the specified axes!")
        slices = []
        for j in range(self.ndim):
            if j in axes:
                i = axes.index(j)
                ax = self.axes[j]
                x1, x2 = limits[i]
                # do it this way as we cannot assume them to be sorted...
                idx1 = np.argmin(np.abs(ax - x1))
                idx2 = np.argmin(np.abs(ax - x2))
                if idx1 > idx2:
                    idx1, idx2 = idx2, idx1
                elif idx1 == idx2:
                    raise ValueError('Selected empty slice along axis %d!' % i)
                slices.append(slice(idx1, idx2 + 1))
            else:
                # empty slice
                slices.append(slice(None))
            self.axes[j] = self.axes[j][slices[-1]]
        self.data = self.data[(*slices,)]

    def interpolate(self, axis1=None, axis2=None, degree=2, sorted=False):
        axes = [axis1, axis2]
        for i in range(self.ndim):
            if axes[i] is None:
                axes[i] = self.axes[i]
        # FITPACK can only deal with strictly increasing axes
        # so sort them beforehand if necessary...
        orig_axes = self.axes
        data = self.data.copy()
        if not sorted:
            for i in range(len(orig_axes)):
                idx = np.argsort(orig_axes[i])
                orig_axes[i] = orig_axes[i][idx]
                data = np.take(data, idx, axis=i)
        dataf = RegularGridInterpolator(tuple(orig_axes), data,
                                        bounds_error=False, fill_value=0.0)
        grid = lib.build_coords(*axes)
        self.data = dataf(grid)
        self.axes = axes

    def flip(self, *axes):
        if len(axes) == 0:
            return
        axes = lib.as_list(axes)
        slices = [slice(None) for ax in self.axes]
        for ax in axes:
            self.axes[ax] = self.axes[ax][::-1]
            slices[ax] = slice(None, None, -1)
        self.data = self.data[slices]
