import { useEffect, useState } from "react";

interface TrendingRepo {
  full_name: string;
  url: string;
  description: string;
  stars: number;
  language: string;
  category: string;
  risk_level: string;
}

type ReportType = "trending" | "hidden_gems";

export function TrendingPanel() {
  const [repos, setRepos] = useState<TrendingRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [scouting, setScouting] = useState(false);
  const [reportType, setReportType] = useState<ReportType>("trending");
  const [source, setSource] = useState<"snapshot" | "live">("snapshot");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/discovery/trending")
      .then((r) => r.json())
      .then((data) => setRepos(Array.isArray(data) ? data : []))
      .catch(() => setRepos([]))
      .finally(() => setLoading(false));
  }, []);

  const scoutNow = async () => {
    setScouting(true);
    setError(null);
    try {
      const res = await fetch(`/api/intel?report_type=${reportType}&min_stars=100`);
      if (!res.ok) throw new Error(`Scout failed (HTTP ${res.status})`);
      const report = await res.json();
      const found: TrendingRepo[] = (report.repos ?? []).map((r: Record<string, unknown>) => ({
        full_name: (r.full_name as string) ?? (r.name as string) ?? "unknown",
        url: (r.url as string) ?? "#",
        description: (r.description as string) ?? "",
        stars: (r.stars as number) ?? 0,
        language: (r.language as string) ?? "",
        category: (r.category as string) ?? "",
        risk_level: (r.risk_level as string) ?? "",
      }));
      setRepos(found);
      setSource("live");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scout failed");
    } finally {
      setScouting(false);
    }
  };

  const dispatch = (full_name: string) => {
    fetch("/api/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: `run ${full_name}`, payload: { module_id: full_name.replace("/", "_") } }),
    });
  };

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-white">
          {reportType === "hidden_gems" ? "Hidden Gems" : "Trending Repos"}
          {source === "live" && (
            <span className="ml-2 rounded bg-green-900 px-2 py-0.5 text-xs font-normal text-green-300">live</span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value as ReportType)}
            className="rounded border border-gray-700 bg-gray-800 px-2 py-1 text-xs text-gray-200"
            aria-label="Report type"
          >
            <option value="trending">Trending</option>
            <option value="hidden_gems">Hidden Gems</option>
          </select>
          <button
            onClick={scoutNow}
            disabled={scouting}
            className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {scouting ? "Scouting…" : "Scout Now"}
          </button>
        </div>
      </div>

      {error && <p className="mb-2 text-sm text-red-400">{error}</p>}

      {loading ? (
        <div className="p-4 text-sm text-gray-400">Loading trending...</div>
      ) : (
        <div className="space-y-3">
          {repos.length === 0 && (
            <p className="text-sm text-gray-400">
              No repos yet. Click <span className="text-indigo-400">Scout Now</span> to run a live GitHub scout.
            </p>
          )}
          {repos.map((repo) => (
            <div key={repo.full_name} className="rounded border border-gray-800 p-3 hover:border-gray-700">
              <div className="flex items-center justify-between">
                <a href={repo.url} target="_blank" rel="noreferrer" className="font-medium text-blue-400 hover:underline">
                  {repo.full_name}
                </a>
                <span className="text-xs text-yellow-400">★ {repo.stars}</span>
              </div>
              {repo.description && <p className="mt-1 text-sm text-gray-300">{repo.description}</p>}
              <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                {repo.language && <span>{repo.language}</span>}
                {repo.language && repo.category && <span>•</span>}
                {repo.category && <span>{repo.category}</span>}
                {repo.risk_level && <span>•</span>}
                {repo.risk_level && <span className="uppercase">{repo.risk_level}</span>}
              </div>
              <button
                onClick={() => dispatch(repo.full_name)}
                className="mt-2 rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-500"
              >
                Dispatch
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
