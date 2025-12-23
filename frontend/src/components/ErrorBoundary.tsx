import React from "react";

type ErrorBoundaryState = { hasError: boolean; error: Error | null };

export class ErrorBoundary extends React.Component<React.PropsWithChildren<unknown>, ErrorBoundaryState> {
  constructor(props: React.PropsWithChildren<unknown>) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error("UI error boundary caught", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "1rem", border: "1px solid #f44336", borderRadius: 8, color: "#f44336" }}>
          <p>Something went wrong while rendering this view.</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>{this.state.error?.message}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
