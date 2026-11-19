"""
CardioSight Shunt Digital Twin - desktop interface.

Tab 1, Scenario builder: tune one patient (twin, valve disease, rhythm, patient modifiers),
add a shunt and therapies (BAT, sotatercept, PADN), and compare against the same patient
untreated: hemodynamic table, PV loops and pressure waveforms.
Tab 2, Paper scripts: run the run_*.py scripts that reproduce the paper tables.

Research model only. Not validated against patient data. Not for clinical use.
"""
import json
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, scrolledtext, filedialog

import scenario as sc

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False

PROJECT = Path(__file__).parent
INF = float('inf')

# (label, metric key, format) for the results table
ROWS = [
    ('Systemic', None, None),
    ('Heart rate (bpm)', 'HR', '{:.0f}'),
    ('Cardiac output, forward (L/min)', 'CO', '{:.2f}'),
    ('Forward stroke volume (mL)', 'LVFSV', '{:.0f}'),
    ('Mean arterial pressure (mmHg)', 'MAP', '{:.0f}'),
    ('Aortic systolic / diastolic', ('AoS', 'AoD'), '{:.0f}/{:.0f}'),
    ('SVR (WU)', 'SVR_WU', '{:.1f}'),
    ('Left heart', None, None),
    ('PCWP = mean LA pressure (mmHg)', 'PCWP', '{:.1f}'),
    ('LA v-wave (mmHg)', 'LAv', '{:.0f}'),
    ('LVEDP (mmHg)', 'LVEDP', '{:.1f}'),
    ('LVEDV / LVESV (mL)', ('LVEDV', 'LVESV'), '{:.0f}/{:.0f}'),
    ('LVEF (%)', 'LVEF', '{:.0f}'),
    ('LA max volume (mL)', 'LAmax', '{:.0f}'),
    ('LV Ees / Ea (mmHg/mL)', ('LV_Ees', 'LV_Ea'), '{:.2f}/{:.2f}'),
    ('Right heart and lungs', None, None),
    ('RAP mean (mmHg)', 'RAP', '{:.1f}'),
    ('PA systolic / diastolic (mmHg)', ('PAs', 'PAd'), '{:.0f}/{:.0f}'),
    ('mPAP (mmHg)', 'mPAP', '{:.1f}'),
    ('PVR (WU)', 'PVR_WU', '{:.2f}'),
    ('RVEDV (mL)', 'RVEDV', '{:.0f}'),
    ('RVEF (%)', 'RVEF', '{:.0f}'),
    ('RA max volume (mL)', 'RAmax', '{:.0f}'),
    ('RV Ees / Ea (mmHg/mL)', ('RV_Ees', 'RV_Ea'), '{:.2f}/{:.2f}'),
    ('RV-PA coupling Ees/Ea', 'RV_coupling', '{:.2f}'),
    ('Shunt and valves', None, None),
    ('Qp/Qs', 'QpQs', '{:.2f}'),
    ('Shunt flow (L/min)', 'Qsh', '{:.2f}'),
    ('LA-RA gradient (mmHg)', 'LA_RA', '{:.1f}'),
    ('MR regurgitant volume (mL) / RF (%)', ('MR_RVol', 'MR_RF'), '{:.0f}/{:.0f}'),
    ('TR regurgitant volume (mL) / RF (%)', ('TR_RVol', 'TR_RF'), '{:.0f}/{:.0f}'),
    ('Pericardial pressure (mmHg)', 'Pperi', '{:.1f}'),
    ('Added stressed volume vs untreated (mL)', 'dV', '{:+.0f}'),
]

SCRIPTS = [
    ("test_baseline.py", "Test Baseline", "Verify installation (~15 s)", False),
    ("run_acute.py", "Acute Effects at Rest", "Baseline vs shunt, both twins (~15 s)", False),
    ("run_rv_compliance.py", "RV Compliance Study", "Right-heart compliance (few min)", False),
    ("run_scenarios.py", "Exercise & Disease Scenarios", "Exercise, PVD, volume retention (few min)", False),
    ("run_reflex.py", "Reflex Mechanisms", "Cardiac vs volume arm gain sweep (few min)", False),
    ("run_echo_matrix.py", "Echo Matrix Analysis", "Match trial echocardiograms (few min)", False),
    ("run_bat.py", "BAT + Shunt", "Baroreflex activation (~7 min)", False),
    ("run_la_volume.py", "LA Volume Mechanisms", "Retention and septal interaction (~5 min)", True),
    ("run_af.py", "Atrial Fibrillation", "Loss of atrial contraction (~3 min)", True),
    ("run_padn.py", "PADN + Shunt", "Pulmonary artery denervation (~3 min)", True),
    ("run_triple.py", "Shunt + BAT + PADN", "Triple therapy (~4 min)", True),
    ("run_coupling.py", "Ventriculo-arterial Coupling", "Ees/Ea for triple-therapy arms (~4 min)", True),
]


