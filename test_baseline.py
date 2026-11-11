"""Regression check: reproduces the published baseline and acute-shunt values.

Run with:  python test_baseline.py      (or: pytest)
Takes about 15 seconds.
"""
from model import TWINS, simulate

# (no shunt, 6 mm shunt) at rest
EXPECTED = {
    'HFrEF': dict(CO=(3.86, 3.49), PCWP=(22.7, 16.1), RAP=(9.1, 10.7), mPAP=(33.1, 29.3),
                  LVEDV=(254, 237), LVEF=(19.5, 18.9), QpQs=(1.00, 1.40)),
    'HFpEF': dict(CO=(4.78, 4.46), PCWP=(19.7, 13.7), RAP=(8.9, 10.2), mPAP=(30.6, 26.3),
                  LVEDV=(124, 117), LVEF=(55.3, 54.6), QpQs=(1.00, 1.24)),
}
TOL = dict(CO=0.02, PCWP=0.15, RAP=0.15, mPAP=0.15, LVEDV=1.0, LVEF=0.15, QpQs=0.01)


def test_baseline_and_acute_shunt():
    for kind, p in TWINS.items():
        base, y = simulate(p)
        shunt, _ = simulate(p, 6.0, y0=y)
        for key, (b_exp, s_exp) in EXPECTED[kind].items():
            assert abs(base[key] - b_exp) <= TOL[key], (kind, key, 'base', base[key], b_exp)
            assert abs(shunt[key] - s_exp) <= TOL[key], (kind, key, 'shunt', shunt[key], s_exp)
        # flow continuity at steady state: Qp - Qs equals shunt flow
        assert abs(shunt['Qp'] - shunt['CO'] - shunt['Qsh']) < 0.02, (kind, 'continuity')


if __name__ == '__main__':
    test_baseline_and_acute_shunt()
    print('OK: baseline and acute-shunt values reproduced for both twins.')
