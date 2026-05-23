import { useQuery } from "@tanstack/react-query";
import { fetchModelsCatalog, fetchModelsCoverage, type CoverageCell } from "../api";
import { ModelCard } from "../components/ModelCard";

function qualityLabel(q: CoverageCell["quality"]): string {
  switch (q) {
    case "high":
      return "High";
    case "medium":
      return "Medium";
    case "low":
      return "Low";
    default:
      return "—";
  }
}

export function ModelsPage() {
  const catalogQuery = useQuery({
    queryKey: ["models-catalog"],
    queryFn: fetchModelsCatalog,
  });

  const coverageQuery = useQuery({
    queryKey: ["models-coverage"],
    queryFn: fetchModelsCoverage,
  });

  return (
    <div className="page">
      <header className="page-header">
        <h1>Models & Language Coverage</h1>
        <p className="muted">
          Compare translation models, BLEU quality scores, and supported target languages.
        </p>
      </header>

      <section className="card">
        <h2>Models</h2>
        {catalogQuery.isLoading && <p className="muted">Loading…</p>}
        <div className="model-grid model-grid--catalog">
          {catalogQuery.data?.items.map((m) => (
            <ModelCard
              key={m.id}
              model={m}
              selected={false}
              onSelect={() => {}}
              selectable={false}
            />
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Language pair coverage</h2>
        <p className="muted coverage-legend">
          <span className="dot dot--high" /> High (&gt;40 BLEU)
          <span className="dot dot--medium" /> Medium (20–40)
          <span className="dot dot--low" /> Low (&lt;20)
          <span className="dot dot--none" /> Not supported
        </p>
        {coverageQuery.isLoading && <p className="muted">Loading matrix…</p>}
        {coverageQuery.data && (
          <div className="table-wrap">
            <table className="coverage-table">
              <thead>
                <tr>
                  <th>Model</th>
                  {coverageQuery.data.languages.map((lang) => (
                    <th key={lang.code}>{lang.name_en}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {coverageQuery.data.items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.display_name}</td>
                    {coverageQuery.data!.languages.map((lang) => {
                      const cell = row.coverage[lang.code];
                      if (!cell?.supported) {
                        return (
                          <td key={lang.code} className="coverage-cell coverage-cell--none">
                            —
                          </td>
                        );
                      }
                      return (
                        <td
                          key={lang.code}
                          className={`coverage-cell coverage-cell--${cell.quality}`}
                          title={
                            cell.bleu != null
                              ? `BLEU ${cell.bleu.toFixed(1)}`
                              : undefined
                          }
                        >
                          <span className={`dot dot--${cell.quality}`} />
                          {qualityLabel(cell.quality)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