def fmt(m, key, f):
    if isinstance(key, tuple):
        return f.format(*(m.get(k, float('nan')) for k in key))
    return f.format(m.get(key, float('nan')))


class ScrollFrame(ttk.Frame):
    """Vertically scrollable frame for the control panel."""
    def __init__(self, parent, width=380):
        super().__init__(parent)
        canvas = tk.Canvas(self, width=width, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.inner, anchor='nw')
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side='left', fill='both', expand=True)
        bar.pack(side='right', fill='y')
        wheel = lambda e: canvas.yview_scroll(int(-e.delta / 120), 'units')
        self.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', wheel))
        self.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))


class ScenarioTab(ttk.Frame):
    def __init__(self, parent, status):
        super().__init__(parent)
        self.status = status
        self.v = {}
        self.result = None
        self.busy = False
        panel = ScrollFrame(self)
        panel.pack(side='left', fill='y', padx=(6, 0), pady=6)
        self._controls(panel.inner)
        right = ttk.Frame(self)
        right.pack(side='left', fill='both', expand=True, padx=6, pady=6)
        self._results(right)
        self.reset()

    # ---------------------------------------------------------------- controls
    def _var(self, key, kind='str'):
        var = {'str': tk.StringVar, 'bool': tk.BooleanVar, 'float': tk.DoubleVar}[kind]()
        self.v[key] = var
        return var

    def _combo(self, f, r, label, key, values, cmd=None):
        ttk.Label(f, text=label).grid(row=r, column=0, sticky='w', pady=2)
        cb = ttk.Combobox(f, textvariable=self._var(key), values=values, state='readonly', width=12)
        cb.grid(row=r, column=1, columnspan=2, sticky='w', pady=2)
        if cmd:
            cb.bind('<<ComboboxSelected>>', cmd)
        return cb

    def _check(self, f, r, label, key):
        ttk.Checkbutton(f, text=label, variable=self._var(key, 'bool')).grid(
            row=r, column=0, columnspan=3, sticky='w', pady=2)

    def _entry(self, f, r, label, key, hint=''):
        ttk.Label(f, text=label).grid(row=r, column=0, sticky='w', pady=2)
        ttk.Entry(f, textvariable=self._var(key), width=8).grid(row=r, column=1, sticky='w', pady=2)
        if hint:
            ttk.Label(f, text=hint, foreground='gray').grid(row=r, column=2, sticky='w', padx=4)

    def _slider(self, f, r, label, key, lo, hi, step, unit=''):
        ttk.Label(f, text=label).grid(row=r, column=0, sticky='w', pady=2)
        var = self._var(key, 'float')
        show = ttk.Label(f, width=7)
        show.grid(row=r, column=2, sticky='w', padx=4)

        def snap(_=None):
            x = round(var.get() / step) * step
            var.set(x)
            show.config(text=(f'{x:g}{unit}' if unit != '%' else f'{x * 100:.0f}%'))
        ttk.Scale(f, from_=lo, to=hi, variable=var, length=130, command=snap).grid(
            row=r, column=1, sticky='w', pady=2)
        var.trace_add('write', lambda *a: show.config(
            text=(f'{var.get():g}{unit}' if unit != '%' else f'{var.get() * 100:.0f}%')))

    def _frame(self, parent, text):
        f = ttk.LabelFrame(parent, text=text, padding=6)
        f.pack(fill='x', pady=4)
        f.columnconfigure(0, minsize=170)
        return f

    def _controls(self, p):
        f = self._frame(p, 'Patient')
        self._combo(f, 0, 'Phenotype (twin)', 'twin', ['HFpEF', 'HFrEF'], self._twin_changed)
        self._combo(f, 1, 'Rhythm', 'rhythm', ['sinus', 'atrial fibrillation'])
        self._combo(f, 2, 'State', 'state', ['rest', 'exercise'])
        self._check(f, 3, 'Pulmonary vascular disease on exercise', 'pvd')

        f = self._frame(p, 'Interatrial shunt')
        self._slider(f, 0, 'Diameter', 'shunt_mm', 0, 10, 0.5, ' mm')
        self._entry(f, 1, 'Discharge coefficient Cd', 'shunt_cd', '0.7 sharp-edged')
        self._check(f, 2, 'Chronic adaptation (reflex volume + PVR rise)', 'chronic')
        self._entry(f, 3, 'Volume-arm gain (mL/mmHg)', 'gain', "'inf' = restore MAP")
        self._entry(f, 4, 'Post-shunt PVR rise (%)', 'pvr_rise')

        f = self._frame(p, 'Valve disease')
        self._combo(f, 0, 'Mitral regurgitation', 'mr', list(sc.MR_EROA), lambda e: self._sev('mr'))
        self._entry(f, 1, '   MR EROA (cm²)', 'mr_eroa')
        self._combo(f, 2, 'Tricuspid regurgitation', 'tr', list(sc.TR_EROA), lambda e: self._sev('tr'))
        self._entry(f, 3, '   TR EROA (cm²)', 'tr_eroa')
        self._check(f, 4, 'Chronic compensation of valve disease/AF', 'lesion_comp')
        self._entry(f, 5, '   Compensation gain (mL/mmHg)', 'lesion_gain', "'inf' = restore MAP")

        f = self._frame(p, 'Therapies')
        self._slider(f, 0, 'Baroreflex activation (BAT)', 'bat', 0, 1, 0.05, '%')
        self._slider(f, 1, 'Sotatercept effect', 'sota', 0, 1, 0.05, '%')
        self._check(f, 2, 'Pulmonary artery denervation (PADN)', 'padn')

        f = self._frame(p, 'Patient modifiers (multipliers on the twin)')
        self._entry(f, 0, 'Heart rate (bpm)', 'hr', 'blank = twin')
        rows = [('LV contractility (Ees ×)', 'lv_ees'), ('LV diastolic stiffness (B ×)', 'lv_stiff'),
                ('RV contractility (Ees ×)', 'rv_ees'), ('RV diastolic stiffness (B ×)', 'rv_stiff'),
                ('LA stiffness (B ×)', 'la_stiff'), ('RA stiffness (B ×)', 'ra_stiff'),
                ('SVR ×', 'svr'), ('PVR ×', 'pvr'), ('PA compliance ×', 'cpa'),
                ('Venous capacitance ×', 'csv'), ('Stressed volume change (mL)', 'dsbv')]
        for i, (lab, key) in enumerate(rows, start=1):
            self._entry(f, i, lab, key)
        self._check(f, len(rows) + 1, 'Pericardial constraint', 'pericardium')
        self._entry(f, len(rows) + 2, 'Septal interaction β (rest)', 'septum', '0-0.5')

        f = self._frame(p, 'Therapy effect-size assumptions (at full strength)')
        for i, (lab, key) in enumerate([('BAT: SVR reduction (%)', 'bat_svr'), ('BAT: HR reduction (%)', 'bat_hr'),
                                        ('BAT: stressed volume reduction (%)', 'bat_sbv'),
                                        ('PADN: resting PVR reduction (%)', 'padn_pvr'),
                                        ('Sotatercept: max PVR reduction (%)', 'sota_pvr')]):
            self._entry(f, i, lab, key)

        b = ttk.Frame(p)
        b.pack(fill='x', pady=8)
        self.run_btn = ttk.Button(b, text='Run scenario', command=self.run)
        self.run_btn.pack(side='left')
        ttk.Button(b, text='Reset', command=self.reset).pack(side='left', padx=6)
        ttk.Button(b, text='Save results…', command=self.save).pack(side='left')

    def _sev(self, valve):
        table = sc.MR_EROA if valve == 'mr' else sc.TR_EROA
        self.v[valve + '_eroa'].set(f"{table[self.v[valve].get()]:.2f}")

    def _twin_changed(self, _=None):
        fit = sc.FIT[self.v['twin'].get()]
        self.v['gain'].set('inf' if fit['gain'] == INF else f"{fit['gain']:g}")
        self.v['pvr_rise'].set(f"{fit['pvr_rise'] * 100:g}")

    def reset(self):
        d = sc.DEFAULTS
        for k in ('twin', 'state', 'mr', 'tr'):
            self.v[k].set(d[k])
        self.v['rhythm'].set('sinus')
        for k in ('pvd', 'chronic', 'lesion_comp', 'padn', 'pericardium'):
            self.v[k].set(d[k])
        for k in ('shunt_mm', 'bat', 'sota'):
            self.v[k].set(d[k])
        self.v['lesion_gain'].set(f"{d['lesion_gain']:g}")
        for k in ('shunt_cd', 'lv_ees', 'lv_stiff', 'rv_ees', 'rv_stiff', 'la_stiff', 'ra_stiff',
                  'svr', 'pvr', 'cpa', 'csv', 'dsbv', 'septum'):
            self.v[k].set(f'{d[k]:g}')
        self.v['hr'].set('')
        for k in ('bat_svr', 'bat_hr', 'bat_sbv', 'padn_pvr', 'sota_pvr'):
            self.v[k].set(f'{d[k] * 100:g}')
        self._sev('mr')
        self._sev('tr')
        self._twin_changed()

    def settings(self):
        g = lambda k: self.v[k].get()
        num = lambda k: float(str(g(k)).strip())
        s = dict(twin=g('twin'), state=g('state'), pvd=g('pvd'), afib=g('rhythm') != 'sinus',
                 shunt_mm=float(g('shunt_mm')), shunt_cd=num('shunt_cd'),
                 mr=g('mr'), tr=g('tr'), mr_eroa=num('mr_eroa'), tr_eroa=num('tr_eroa'),
                 lesion_comp=g('lesion_comp'), bat=float(g('bat')), sota=float(g('sota')), padn=g('padn'),
                 chronic=g('chronic'), pericardium=g('pericardium'),
                 hr=num('hr') if str(g('hr')).strip() else None)
        gain = str(g('gain')).strip().lower()
        s['gain'] = INF if gain in ('inf', '∞') else float(gain)
        lg = str(g('lesion_gain')).strip().lower()
        s['lesion_gain'] = INF if lg in ('inf', '∞') else float(lg)
        s['pvr_rise'] = num('pvr_rise') / 100
        for k in ('lv_ees', 'lv_stiff', 'rv_ees', 'rv_stiff', 'la_stiff', 'ra_stiff',
                  'svr', 'pvr', 'cpa', 'csv', 'dsbv', 'septum'):
            s[k] = num(k)
        for k in ('bat_svr', 'bat_hr', 'bat_sbv', 'padn_pvr', 'sota_pvr'):
            s[k] = num(k) / 100
        if not 0 <= s['shunt_mm'] <= 10:
            raise ValueError('Shunt diameter must be 0-10 mm')
        if not 0 <= s['septum'] <= 0.5:
            raise ValueError('Septal interaction β must be 0-0.5')
        for k in ('lv_ees', 'lv_stiff', 'rv_ees', 'rv_stiff', 'la_stiff', 'ra_stiff', 'svr', 'pvr', 'cpa', 'csv'):
            if s[k] <= 0:
                raise ValueError(f'{k} multiplier must be > 0')
        return s

    # ---------------------------------------------------------------- results
    def _results(self, p):
        top = ttk.Frame(p)
        top.pack(fill='both', expand=False)
        cols = ('untreated', 'scenario', 'change')
        self.tree = ttk.Treeview(top, columns=cols, height=18)
        self.tree.heading('#0', text='Measure')
        self.tree.column('#0', width=270)
        for c, w in zip(cols, (110, 110, 90)):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor='e')
        self.tree.tag_configure('hdr', background='#e8eef6', font=('Segoe UI', 9, 'bold'))
        self.tree.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(top, orient='vertical', command=self.tree.yview)
        sb.pack(side='left', fill='y')
        self.tree.configure(yscrollcommand=sb.set)
        self.notes = scrolledtext.ScrolledText(top, wrap='word', width=42, height=18, font=('Segoe UI', 9))
        self.notes.pack(side='left', fill='both', padx=(6, 0))
        self.notes.insert('end', 'Set up a patient and therapies on the left, then press "Run scenario".\n\n'
                                 'The untreated column is the same patient (twin, modifiers, valve disease, '
                                 'rhythm, rest/exercise) with no shunt and no therapy.\n\n'
                                 'A run takes about 10-60 s; chronic shunt adaptation and valve compensation '
                                 'solve for retained volume and take longest.\n\n'
                                 'Research model only. Not for clinical use.')
        if HAVE_MPL:
            self.fig = Figure(figsize=(9, 4.6), dpi=90)
            self.canvas = FigureCanvasTkAgg(self.fig, master=p)
            self.canvas.get_tk_widget().pack(fill='both', expand=True, pady=(6, 0))
        else:
            ttk.Label(p, text='Install matplotlib for PV loops and waveforms: pip install matplotlib').pack()

    def run(self):
        if self.busy:
            return
        try:
            s = self.settings()
        except ValueError as e:
            messagebox.showerror('Invalid input', str(e))
            return
        self.busy = True
        self.run_btn.config(state='disabled')
        self.status.set('Running scenario...')
        threading.Thread(target=self._work, args=(s,), daemon=True).start()

    def _work(self, s):
        log = lambda msg: self.after(0, self.status.set, msg)
        try:
            out = sc.run_scenario(s, log=log)
            self.after(0, self._show, out)
        except Exception as e:                                   # noqa: BLE001
            self.after(0, messagebox.showerror, 'Simulation failed', repr(e))
            self.after(0, self.status.set, 'Simulation failed')
        finally:
            self.after(0, self._done)

    def _done(self):
        self.busy = False
        self.run_btn.config(state='normal')

    def _show(self, out):
        self.result = out
        b, r = out['base'], out['scen']
        self.tree.delete(*self.tree.get_children())
        for lab, key, f in ROWS:
            if key is None:
                self.tree.insert('', 'end', text=lab, values=('', '', ''), tags=('hdr',))
                continue
            keys = key if isinstance(key, tuple) else (key,)
            dfmt = lambda x: f'{x:+.2f}' if abs(x) < 10 else f'{x:+.0f}'
            dtxt = '' if key == 'dV' else '/'.join(dfmt(r.get(k, 0) - b.get(k, 0)) for k in keys)
            self.tree.insert('', 'end', text=lab, values=(fmt(b, key, f), fmt(r, key, f), dtxt))
        s = out['settings']
        lines = [f"{s['twin']}, {s['state']}{' + PVD' if s['state'] == 'exercise' and s['pvd'] else ''}, "
                 f"{'AF' if s['afib'] else 'sinus'}",
                 f"Shunt {s['shunt_mm']:g} mm (Cd {s['shunt_cd']:g}), {'chronic' if s['chronic'] else 'acute'}; "
                 f"BAT {s['bat'] * 100:.0f}%, sotatercept {s['sota'] * 100:.0f}%, PADN {'yes' if s['padn'] else 'no'}",
                 f"Reflex: gain {out['info']['gain']:g} mL/mmHg, PVR rise applied {out['info']['pvr_rise'] * 100:.0f}%, "
                 f"retained volume {out['info']['dV']:.0f} mL", '']
        for v, key in (('MR', 'MR'), ('TR', 'TR')):
            if out['info'][key + '_EROA'] > 0:
                for col, m in (('untreated', b), ('scenario', r)):
                    lines.append(f"{v} EROA {out['info'][key + '_EROA']:.2f} cm² → {col}: RVol {m[key + '_RVol']:.0f} mL, "
                                 f"RF {m[key + '_RF']:.0f}% = {sc.classify(v, m[key + '_RVol'], m[key + '_RF'])}")
        lines += out['notes'] + ['', 'BAT, PADN and sotatercept effects are assumed sizes, not fitted to trial data.']
        self.notes.delete('1.0', 'end')
        self.notes.insert('end', '\n'.join(lines))
        self._plot(b['trace'], r['trace'])
        self.status.set('Done')

    def _plot(self, tb, tr):
        if not HAVE_MPL:
            return
        fig = self.fig
        fig.clear()
        axs = fig.subplots(1, 4)
        spec = [('LV PV loop', [('VLV', 'PLV', 'C3')]), ('RV PV loop', [('VRV', 'PRV', 'C0')]),
                ('Atrial PV loops', [('VLA', 'PLA', 'C1'), ('VRA', 'PRA', 'C2')])]
        for ax, (title, curves) in zip(axs, spec):
            for vk, pk, c in curves:
                ax.plot(tb[vk], tb[pk], '--', color=c, lw=1, alpha=0.7)
                ax.plot(tr[vk], tr[pk], '-', color=c, lw=1.6, label=vk[1:])
            ax.set_title(title, fontsize=9)
            ax.set_xlabel('Volume (mL)', fontsize=8)
            ax.tick_params(labelsize=7)
        axs[0].set_ylabel('Pressure (mmHg)', fontsize=8)
        axs[2].legend(fontsize=7, loc='upper left')
        ax = axs[3]
        for pk, c, lab in (('PLA', 'C1', 'LA'), ('PRA', 'C2', 'RA'), ('PPA', 'C4', 'PA')):
            ax.plot(tb['t'], tb[pk], '--', color=c, lw=1, alpha=0.7)
            ax.plot(tr['t'], tr[pk], '-', color=c, lw=1.6, label=lab)
        ax.set_title('Pressures over one beat', fontsize=9)
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7, loc='upper right')
        fig.suptitle('solid = scenario, dashed = untreated', fontsize=8, y=0.995)
        fig.tight_layout()
        self.canvas.draw()

    def save(self):
        if not self.result:
            messagebox.showinfo('Nothing to save', 'Run a scenario first.')
            return
        (PROJECT / 'results').mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(initialdir=PROJECT / 'results', defaultextension='.json',
                                            filetypes=[('JSON', '*.json')], initialfile='scenario.json')
        if not path:
            return
        out = dict(self.result)
        s = dict(out['settings'])
        s['gain'], s['lesion_gain'] = str(s['gain']), str(s['lesion_gain'])
        info = dict(out['info'], gain=str(out['info']['gain']))
        Path(path).write_text(json.dumps(dict(settings=s, info=info, notes=out['notes'],
                                              untreated=out['base'], scenario=out['scen']), indent=1))
        self.status.set(f'Saved {path}')


