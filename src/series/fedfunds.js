// 米政策金利（FF金利の月平均、%）。FRED FEDFUNDS、1954-07 以降
import { TABS } from '../core/data.js';

export default {
  id: 'ff',
  name: '政策金利',
  unit: '%',
  axis: 'right',
  scale: 'linear',
  color: '#6b4fa0',
  sources: { monthly: { type: 'gviz', gid: TABS.rates, date: '月', value: '政策金利' } },
};
