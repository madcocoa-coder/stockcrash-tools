// 米10年国債利回り（月平均、%）。1871-01〜1953-03 は Shiller の Long Interest Rate、1953-04 以降は FRED GS10
import { TABS } from '../core/data.js';

export default {
  id: 'ust10y',
  name: '米10年金利',
  unit: '%',
  axis: 'right',
  scale: 'linear',
  color: '#1a8c80',
  sources: { monthly: { type: 'gviz', gid: TABS.rates, date: '月', value: '米10年金利' } },
};
