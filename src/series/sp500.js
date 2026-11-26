// S&P500 名目終値（配当なし・インフレ調整なし）
import { TABS } from '../core/data.js';

export default {
  id: 'sp500',
  name: 'S&P500',
  unit: 'pt',
  axis: 'left',
  scale: 'log',
  color: '#233b5e',
  sources: {
    // 1871-01〜1927-12 は Shiller 月次平均、1928-01 以降は月末終値（日付は毎月1日）
    monthly: { type: 'gviz', gid: TABS.monthly, date: '月', value: '終値' },
    // 1927-12-30〜。期間で絞るときは列記号（A,B）で gviz のクエリを組む
    daily: { type: 'gviz', gid: TABS.daily, date: '日付', value: '終値', cols: ['A', 'B'] },
  },
};
