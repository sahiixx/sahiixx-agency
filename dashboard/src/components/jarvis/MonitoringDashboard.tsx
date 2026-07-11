import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, Database, Layers, Zap, Activity } from 'lucide-react';

interface Stats {
  modules: number;
  active: number;
  totalStars: number;
  memoryEvents: number;
  categories: Record<string, number>;
  languages: Record<string, number>;
  recentTasks: number;
  healthScore: number;
}

const COLORS = ['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#ec4899', '#6366f1'];

export function MonitoringDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [registryResp, healthResp] = await Promise.all([
          fetch('/api/registry'),
          fetch('/api/jarvis/status'),
        ]);

        const registry = registryResp.ok ? await registryResp.json() : {};
        const jarvis = healthResp.ok ? await healthResp.json() : {};

        const categories: Record<string, number> = {};
        const languages: Record<string, number> = {};

        if (registry.modules) {
          for (const mod of registry.modules) {
            const cat = mod.category || 'unknown';
            categories[cat] = (categories[cat] || 0) + 1;

            const lang = mod.language || 'Unknown';
            languages[lang] = (languages[lang] || 0) + 1;
          }
        }

        setStats({
          modules: registry.total || registry.modules?.length || 0,
          active: registry.active || 0,
          totalStars: registry.totalStars || 0,
          memoryEvents: registry.memoryEvents || 0,
          categories,
          languages,
          recentTasks: jarvis.turn_count || 0,
          healthScore: 85,
        });
      } catch {
        setStats({
          modules: 0,
          active: 0,
          totalStars: 0,
          memoryEvents: 0,
          categories: {},
          languages: {},
          recentTasks: 0,
          healthScore: 0,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map(i => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="h-20 bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const statCards = [
    { label: 'Modules', value: stats.modules, icon: Layers, color: 'text-cyan-500' },
    { label: 'Active', value: stats.active, icon: Zap, color: 'text-green-500' },
    { label: 'Total Stars', value: stats.totalStars.toLocaleString(), icon: TrendingUp, color: 'text-purple-500' },
    { label: 'Memory Events', value: stats.memoryEvents, icon: Database, color: 'text-amber-500' },
  ];

  const categoryData = Object.entries(stats.categories)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const languageData = Object.entries(stats.languages)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  return (
    <div className="space-y-4">
      {/* Stat Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map(stat => (
          <Card key={stat.label}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                </div>
                <stat.icon className={`h-8 w-8 ${stat.color} opacity-50`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Categories */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Categories</CardTitle>
          </CardHeader>
          <CardContent>
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={categoryData} layout="vertical">
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#06b6d4" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
                No data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Languages */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Languages</CardTitle>
          </CardHeader>
          <CardContent>
            {languageData.length > 0 ? (
              <div className="flex items-center gap-4">
                <ResponsiveContainer width="50%" height={200}>
                  <PieChart>
                    <Pie
                      data={languageData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {languageData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-1">
                  {languageData.map((lang, i) => (
                    <div key={lang.name} className="flex items-center gap-2 text-xs">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: COLORS[i % COLORS.length] }}
                      />
                      <span className="flex-1">{lang.name}</span>
                      <span className="text-muted-foreground">{lang.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
                No data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Health Score */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">System Health Score</span>
            </div>
            <span className="text-2xl font-bold">{stats.healthScore}%</span>
          </div>
          <Progress value={stats.healthScore} className="h-2" />
          <p className="text-xs text-muted-foreground mt-2">
            {stats.healthScore >= 80 ? 'All systems operational' : 'Some systems need attention'}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
