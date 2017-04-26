from io import StringIO
from os.path import splitext
import importlib
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.animation as anim
from math import ceil
import sys
import splipy
from itertools import chain, product, islice, repeat, tee, combinations_with_replacement
from multiprocessing import Pool
from tqdm import tqdm
from . import data


<<<<<<< HEAD
def structure(fn, out, coords, nums, level=0, store_basis=True, fprefix=''):
=======
plt.switch_backend('Qt5Agg')


def transform(fn, normal, basept, auto, out):
    vtk = importlib.import_module('vtk')
    f = next(data.read(fn))

    if not normal and not basept:
        polydata = f.reader.GetOutput()
        arr = np.array([polydata.GetPoint(i) for i in range(polydata.GetNumberOfPoints())])
        arr = arr - arr.mean(axis=0)
        w, v = np.linalg.eig(np.dot(arr.T, arr))
        min_idx = w.argmin()
        normal = v[:,min_idx]
        basept = polydata.GetPoint(0)

        if not auto:
            print('Normal: {}', normal)
            print('Base: {}', basept)

            return

    normal = np.array(normal)
    basept = np.array(basept)

    transform = vtk.vtkTransform()
    transform.PostMultiply()
    transform.Translate(*(-p for p in basept))

    tgt = np.array([0, 1, 0])
    if np.dot(normal, tgt) < 0:
        normal = -normal
    axis = np.cross(normal, tgt)
    axis /= np.linalg.norm(axis)
    angle = np.arccos(np.dot(normal, tgt)) * 180 / np.pi
    print(angle, axis, fn)
    transform.RotateWXYZ(angle, *axis)

    transformfilter = vtk.vtkTransformPolyDataFilter()
    transformfilter.SetInputConnection(f.reader.GetOutputPort())
    transformfilter.SetTransform(transform)
    transformfilter.Update()

    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(out)
    writer.SetInputConnection(transformfilter.GetOutputPort())
    writer.Write()


def structure(fn, out, coords, nums, level=0, store_basis=True, fprefix='', tolerance=None):
>>>>>>> b280573f73c1407343a1b1a2f241266a29d3cb68
    vtk = importlib.import_module('vtk')

    f = next(data.read(fn))
    dataset = f.reader.GetOutput()

    # Substitute unknown bounds with bounding box
    xmin, xmax, ymin, ymax, zmin, zmax = dataset.GetBounds()
    bbox = [(xmin, xmax), (ymin, ymax), (zmin, zmax)]
    for i, (c, bb) in enumerate(zip(coords, bbox)):
        if c[0] is None: c[0] = bb[0]
        if c[1] is None: c[1] = bb[1]
        if c[0] == c[1]: nums[i] = 0

    dims = 0
    shape = []
    for i, (c, n) in enumerate(zip(coords, nums)):
        coords[i] = np.linspace(c[0], c[1], n+1)
        if n > 0:
            dims += 1
            shape.append(n+1)

    points = vtk.vtkPoints()
    for z, y, x in product(*coords[::-1]):
        points.InsertNextPoint(x, y, z)
    new_grid = vtk.vtkStructuredGrid()
    new_grid.SetDimensions(*[n+1 for n in nums])
    new_grid.SetPoints(points)

    probefilter = vtk.vtkProbeFilter()
    probefilter.SetSourceConnection(f.reader.GetOutputPort())
    probefilter.SetInputData(new_grid)

    if tolerance:
        probefilter.SetComputeTolerance(False)
        probefilter.SetTolerance(tolerance)

    probefilter.Update()
    structgrid = probefilter.GetStructuredGridOutput()

    basename, ext = splitext(out)

    if ext in {'.hdf5', '.h5'}:
        f = data.IFEMFile(out)

        if store_basis:
            obj = {
                1: splipy.Curve,
                2: splipy.Surface,
                3: splipy.Volume,
            }[dims]()
            obj.set_dimension(3)
            obj.refine(*[k-2 for k in shape])
            for stuff in product(*map(enumerate, coords)):
                idx = tuple([i for (i,_),c in zip(stuff, coords) if len(c) > 1] + [None])
                obj.controlpoints[idx] = tuple(c for _,c in stuff)
            f.save_basis('basis', 0, obj)

        pointdata = structgrid.GetPointData()
        for i in range(pointdata.GetNumberOfArrays()):
            fieldname = pointdata.GetArrayName(i)
            if fieldname.startswith('vtk'):
                continue
            array = pointdata.GetArray(i)
            coefs = np.zeros((np.prod(shape), len(array.GetTuple(0))))
            for i, _ in enumerate(product(*coords[::-1])):
                coefs[i,:] = array.GetTuple(i)
            f.save_coeffs(fprefix + fieldname, 'basis', level, 0, coefs, transpose=False)

    elif ext == '.vtk':
        writer = vtk.vtkStructuredGridWriter()
        writer.SetFileName(out)
        writer.SetInputData(structgrid)
        writer.Write()


