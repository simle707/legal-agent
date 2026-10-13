import { FormEvent, KeyboardEvent } from "react";

type ComposerProps = {
  value: string;
  loading: boolean;
  canSend: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
};

export function Composer({
  value,
  loading,
  canSend,
  onChange,
  onSubmit,
  onKeyDown,
}: ComposerProps) {
  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-3xl">
      <label className="block">
        <span className="sr-only">咨询内容</span>
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          rows={3}
          placeholder="描述你的情况，例如：公司单方面解除劳动合同，没有支付补偿……"
          className="w-full resize-none rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm leading-6 outline-none ring-[var(--gold)] placeholder:text-[var(--muted)] focus:ring-2"
        />
      </label>
      <div className="mt-3 flex items-center justify-between gap-4">
        <p className="text-xs text-[var(--muted)]">Enter 发送，Shift + Enter 换行</p>
        <button
          type="submit"
          disabled={!canSend}
          className="rounded-full bg-[var(--ink)] px-5 py-2 text-sm text-[var(--paper)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "发送中" : "发送咨询"}
        </button>
      </div>
    </form>
  );
}
