from django.shortcuts import render
# fast_batch_visibility.py
import numpy as np
import requests
import pandas as pd
from integrations.models import SBO
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u
from concurrent.futures import ThreadPoolExecutor, as_completed
from astropy.constants import G, M_sun

# ---------- KONWERSJE / STAŁE ----------
DEG2RAD = np.pi/180.0
RAD2DEG = 180.0/np.pi
DAY2SEC = 86400.0
# mu in AU^3 / day^2
_mu = (G * M_sun).to(u.AU**3 / u.day**2).value

# ---------- HELPERY (wektorowe) ----------
def make_time_grid(start_time, end_time, cadence_min):
    t0 = Time(start_time).jd
    t1 = Time(end_time).jd
    step = cadence_min / (24*60)
    jds = np.arange(t0, t1 + 1e-12, step)   # include end if aligns
    return Time(jds, format='jd')

def solve_kepler_vec(M, e, tol=1e-12, max_iter=60):
    """
    M, e can be arrays (same shape). Returns E (array).
    Newton iteration vectorized.
    """
    E = M.copy()
    for _ in range(max_iter):
        f = E - e * np.sin(E) - M
        fp = 1 - e * np.cos(E)
        dE = f / fp
        E -= dE
        if np.all(np.abs(dE) < tol):
            break
    return E

def orbit_xyz_vectorized(a_AU, e, inc_deg, raan_deg, argp_deg, M0_deg, epoch_jd, times_jd):
    """
    Compute heliocentric positions (X,Y,Z) [AU] for a single orbit at many times.
    Inputs scalars for orbit (a,e,...) and times_jd (1D array).
    Returns arrays X,Y,Z (1D arrays length = len(times_jd)) and r (radius AU).
    """
    a = a_AU  # AU
    inc = inc_deg * DEG2RAD
    raan = raan_deg * DEG2RAD
    argp = argp_deg * DEG2RAD
    M0 = M0_deg * DEG2RAD

    n = np.sqrt(_mu / (a**3))  # rad/day

    dt_days = times_jd - epoch_jd
    M = (M0 + n * dt_days) % (2*np.pi)

    E = solve_kepler_vec(M, e)
    # true anomaly
    nu = 2 * np.arctan2(np.sqrt(1+e) * np.sin(E/2), np.sqrt(1-e) * np.cos(E/2))
    r = a * (1 - e * np.cos(E))

    x_orb = r * np.cos(nu)
    y_orb = r * np.sin(nu)

    cosO = np.cos(raan); sinO = np.sin(raan)
    cosi = np.cos(inc); sini = np.sin(inc)
    cosw = np.cos(argp); sinw = np.sin(argp)

    X = (cosO*cosw - sinO*sinw*cosi) * x_orb + (-cosO*sinw - sinO*cosw*cosi) * y_orb
    Y = (sinO*cosw + cosO*sinw*cosi) * x_orb + (-sinO*sinw + cosO*cosw*cosi) * y_orb
    Z = (sini * sinw) * x_orb + (sini * cosw) * y_orb

    return X, Y, Z, r

def earth_heliocentric_positions(times_jd):
    """
    Very fast Kepler approx for Earth's heliocentric position on times_jd (1D array).
    Returns earth_xyz (3, N) array in AU.
    Uses rough Earth orbital elements (sufficient for relative geometry in planning).
    """
    # Rough J2000 elements for Earth
    a = 1.000001018
    e = 0.0167086
    inc = 0.00005
    raan = -11.26064
    argp = 102.94719
    M0 = 357.51716  # deg at epoch
    epoch = 2451545.0
    X, Y, Z, r = orbit_xyz_vectorized(a, e, inc, raan, argp, M0, epoch, times_jd)
    return np.vstack([X, Y, Z])  # shape (3, N)

# ---------- GEOMETRIA -> RA/DEC/ALT (wektorowo) ----------
def compute_radec_alt_for_vector(X, Y, Z, earth_xyz, times, location):
    """
    X,Y,Z: arrays [N] - heliocentric positions of object (AU)
    earth_xyz: (3,N) - heliocentric positions of Earth (AU)
    times: astropy Time array (len N)
    location: EarthLocation
    Returns:
      ra_deg, dec_deg, alt_deg, elong_deg  (arrays length N)
    All angles in degrees.
    """
    # geocentric vector (object from earth)
    gx = X - earth_xyz[0]
    gy = Y - earth_xyz[1]
    gz = Z - earth_xyz[2]

    # RA/DEC
    ra = np.arctan2(gy, gx)  # rad
    dec = np.arctan2(gz, np.sqrt(gx*gx + gy*gy))

    # normalize RA to 0..2pi
    ra = np.mod(ra, 2*np.pi)

    # altitude: need local sidereal time (rad)
    # fast GMST approx in hours -> convert to rad
    gmst_hours = (18.697374558 + 24.06570982441908 * (times.jd - 2451545.0)) % 24.0
    gmst_rad = gmst_hours * (2*np.pi/24.0)
    lst = gmst_rad + np.deg2rad(location.lon.value)  # rad

    ha = lst - ra
    # normalize ha to [-pi, pi]
    ha = (ha + np.pi) % (2*np.pi) - np.pi

    lat_rad = np.deg2rad(location.lat.value)
    alt = np.arcsin(np.sin(lat_rad)*np.sin(dec) + np.cos(lat_rad)*np.cos(dec)*np.cos(ha))

    # elongation: angle Sun-Earth-Object (approx): angle between (obj - earth) and (-earth)
    sun_to_earth = -earth_xyz  # shape (3,N)
    obj_from_earth = np.vstack([gx, gy, gz])  # shape (3,N)
    dot = np.sum(sun_to_earth * obj_from_earth, axis=0)
    norm1 = np.sqrt(np.sum(sun_to_earth*sun_to_earth, axis=0))
    norm2 = np.sqrt(np.sum(obj_from_earth*obj_from_earth, axis=0))
    cos_elong = dot / (norm1 * norm2)
    cos_elong = np.clip(cos_elong, -1.0, 1.0)
    elong = np.arccos(cos_elong)

    return np.rad2deg(ra), np.rad2deg(dec), np.rad2deg(alt), np.rad2deg(elong)