class ScriptsTab(ttk.Frame):
    """The original launcher: run the paper-reproduction scripts."""
    def __init__(self, parent, status):
        super().__init__(parent, padding=10)
        self.status = status
        c = ttk.LabelFrame(self, text='Paper scripts', padding=10)
        c.pack(fill='x')
        ttk.Label(c, text='Shunt diameter (mm):').grid(row=0, column=0, sticky='w')
        self.d = tk.StringVar(value='6')
        ttk.Entry(c, textvariable=self.d, width=8).grid(row=0, column=1, sticky='w')
        ttk.Label(c, text='Twin (for per-twin scripts):').grid(row=0, column=2, sticky='e', padx=(20, 4))
        self.twin = tk.StringVar(value='HFpEF')
        ttk.Combobox(c, textvariable=self.twin, values=['HFpEF', 'HFrEF'], state='readonly',
                     width=8).grid(row=0, column=3, sticky='w')
        for i, (script, name, desc, per_twin) in enumerate(SCRIPTS, start=1):
            ttk.Button(c, text=name, width=30, command=lambda s=script, t=per_twin: self.run(s, t)).grid(
                row=i, column=0, columnspan=2, sticky='w', pady=2)
            ttk.Label(c, text=desc + (' — per twin' if per_twin else '')).grid(
                row=i, column=2, columnspan=2, sticky='w', padx=10)
        self.out = scrolledtext.ScrolledText(self, wrap='none', font=('Consolas', 9), height=18)
        self.out.pack(fill='both', expand=True, pady=(10, 0))

    def run(self, script, per_twin):
        try:
            d = self.d.get().strip()
            float(d)
        except ValueError:
            messagebox.showerror('Invalid input', 'Shunt diameter must be a number')
            return
        cmd = [sys.executable, str(PROJECT / script)]
        if script != 'test_baseline.py':
            cmd += ([self.twin.get()] if per_twin else []) + [d]
        self.out.delete('1.0', 'end')
        self.out.insert('end', ' '.join(Path(c).name if i < 2 else c for i, c in enumerate(cmd)) + '\n\n')
        self.status.set(f'Running {script}...')
        threading.Thread(target=self._proc, args=(cmd, script), daemon=True).start()

    def _proc(self, cmd, script):
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    cwd=str(PROJECT), bufsize=1)
            for line in proc.stdout:
                self.after(0, self._append, line)
            proc.wait()
            msg = f'{script} finished' if proc.returncode == 0 else f'{script} failed'
            self.after(0, self.status.set, msg)
        except Exception as e:                                   # noqa: BLE001
            self.after(0, self.status.set, f'Error: {e}')

    def _append(self, text):
        self.out.insert('end', text)
        self.out.see('end')


def main():
    root = tk.Tk()
    root.title('CardioSight Shunt Digital Twin Simulator')
    root.geometry('1500x900')
    try:
        root.iconbitmap(str(PROJECT / 'cardiosight_icon.ico'))
    except tk.TclError:
        pass
    status = tk.StringVar(value='Ready.  Research model only — not for clinical use.')
    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True)
    nb.add(ScenarioTab(nb, status), text='  Scenario builder  ')
    nb.add(ScriptsTab(nb, status), text='  Paper scripts  ')
    ttk.Label(root, textvariable=status, relief='sunken', anchor='w').pack(fill='x', side='bottom')
    root.mainloop()


if __name__ == '__main__':
    main()
