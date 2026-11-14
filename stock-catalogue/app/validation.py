"""Field normalisation, SKU / name generation and weight plausibility checks."""
import math
import re

AVAILABILITY = {
    "available": "Available",
    "out_of_stock": "Out of stock",
    "unconfirmed": "Unconfirmed",
}
_AVAIL_ALIASES = {
    "available": "available", "in stock": "available", "instock": "available", "yes": "available",
    "y": "available", "a": "available",
    "out of stock": "out_of_stock", "out_of_stock": "out_of_stock", "outofstock": "out_of_stock",
    "no": "out_of_stock", "n": "out_of_stock", "oos": "out_of_stock", "unavailable": "out_of_stock",
    "unconfirmed": "unconfirmed", "": "unconfirmed", "unknown": "unconfirmed", "?": "unconfirmed",
    "on request": "unconfirmed",
}
PIPE_CLASSES = ("", "L", "M", "H")
STEEL = 0.00785  # kg per mm^2 per metre (density 7850 kg/m3)


def norm_availability(v):
    key = (v or "").strip().lower().replace("-", " ")
    if key in _AVAIL_ALIASES:
        return _AVAIL_ALIASES[key]
    key2 = key.replace(" ", "_")
    if key2 in AVAILABILITY:
        return key2
    raise ValueError(f"Unknown availability '{v}'. Use Available, Out of stock or Unconfirmed.")


def norm_size(v):
    """'40X20', '40*20', '40 x 20' -> '40 x 20'."""
    s = (v or "").strip()
    s = re.sub(r"\s*[xX×*]\s*", " x ", s)
    return re.sub(r"\s+", " ", s)


def to_float(v, field):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"{field}: '{v}' is not a number")


def fmt_num(x, decimals=None):
    if x is None:
        return ""
    if decimals is not None:
        return f"{x:.{decimals}f}"
    return ("%g" % x)


def fmt_thk(t):
    return "" if t is None else f"{t:.1f}"


def make_sku(prefix, size, thickness=None):
    core = re.sub(r"\s+", "", (size or "").upper())
    sku = f"{prefix}-{core}"
    if thickness is not None:
        sku += f"-{fmt_thk(thickness)}"
    return sku


def make_name(category, a):
    label = category["item_label"] or category["name"]
    size = a.get("size") or ""
    t = a.get("thickness_mm")
    if category["slug"] == "chs" or a.get("nominal_bore"):
        nb = a.get("nominal_bore") or size
        od = a.get("od_mm")
        s = f"{label} {nb}"
        if od:
            s += f", OD {fmt_num(od)}"
        if t is not None:
            s += f" x {fmt_thk(t)} mm"
        if a.get("pipe_class"):
            s += f" ({a['pipe_class']})"
        return s
    if t is not None:
        return f"{label} {size} x {fmt_thk(t)} mm"
    return f"{label} {size} mm".strip()


def nominal_from_size(size):
    nums = re.findall(r"\d+(?:\.\d+)?", size or "")
    return [float(n) for n in nums]


def theoretical_kg_m(slug, a):
    nums = nominal_from_size(a.get("size"))
    t = a.get("thickness_mm")
    try:
        if slug == "round-bars" and nums:
            return math.pi / 4 * nums[0] ** 2 * STEEL
        if slug == "square-bars" and nums:
            return nums[0] ** 2 * STEEL
        if slug in ("flats", "flats-round-edge") and len(nums) >= 2:
            return nums[0] * nums[1] * STEEL
        if slug == "angles" and len(nums) >= 3:
            a1, a2, th = nums[:3]
            return (a1 + a2 - th) * th * STEEL
        if slug in ("rhs", "shs") and len(nums) >= 2 and t:
            # sharp-corner approximation; real IS 4923 sections are a few % lighter
            return (2 * (nums[0] + nums[1]) - 4 * t) * t * STEEL
        if slug == "chs" and a.get("od_mm") and t:
            return math.pi * (a["od_mm"] - t) * t * STEEL
    except (TypeError, IndexError):
        return None
    return None


# tolerance bands (fraction). Hollow sections use a wider lower band because of corner radii.
_TOL = {"rhs": (-0.07, 0.04), "shs": (-0.07, 0.04), "chs": (-0.05, 0.05)}
_DEFAULT_TOL = (-0.05, 0.05)
PIECE_LENGTH_M = 6.0


def weight_check(slug, a):
    """Return a human-readable note if the printed weights look inconsistent, else ''."""
    issues = []
    kgm = a.get("weight_kg_m")
    theo = theoretical_kg_m(slug, a)
    if kgm and theo:
        dev = (kgm - theo) / theo
        lo, hi = _TOL.get(slug, _DEFAULT_TOL)
        if dev < lo or dev > hi:
            issues.append(f"Kg/m {fmt_num(kgm)} differs {dev:+.0%} from theoretical {theo:.2f}")
    kgpc = a.get("weight_kg_pc")
    if kgm and kgpc:
        expected = kgm * PIECE_LENGTH_M
        dev = (kgpc - expected) / expected
        if abs(dev) > 0.015:
            issues.append(f"Kg/pc {fmt_num(kgpc)} does not equal Kg/m x 6 m ({expected:.2f})")
    return "; ".join(issues)


def wa_digits(phone):
    """Return digits for a wa.me link (country code included), or '' if unusable."""
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 10:          # Indian mobile without country code
        d = "91" + d
    if len(d) == 12 and d.startswith("91"):
        return d
    if 11 <= len(d) <= 15 and not d.startswith("0"):
        return d
    return ""


def pretty_phone(phone):
    d = wa_digits(phone)
    if len(d) == 12 and d.startswith("91"):
        return f"+91 {d[2:7]} {d[7:]}"
    return phone or ""
