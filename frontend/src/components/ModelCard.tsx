import type { ModelItem } from "../api";

type Props = {
  model: ModelItem;
  selected: boolean;
  onSelect: () => void;
  selectable?: boolean;
};

export function ModelCard({ model, selected, onSelect, selectable = true }: Props) {
  return (
    <article
      className={`model-card${selected ? " model-card--selected" : ""}${
        !selectable ? " model-card--static" : ""
      }`}
      onClick={selectable ? onSelect : undefined}
      onKeyDown={
        selectable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect();
              }
            }
          : undefined
      }
      role={selectable ? "button" : undefined}
      tabIndex={selectable ? 0 : undefined}
    >
      <header className="model-card__head">
        {selectable && (
          <input
            type="radio"
            name="model"
            checked={selected}
            onChange={onSelect}
            onClick={(e) => e.stopPropagation()}
            aria-label={model.display_name}
          />
        )}
        <div>
          <h3>{model.display_name}</h3>
          {model.provider && <p className="model-card__provider">{model.provider}</p>}
        </div>
        <div className="model-card__tags">
          {model.is_recommended && <span className="tag tag--recommended">Recommended</span>}
          {model.tags.map((tag) => (
            <span key={tag} className="tag">
              {tag}
            </span>
          ))}
        </div>
      </header>
      <p className="model-card__summary">{model.pipeline_summary || model.description}</p>
      {model.description && model.pipeline_summary !== model.description && (
        <p className="model-card__description">{model.description}</p>
      )}
      {model.metrics && (
        <dl className="model-card__metrics">
          <div>
            <dt>BLEU</dt>
            <dd>{model.metrics.bleu != null ? model.metrics.bleu.toFixed(1) : "—"}</dd>
          </div>
          {model.metrics.dataset_name && (
            <div className="model-card__dataset">
              <dt>Dataset</dt>
              <dd>{model.metrics.dataset_name}</dd>
            </div>
          )}
        </dl>
      )}
    </article>
  );
}
