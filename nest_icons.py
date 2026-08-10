import folium

CSS_NEST = """
<style>
.nest       { position:relative; width:36px; height:36px; }
.nest-cup   { position:absolute; left:5px; top:5px; width:26px; height:26px;
              border-radius:50%; background:var(--fill); border:2px solid var(--ring);
              display:grid; place-items:center; box-sizing:border-box;
              box-shadow:0 1px 3px rgba(0,0,0,.35); }
.nest-cup i { font-size:14px; color:var(--ink); line-height:1; }

.nest-badge   { position:absolute; width:15px; height:15px; border-radius:50%;
                background:#fff; border:1.5px solid var(--b);
                display:grid; place-items:center; box-sizing:border-box;
                box-shadow:0 1px 2px rgba(0,0,0,.3);
                font:600 8px/1 system-ui,sans-serif; color:var(--b); }
.nest-badge i { font-size:8px; color:var(--b); line-height:1; }

.nest-temp    { position:absolute; width:18px; height:18px; border-radius:50%;
                background:var(--b); border:1.5px solid rgba(0,0,0,.28);
                display:grid; place-items:center; box-sizing:border-box;
                box-shadow:0 1px 2px rgba(0,0,0,.3);
                font:600 9px/1 system-ui,sans-serif; color:var(--t); }

.nest-nw { top:-3px;  left:-3px;  }
.nest-ne { top:-3px;  right:-3px; }
.nest-sw { bottom:2px;  left:-5px; }
.nest-s  { bottom:0;  left:50%; margin-left:-7.5px; }
.nest-se { bottom:2px;  right:-5px; }

.nest-dir { position:absolute; inset:-5px; transform:rotate(calc(var(--rot,0) * 1deg));
            filter:drop-shadow(0 0 0.5px #fff) drop-shadow(0 0 1px #fff); }
.nest-dir::before { content:""; position:absolute; left:50%; top:-1px; margin-left:-5px;
              border:5px solid transparent; border-bottom-color:var(--ring); }

.nest-label { position:absolute; left:38px; top:9px; white-space:nowrap;
              font:600 11px/1.4 system-ui,sans-serif; color:#222;
              background:rgba(255,255,255,.85); padding:0 4px; border-radius:2px; }
.nb-tip       { font:12px/1.45 system-ui,sans-serif; color:#222; }
.nb-head      { font-weight:700; margin-bottom:6px; }
.nb-tip table { border-collapse:collapse; }

.nb-meta      { width:100%; }
.nb-meta th   { text-align:left;  font-weight:400; color:#555; padding:1px 10px 1px 0; white-space:nowrap; }
.nb-meta td   { text-align:right; padding:1px 0; font-variant-numeric:tabular-nums; }

.nb-caption     { margin:8px 0 3px; padding-top:6px; border-top:1px solid rgba(0,0,0,.15); color:#555; }
.nb-readings th { font-weight:400; color:#555; text-align:right; padding:1px 0 1px 8px; }
.nb-readings td { text-align:right; padding:1px 0 1px 8px; font-variant-numeric:tabular-nums; }
.nb-readings tr th:first-child,
.nb-readings tr td:first-child { text-align:left; padding-left:0; white-space:nowrap; }
.nb-group th    { text-align:center; padding-bottom:2px; }

.nb-readings .nb-night { border-left:1px solid rgba(0,0,0,.15); padding-left:14px; }
.nb-readings td:nth-child(4),
.nb-readings tr:not(.nb-group) th:nth-child(4) { padding-right:14px; }
</style>
"""

# --------------------------------------------------------------------------
# categorical lookups -- edit these, not the function body
# --------------------------------------------------------------------------
SENSOR = {                       # Type -> (unused glyph, ring colour)
    "Nest":    (None,         "#37474F"),
    "iButton": ("circle-dot", "#5B2D9B"),
    "Intelligent":   ("microchip",  "#C2185B"),
}
EGG_BADGE = ("egg",   "#b08341")
CHICK_BADGE = ("dove", "#0F766E")
DEAD_BADGE = ("skull", "#8a2f2f")

SPECIES = {                      # species code -> (glyph, colour)
    "GT": ("crow", "#4E7A0E"),   # great tit
    "BT": ("crow", "#1565C0"),   # blue tit
}

