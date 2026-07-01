import { tickerText } from '../data/pipelineData';

export default function Ticker() {
  const doubled = `${tickerText}   ${tickerText}`;
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 overflow-hidden border-t border-surface-700/50 bg-surface-950/90 backdrop-blur-xl">
      <div className="ticker-animate flex whitespace-nowrap py-2">
        <span className="inline-block px-4 text-xs font-medium text-surface-400">
          {doubled}
        </span>
      </div>
    </div>
  );
}
