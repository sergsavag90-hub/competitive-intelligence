import React, { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { Competitor } from "@types/api";

type Props = {
  rows: Competitor[];
  onSelect?: (competitor: Competitor) => void;
};

export const CompetitorTable: React.FC<Props> = ({ rows, onSelect }) => {
  const columnDefs = useMemo<ColDef[]>(() => [
    { field: "name", headerName: "Name", flex: 1 },
    { field: "url", headerName: "URL", flex: 1 },
    { field: "priority", headerName: "Priority", width: 120 },
    { field: "enabled", headerName: "Enabled", width: 120 }
  ], []);

  return (
    <div className="ag-theme-alpine" style={{ height: 400, width: "100%" }}>
      <AgGridReact
        rowData={rows}
        columnDefs={columnDefs}
        rowSelection="single"
        onRowClicked={(e) => onSelect?.(e.data)}
        animateRows
        suppressCellFocus
      />
    </div>
  );
};