# temperature ramp for the two top badges (blue -> yellow -> red)
TEMP_RAMP = [(44, 123, 182), (171, 217, 233), (255, 255, 191),
             (253, 174, 97), (215, 25, 28)]
TEMP_DOMAIN = (12.0, 27.0)       # degC; 1st-99th percentile of the daytime means; just fallback


# --------------------------------------------------------------------------
def _missing(value):
    """True for None and for NaN (NaN is the only value not equal to itself)."""
    return value is None or value != value


def temp_color(value, domain=TEMP_DOMAIN):
    """Map a temperature onto TEMP_RAMP, clamped to the domain."""
    low, high = domain
    t = 0.0 if high <= low else (value - low) / (high - low)
    t = min(1.0, max(0.0, t))
    last = len(TEMP_RAMP) - 1
    i = min(int(t * last), last - 1)
    f = t * last - i
    a, b = TEMP_RAMP[i], TEMP_RAMP[i + 1]
    return "#%02x%02x%02x" % tuple(round(a[j] + (b[j] - a[j]) * f) for j in range(3))


def _readable_ink(hex_colour):
    """Pick near-black or near-white for legibility on an arbitrary fill."""
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return "#2b2b2b"

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "#2b2b2b" if luminance > 0.42 else "#f5f5f5"


def nest_icon(
    bird=None,          # FA glyph inside the circle, e.g. "crow"; None = empty nest
    bird_color=None,    # glyph colour, per species; None = auto-contrast vs fill
    fill="#ffffff",     # circle background
    ring=None,          # circle border; None = sensor tier colour
    sensor="Nest",      # "Nest" | "iButton" | "Intelligent"  -> ring colour
    t_in=None,          # mean daytime inside temp   -> NW badge, number
    t_out=None,         # mean daytime outside temp  -> NE badge, number
    eggs=None,          # >0 number, NaN icon, 0 absent  -> SW badge (bottom left)
    chicks=None,        # >0 number, NaN icon, 0 absent  -> S  badge (bottom centre)
    dead=None,          # >0 number, NaN icon, 0 absent  -> SE badge (bottom right)
    label=None,         # optional always-on text to the right
    facing=None,        # compass bearing in degrees     -> arrow on the rim
    temp_domain=TEMP_DOMAIN,
):
    _, sensor_colour = SENSOR[sensor]
    ring = ring or sensor_colour
    ink = bird_color or _readable_ink(fill)

    def count_badge(slot, spec, value):
        """Number when >0, icon when unknown, nothing when 0."""
        glyph, colour = spec
        if _missing(value):
            inner = f'<i class="fa fa-{glyph}"></i>'
        elif value > 0:
            inner = f"{int(round(value))}"
        else:
            return ""
        return f'<div class="nest-badge nest-{slot}" style="--b:{colour}">{inner}</div>'

    def temp_badge(slot, value):
        """Number on a ramp-coloured disc; nothing when there is no reading."""
        if _missing(value):
            return ""
        background = temp_color(value, temp_domain)
        return (f'<div class="nest-temp nest-{slot}" '
                f'style="--b:{background};--t:{_readable_ink(background)}">'
                f'{int(round(value))}</div>')

    glyph = f'<i class="fa fa-{bird}"></i>' if bird else ""
    parts = [f'<div class="nest-cup">{glyph}</div>']
    if facing is not None:
        parts.append('<div class="nest-dir"></div>')   # before the badges, so they occlude it
    parts.append(temp_badge("nw", t_in))
    parts.append(temp_badge("ne", t_out))
    parts.append(count_badge("sw", EGG_BADGE, eggs))
    parts.append(count_badge("s",  CHICK_BADGE, chicks))
    parts.append(count_badge("se", DEAD_BADGE, dead))
    if label:
        parts.append(f'<span class="nest-label">{label}</span>')

    return folium.DivIcon(
        html=(f'<div class="nest" '
              f'style="--fill:{fill};--ring:{ring};--ink:{ink};--rot:{facing or 0}">'
              + "".join(parts) + "</div>"),
        icon_size=(36, 36),
        icon_anchor=(18, 18),
        popup_anchor=(0, -16),
    )


def add_nest_css(m):
    """Inject the stylesheet once per map."""
    m.get_root().header.add_child(folium.Element(CSS_NEST))
