from branca.element import MacroElement
from folium.template import Template

# metric -> (Font Awesome glyph, colour, tooltip text). Colours match the marker badges.
METRICS = (
    ("Eggs",   "egg",   "#b08341", "eggs"),
    ("Chicks", "dove",  "#0F766E", "chicks"),
    ("Deaths", "skull", "#8a2f2f", "deaths"),
)


class YearlyStats(MacroElement):
    """Panel at the bottom of the map with the yearly average and maximum per metric.

    ``stats`` maps a year to ``{"avg": {metric: text}, "max": {metric: text}}``.
    The panel follows the year selected in the GroupedLayerControl.
    """

    _template = Template("""
        {% macro header(this,kwargs) %}
        <style>
        .yearly-stats { display:inline-flex; align-items:center; gap:10px;
                        background:rgba(255,255,255,.88); padding:5px 10px; border-radius:4px;
                        font:12px/1.4 system-ui,sans-serif; color:#222; white-space:nowrap; }
        .yearly-stats .ys-year { font-size:15px; font-weight:600;
                                 padding-right:9px; border-right:1px solid rgba(0,0,0,.18); }
        .yearly-stats table { border-collapse:collapse; }
        .yearly-stats th, .yearly-stats td { padding:0 0 0 11px; text-align:right; font-weight:400; }
        .yearly-stats thead th { padding-bottom:2px; }
        .yearly-stats tbody th { text-align:left; padding:0 2px 0 0; color:#666; font-size:11px; }
        .yearly-stats td { font-variant-numeric:tabular-nums; }
        </style>
        {% endmacro %}

        {% macro script(this,kwargs) %}
            var {{ this.get_name() }} = L.control({ position: '{{ this.position }}' });
            {{ this.get_name() }}.onAdd = function (map) {
                var stats   = {{ this.stats|tojson }};
                var metrics = {{ this.metrics|tojson }};
                var box = L.DomUtil.create('div', 'yearly-stats');

                function row(label, values) {
                    var cells = metrics.map(function (m) {
                        return '<td>' + values[m[0]] + '</td>';
                    }).join('');
                    return '<tr><th>' + label + '</th>' + cells + '</tr>';
                }

                function show(year) {
                    var s = stats[year];
                    if (!s) { box.innerHTML = ''; return; }
                    var head = metrics.map(function (m) {
                        return '<th><i class="fa fa-' + m[1] + '" style="color:' + m[2] +
                               '" title="' + m[3] + '"></i></th>';
                    }).join('');
                    box.innerHTML =
                        '<span class="ys-year">' + year + '</span>' +
                        '<table><thead><tr><th></th>' + head + '</tr></thead><tbody>' +
                        row('&empty;', s.avg) + row('max', s.max) +
                        '</tbody></table>';
                }

                show({{ this.initial|tojson }});
                map.on('overlayadd', function (e) { if (stats[e.name]) { show(e.name); } });
                L.DomEvent.disableClickPropagation(box);
                return box;
            };
            {{ this.get_name() }}.addTo({{ this._parent.get_name() }});
        {% endmacro %}
    """)

    def __init__(self, stats, initial, position="bottomright", metrics=METRICS):
        super().__init__()
        self._name = "YearlyStats"
        self.stats = stats
        self.initial = str(initial)
        self.position = position
        self.metrics = [list(m) for m in metrics]
