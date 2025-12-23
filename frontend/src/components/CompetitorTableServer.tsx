import React, { useMemo, useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, IGetRowsParams, GridReadyEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { useCompetitorPaged } from "@hooks/useCompetitorPaged";
import client from "@api/client";
import { Competitor } from "../types/api";

type Props = {
  pageSize?: number;
  onSelect?: (competitor: Competitor) => void;
};

export const CompetitorTableServer: React.FC<Props> = ({ pageSize = 200, onSelect }) => {
  const gridRef = useRef<AgGridReact<Competitor>>(null);
  const { isLoading } = useCompetitorPaged(0, pageSize);

  const columnDefs = useMemo<ColDef[]>(() => [
    { field: "name", headerName: "Name", flex: 1 },
    { field: "url", headerName: "URL", flex: 1 },
    { field: "priority", headerName: "Priority", width: 120 },
    { field: "enabled", headerName: "Enabled", width: 120 }
  ], []);

  const onGridReady = (params: GridReadyEvent) => {
    const dataSource = {
      rowCount: undefined,
      getRows: async (gridParams: IGetRowsParams) => {
        const offset = gridParams.startRow;
        const limit = gridParams.endRow - gridParams.startRow;
        const res = await client.get<{ items?: Competitor[]; total?: number }>("/api/v1/competitors/paged", {
          params: { offset, limit },
        });
        const payload = res.data;
        const items = payload?.items ?? [];
        gridParams.successCallback(items, payload?.total ?? items.length);
      },
    };
    (params.api as any).setDatasource(dataSource);
  };

  return (
    <div className="ag-theme-alpine" style={{ height: 500, width: "100%" }}>
      <AgGridReact
        ref={gridRef as any}
        columnDefs={columnDefs}
        rowSelection="single"
        animateRows
        rowModelType="infinite"
        cacheBlockSize={pageSize}
        maxBlocksInCache={5}
        suppressCellFocus
        onRowClicked={(e) => onSelect?.(e.data)}
        onGridReady={onGridReady}
        overlayLoadingTemplate="<span class='ag-overlay-loading-center'>Loading...</span>"
        overlayNoRowsTemplate={isLoading ? "Loading..." : "No rows"}
      />
    </div>
  );
};
