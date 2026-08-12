import { AgentAvatar } from "./icons";

export default function MobileHeader() {
  return (
    <div className="flex items-center gap-3 border-b border-black/5 px-5 py-4 md:hidden">
      <AgentAvatar />
      <div>
        <p className="text-sm font-semibold text-gray-900">리뷰 분석 에이전트</p>
        <p className="flex items-center gap-1 text-xs text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          실시간 데이터 연결됨
        </p>
      </div>
    </div>
  );
}
