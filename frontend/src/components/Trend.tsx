import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface Props { data: Record<string, unknown>[]; x: string; y: string; color?: string; area?: boolean; unit?: string; }
export function Trend({ data, x, y, color = '#9de5b3', area = true, unit = '' }: Props) {
  if (!data.length) return <div className="chart-empty">En attente de mesures</div>;
  const content = <>
    <CartesianGrid stroke="var(--line)" strokeDasharray="3 5" vertical={false}/>
    <XAxis dataKey={x} minTickGap={48} tick={{ fill: 'var(--muted)', fontSize: 10 }} axisLine={false} tickLine={false}/>
    <YAxis width={56} tick={{ fill: 'var(--muted)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => Number(v).toFixed(2)}/>
    <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 9, color: 'var(--text)' }} formatter={(value: number) => [value.toFixed(4) + unit, y]}/>
    {area ? <Area type="linear" dataKey={y} stroke={color} strokeWidth={1.8} fill={color} fillOpacity={0.09} isAnimationActive={false}/> : <Line type="linear" dataKey={y} stroke={color} strokeWidth={1.4} dot={false} isAnimationActive={false}/>}
  </>;
  return <div className="chart"><ResponsiveContainer width="100%" height="100%">{area ? <AreaChart data={data}>{content}</AreaChart> : <LineChart data={data}>{content}</LineChart>}</ResponsiveContainer></div>;
}
