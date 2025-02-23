import cupy as cp
import numpy as np
import pytest

from cucim.skimage._shared import testing
from cucim.skimage.registration import optical_flow_ilk
from cucim.skimage.transform import warp


def _sin_flow_gen(image0, max_motion=4.5, npics=5):
    """Generate a synthetic ground truth optical flow with a sinusoid as
      first component.

    Parameters:
    ----
    image0: ndarray
        The base image to be warped.
    max_motion: float
        Maximum flow magnitude.
    npics: int
        Number of sinusoid pics.

    Returns
    -------
    flow, image1 : ndarray
        The synthetic ground truth optical flow with a sinusoid as
        first component and the corresponding warped image.

    """
    grid = cp.meshgrid(*[cp.arange(n) for n in image0.shape], indexing='ij')
    grid = cp.stack(grid)
    # TODO: make upstream scikit-image PR changing gt_flow dtype to float
    gt_flow = cp.zeros_like(grid, dtype=float)
    gt_flow[0, ...] = max_motion * cp.sin(
        grid[0] / grid[0].max() * npics * np.pi
    )
    image1 = warp(image0, grid - gt_flow, mode="nearest")
    return gt_flow, image1


@pytest.mark.parametrize('dtype', [cp.float32, cp.float64])
@pytest.mark.parametrize('gaussian', [True, False])
@pytest.mark.parametrize('prefilter', [True, False])
def test_2d_motion(dtype, gaussian, prefilter):
    # Generate synthetic data
    rnd = np.random.RandomState(0)
    image0 = rnd.normal(size=(256, 256))
    image0 = cp.asarray(image0, dtype=dtype)
    gt_flow, image1 = _sin_flow_gen(image0)
    image1 = image1.astype(dtype, copy=False)
    # Estimate the flow
    flow = optical_flow_ilk(image0, image1,
                            gaussian=gaussian, prefilter=prefilter,
                            dtype=dtype)
    assert flow.dtype == dtype
    # Assert that the average absolute error is less then half a pixel
    assert abs(flow - gt_flow).mean() < 0.5


@pytest.mark.parametrize('gaussian', [True, False])
@pytest.mark.parametrize('prefilter', [True, False])
def test_3d_motion(gaussian, prefilter):
    # Generate synthetic data
    rnd = np.random.RandomState(0)
    image0 = rnd.normal(size=(50, 55, 60))
    image0 = cp.asarray(image0)
    gt_flow, image1 = _sin_flow_gen(image0, npics=3)
    # Estimate the flow
    flow = optical_flow_ilk(image0, image1, radius=5,
                            gaussian=gaussian, prefilter=prefilter)

    # Assert that the average absolute error is less then half a pixel
    assert abs(flow - gt_flow).mean() < 0.5


def test_no_motion_2d():
    rnd = np.random.RandomState(0)
    img = rnd.normal(size=(256, 256))
    img = cp.asarray(img)

    flow = optical_flow_ilk(img, img)

    assert cp.all(flow == 0)


def test_no_motion_3d():
    rnd = np.random.RandomState(0)
    img = rnd.normal(size=(64, 64, 64))
    img = cp.asarray(img)

    flow = optical_flow_ilk(img, img)

    assert cp.all(flow == 0)


def test_optical_flow_dtype():
    # Generate synthetic data
    rnd = np.random.RandomState(0)
    image0 = rnd.normal(size=(256, 256))
    image0 = cp.asarray(image0)
    gt_flow, image1 = _sin_flow_gen(image0)
    # Estimate the flow at double precision
    flow_f64 = optical_flow_ilk(image0, image1, dtype='float64')

    assert flow_f64.dtype == 'float64'

    # Estimate the flow at single precision
    flow_f32 = optical_flow_ilk(image0, image1, dtype='float32')

    assert flow_f32.dtype == 'float32'

    # Assert that floating point precision does not affect the quality
    # of the estimated flow

    assert cp.abs(flow_f64 - flow_f32).mean() < 1e-3


def test_incompatible_shapes():
    rnd = cp.random.RandomState(0)
    I0 = rnd.normal(size=(256, 256))
    I1 = rnd.normal(size=(255, 256))
    with testing.raises(ValueError):
        u, v = optical_flow_ilk(I0, I1)


def test_wrong_dtype():
    rnd = cp.random.RandomState(0)
    img = rnd.normal(size=(256, 256))
    with testing.raises(ValueError):
        u, v = optical_flow_ilk(img, img, dtype='int')