# ---------- DETEKCJA OKIEN (wektorowo) ----------
def detect_windows_from_mask(mask, times):
    """
    mask: boolean 1D array
    times: astropy Time array (same length)
    Returns list of (start_time_iso, end_time_iso, start_idx, end_idx)
    """
    if mask.size == 0:
        return []
    diff = np.diff(mask.astype(np.int8))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0]

    if mask[0]:
        starts = np.r_[0, starts]
    if mask[-1]:
        ends = np.r_[ends, mask.size-1]

    windows = []
    for s, e in zip(starts, ends):
        windows.append((times[s].iso, times[e].iso, int(s), int(e)))
    return windows

# ---------- SZYBKA FUNKCJA DLA JEDNEGO OBIEKTU (wewnętrzna) ----------
def _process_one_object(orb, times, times_jd, earth_xyz, location,
                        min_alt, min_elong):
    """
    orb: dict with keys: name,a,e,i,om,w,ma,epoch
    returns name -> windows list (each: dict)
    """
    name = orb.get("name", orb.get("designation", "unnamed"))
    try:
        X, Y, Z, r = orbit_xyz_vectorized(float(orb["a"]), float(orb["e"]),
                                          float(orb["i"]), float(orb["om"]),
                                          float(orb["w"]), float(orb["ma"]),
                                          float(orb["epoch"]), times_jd)
    except Exception as exc:
        # if any problem with params, return empty
        return name, []

    ra_deg, dec_deg, alt_deg, elong_deg = compute_radec_alt_for_vector(X, Y, Z, earth_xyz, times, location)

    # mask criteria (tuneable)
    mask = (alt_deg >= min_alt) & (elong_deg >= min_elong)

    windows_raw = detect_windows_from_mask(mask, times)
    if not windows_raw:
        return []
    windows_out = []
    for start_iso, end_iso, si, ei in windows_raw:
        a = SBO(name = name, latitude = float(ra_deg[si]), longitude = float(dec_deg[si]), begin_time = start_iso, end_time = end_iso)
        windows_out.append(a)
    return  windows_out

# ---------- FUNKCJA BATCH (publiczna) ----------
def visibility_for_many(objects,
                        start_time, end_time,
                        observer_lat, observer_lon, observer_elev_m=0,
                        cadence_min=10,
                        min_alt_deg=5.0,
                        min_elong_deg=10.0,
                        max_workers=8):
    """
    objects: list of dicts. Required keys: name,a,e,i,om,w,ma,epoch
             a [AU], e, i/om/w/ma in degrees, epoch in JD
    start_time/end_time: anything accepted by astropy Time (e.g. '2025-12-09 18:00:00' or datetime)
    observer_lat/lon: degrees (lon positive east)
    observer_elev_m: meters
    cadence_min: sampling (minutes)
    min_alt_deg: minimal altitude to consider visible
    min_elong_deg: minimal solar elongation
    max_workers: number of threads for parallel processing

    Returns: dict mapping object name -> list of windows (each a dict).
             Objects with empty windows are omitted.
    """
    # time grid
    times = make_time_grid(start_time, end_time, cadence_min)
    times_jd = times.jd  # numpy array
    # earth positions once
    earth_xyz = earth_heliocentric_positions(times_jd)  # shape (3, N)

    # observer location
    location = EarthLocation(lat=observer_lat*u.deg, lon=observer_lon*u.deg, height=observer_elev_m*u.m)

    results = []

    # for obj in objects:
    #     windows = _process_one_object(obj, times, times_jd, earth_xyz, location,
    #                                   min_alt_deg, min_elong_deg)
    #     if windows:  # only keep objects that have at least one window
    #         results.extend(windows)


    # parallel map
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        futures = [exe.submit(_process_one_object, obj, times, times_jd, earth_xyz, location, min_alt_deg, min_elong_deg)
                   for obj in objects]
        for fut in as_completed(futures):
            windows = fut.result()
            if windows:  # only keep objects that have at least one window
                results.extend(windows)
    return results

def fetch_sbdb_objects(limit):
    url = (
        "https://ssd-api.jpl.nasa.gov/sbdb_query.api?"
        f"fields=name,a,e,i,om,w,ma,epoch&sb-kind=a&limit={limit}"
    )
    data = requests.get(url).json()
    fields = data["fields"]

    objects = []
    for row in data["data"]:
        entry = dict(zip(fields, row))
        objects.append(entry)
    return objects

def get_query_sbo(latitude, longitude, begin_time, end_time, elevation=100, limit=100):
    objects = fetch_sbdb_objects(limit)
    res = visibility_for_many(objects,
                              start_time=begin_time,
                              end_time=end_time,
                              observer_lat=latitude, observer_lon=longitude, observer_elev_m=elevation,
                              cadence_min=10,
                              min_alt_deg=10.0,
                              min_elong_deg=22.0,
                              max_workers=8)
    sbo_list_dict = [obj.to_dict() for obj in res]
    return sbo_list_dict