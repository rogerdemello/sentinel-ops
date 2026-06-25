import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

/** Catches render-time errors (e.g. a malformed API payload) so a single bad
 *  component degrades to a recoverable message instead of white-screening the app. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    // eslint-disable-next-line no-console
    console.error("Render error caught by ErrorBoundary:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-ink-900 p-6">
          <div className="max-w-md rounded-xl border border-red-500/40 bg-ink-800 p-6 text-center">
            <div className="text-lg font-semibold text-red-300">Something went wrong</div>
            <p className="mt-2 text-sm text-slate-400">
              The dashboard hit an unexpected error while rendering. The backend may have
              returned data in an unexpected shape.
            </p>
            <pre className="mt-3 max-h-32 overflow-auto rounded-lg bg-ink-900 p-2 text-left font-mono text-[11px] text-slate-500">
              {this.state.error.message}
            </pre>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-4 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink-900 hover:bg-accent/90"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
