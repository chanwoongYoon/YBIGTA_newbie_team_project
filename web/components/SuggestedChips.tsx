export default function SuggestedChips({
  suggestions,
  onSelect,
  disabled,
}: {
  suggestions: string[];
  onSelect: (text: string) => void;
  disabled?: boolean;
}) {
  if (!suggestions.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((s) => (
        <button
          key={s}
          disabled={disabled}
          onClick={() => onSelect(s)}
          className="rounded-full border border-brand/25 bg-white px-3 py-1.5 text-xs font-medium text-brand transition hover:bg-brand-light disabled:cursor-not-allowed disabled:opacity-50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
