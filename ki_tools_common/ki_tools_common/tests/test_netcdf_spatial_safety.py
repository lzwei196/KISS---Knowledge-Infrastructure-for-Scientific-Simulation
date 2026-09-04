"""Regression tests for longitude, CRS, and empty-domain safety."""
from __future__ import annotations

import numpy as np
import pytest

xr = pytest.importorskip("xarray")

from ki_tools_common import netcdf_utils as nu


def _grid(longitudes):
    lat = np.array([20.0, 10.0, 0.0])  # descending is intentional
    lon = np.asarray(longitudes, dtype=float)
    values = np.arange(lat.size * lon.size).reshape(lat.size, lon.size)
    return xr.Dataset({"v": (("lat", "lon"), values)},
                      coords={"lat": lat, "lon": lon})


def test_bbox_subset_handles_western_longitudes_on_0360_grid():
    ds = _grid([340.0, 350.0, 355.0, 0.0, 10.0])
    out = nu.bbox_subset(ds, 0, 20, -10, -5)
    assert out.lon.values.tolist() == [350.0, 355.0]
    assert out.lat.values.tolist() == [20.0, 10.0, 0.0]


def test_bbox_subset_handles_descending_longitude_and_antimeridian():
    ds = _grid([200.0, 190.0, 180.0, 170.0, 160.0])
    out = nu.bbox_subset(ds, 0, 20, 170, -170)
    assert out.lon.values.tolist() == [190.0, 180.0, 170.0]


def test_bbox_subset_rejects_empty_and_curvilinear_domains():
    ds = _grid([0.0, 10.0, 20.0])
    with pytest.raises(ValueError, match="does not overlap"):
        nu.bbox_subset(ds, 40, 50, 0, 20)

    curved = xr.Dataset(
        {"v": (("y", "x"), np.ones((2, 2)))},
        coords={"XLAT": (("y", "x"), [[0, 0], [1, 1]]),
                "XLONG": (("y", "x"), [[10, 11], [10, 11]])},
    )
    with pytest.raises(ValueError, match="curvilinear"):
        nu.bbox_subset(curved, 0, 1, 10, 11)


def test_basin_mask_reprojects_and_normalises_0360_longitude(monkeypatch,
                                                             tmp_path):
    shp = tmp_path / "basin.shp"
    shp.write_bytes(b"placeholder")
    calls = []

    class Crs:
        def equals(self, other):
            return False

    class Geometry:
        def covers(self, point):
            lon, lat = point
            return -10 <= lon <= -5 and 0 <= lat <= 20

    class GeometryColumn:
        unary_union = Geometry()

    class Frame:
        empty = False
        crs = Crs()
        geometry = GeometryColumn()

        def to_crs(self, value):
            calls.append(value)
            self.crs = value
            return self

    class Gpd:
        @staticmethod
        def read_file(_path):
            return Frame()

    monkeypatch.setattr(nu, "_HAS_GEO", True)
    monkeypatch.setattr(nu, "gpd", Gpd())
    monkeypatch.setattr(nu, "Point", lambda lon, lat: (lon, lat))
    mask = nu.basin_mask_from_shapefile(
        _grid([340.0, 350.0, 355.0, 0.0]), str(shp))
    assert calls == ["EPSG:4326"]
    assert mask[:, 1:3].all()
    assert not mask[:, [0, 3]].any()


def test_spatial_mean_rejects_empty_and_all_nan_domains():
    data = np.ones((2, 2, 2))
    with pytest.raises(ValueError, match="selects no cells"):
        nu._spatial_mean(data, np.zeros((2, 2), dtype=bool), source="test.nc")
    with pytest.raises(ValueError, match="only missing values"):
        nu._spatial_mean(np.full((2, 2, 2), np.nan), None, source="test.nc")