def plot(filename, field, comp=0, level=0, show=True, vmin=None, vmax=None, out=None,
         colorbar=True, ticks=True, style='imshow'):
    f = next(data.read(filename))

    back_plotter = {
        'imshow': plt.imshow,
        'contour': plt.contourf,
    }[style]

    ignore_kwds = {
        'imshow': {'levels'},
        'contour': set(),
    }[style]

    def plotter(*args, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if k not in ignore_kwds}
        back_plotter(*args, **kwargs)

    plt.clf()
    coeffs = f.coeffs(field, level, 0)
    if isinstance(comp, int):
        coeffs = coeffs[...,comp]
        levs = np.linspace(np.min(coeffs), np.max(coeffs), 20)
        plotter(coeffs.T, vmin=vmin, vmax=vmax, levels=levs)
        if colorbar:
            plt.colorbar()
    elif comp in {'ss', 'ssq'}:
        coeffs = np.sum(coeffs ** 2, axis=-1)
        if comp == 'ssq':
            coeffs = np.sqrt(coeffs)
        levs = np.linspace(np.min(coeffs), np.max(coeffs), 20)
        plotter(coeffs.T, vmin=vmin, vmax=vmax, levels=levs)
        if colorbar:
            plt.colorbar()
    elif len(comp) == 2 and all(c in 'xyz' for c in comp):
        u, v = (coeffs[...,'xyz'.index(c)].T for c in comp)
        plt.quiver(u, v, alpha=0.15)

    plt.axes().set_aspect(1)

    if not ticks:
        plt.tick_params(axis='x', which='both', bottom='off', top='off', labelbottom='off')
        plt.tick_params(axis='y', which='both', left='off', right='off', labelleft='off')

    if out:
        plt.savefig(out, bbox_inches='tight', pad_inches=0)

    if show:
        plt.show()


def animate(filename, field, comp=0, out='out.mp4'):
    f = next(data.read(filename))
    fig = plt.gcf()
    plt.get_current_fig_manager().window.showMaximized()

    def do(i):
        plot(filename, field, comp=comp, level=i, show=False, vmin=0, vmax=2)
        plt.title('t = {:.4f}'.format(f.t_at(i)))

    writer = anim.writers['ffmpeg'](fps=int(ceil(1/f.dt)), bitrate=2000)
    animation = anim.FuncAnimation(fig, do, tqdm(range(0, f.ntimes)))
    animation.save(out, writer=writer)


def reduce(fields, filenames, out):
    objs = list(chain.from_iterable(data.read(fn) for fn in filenames))
    coeffs = []
    basis = None
    for obj in objs:
        for t in range(0, obj.ntimes):
            coeffs.append(np.hstack(obj.coeffs(f, t, 0) for f in fields))
        if not basis:
            basis = obj.basis(obj.field(fields[0]).attrib['basis'], 0)

    cshape = coeffs[0].shape
    axes = tuple(range(len(cshape)-1))
    coeffs = [c - np.mean(c, axis=axes) for c in coeffs]

    r_coeffs = np.array(coeffs)
    axes = list(range(0, len(r_coeffs.shape)))
    axes = axes[1:] + axes[:1]
    t_coeffs = np.transpose(r_coeffs, axes)

    print('Assembling correlation matrix')
    data_mx = np.tensordot(r_coeffs, t_coeffs, axes=3)

    print('Computing eigenvalues')
    w, v = np.linalg.eigh(data_mx)
    w = w[::-1]
    v = v[:,::-1]

    res = data.IFEMFile(out)
    res.save_basis('basis', 0, basis)
    for k in tqdm(range(0, v.shape[-1]), desc='Finalizing modes'):
        mode = np.zeros(cshape)
        for i, vv in enumerate(v[:,k]):
            mode += vv * coeffs[i]
        mode /= np.sqrt(w[k])
        fieldname = 'mode{:02}'.format(k+1)
        res.save_coeffs(fieldname, 'basis', 0, 0, mode, transpose=True)
        res.set_meta(fieldname, 'energy', w[k] / np.trace(data_mx))


def spectrum(filename, out, plot=False):
    obj = next(data.read(filename))
    nmodes = len(list(obj.fields))

    spec, cspec = [], []
    for i in range(1, nmodes):
        fname = 'mode{:02}'.format(i)
        energy = float(obj.get_meta(fname, 'energy'))
        spec.append(energy)
        cspec.append(energy + (cspec[-1] if cspec else 0))

    with open(out, 'w') as f:
        for s, c in zip(spec, cspec):
            f.write('{} {}\n'.format(s, c))

    if plot:
        plt.plot(cspec, linewidth=2, marker='o')
        plt.plot([0, len(spec) - 1], [0.95, 0.95], '--')
        plt.show()


def avg(filename, field, varying=None, t=0):
    obj = next(data.read(filename))
    coeffs = obj.coeffs(field, t, 0)

    if varying is None:
        axes = tuple(range(0, len(coeffs.shape) - 1))
    else:
        varying = 'xyz'.index(varying)
        axes = tuple(range(0, len(coeffs.shape) - 1))
        axes = tuple(a for a in axes if a != varying)
    mean = np.mean(coeffs, axis=axes)
    print(mean)


def disp_flux(filename, varying=None, t=0):
    obj = next(data.read(filename))
    coeffs = obj.coeffs('U', t, 0)

    if varying is None:
        axes = tuple(range(0, len(coeffs.shape) - 1))
    else:
        varying = 'xyz'.index(varying)
        axes = tuple(range(0, len(coeffs.shape) - 1))
        axes = tuple(a for a in axes if a != varying)

    mean_u = np.mean(coeffs, axis=axes)

    u_tilde = mean_u - coeffs
    z_tilde = u_tilde[..., 2]
    z_tilde = np.reshape(z_tilde, (np.prod(z_tilde.shape), 1))

    test = np.hstack([z_tilde]*3)
    test = np.reshape(test, u_tilde.shape)

    prod = u_tilde * test
    mean_prod = np.mean(prod, axis=axes)
    print(mean_prod)
