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

export function TrendingPanel() {
  const [repos, setRepos] = useState<TrendingRepo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/discovery/trending")
      .then((r) => r.json())
      .then((data) => setRepos(Array.isArray(data) ? data : []))
      .finally(() => setLoading(false));
  }, []);

  const dispatch = (full_name: string) => {
    fetch("/api/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: `run ${full_name}`, payload: { module_id: full_name.replace("/", "_") } }),
    });
  };

  if (loading) return <div className="p-4 text-sm text-gray-400">Loading trending...</div>;

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <h2 className="mb-3 text-lg font-semibold text-white">Trending Repos</h2>
      <div className="space-y-3">
        {repos.length === 0 && <p className="text-sm text-gray-400">No trending repos discovered yet.</p>}
        {repos.map((repo) => (
          <div key={repo.full_name} className="rounded border border-gray-800 p-3 hover:border-gray-700">
            <div className="flex items-center justify-between">
              <a href={repo.url} target="_blank" rel="noreferrer" className="font-medium text-blue-400 hover:underline">
                {repo.full_name}
              </a>
              <span className="text-xs text-yellow-400">★ {repo.stars}</span>
            </div>
            <p className="mt-1 text-sm text-gray-300">{repo.description}</p>
            <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
              <span>{repo.language}</span>
              <span>•</span>
              <span>{repo.category}</span>
              <span>•</span>
              <span className="uppercase">{repo.risk_level}</span>
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
    </div>
  );
}
