import React from "react";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../ErrorBoundary";

const Boom: React.FC = () => {
  throw new Error("boom");
};

describe("ErrorBoundary", () => {
  it("renders fallback on error", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    expect(screen.getByText(/boom/i)).toBeInTheDocument();
  });
});
