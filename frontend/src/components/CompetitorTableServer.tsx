import React, { useMemo, useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, IGetRowsParams, GridReadyEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { useCompetitorPaged } from "@hooks/useCompetitorPaged";
import { Competitor } from "@types/api";

type Props = {
  pageSize?: number;
  onSelect?: (competitor: Competitor) => void;
};

export const CompetitorTableServer: React.FC<Props> = ({ pageSize = 200, onSelect }) => {
  const gridRef = useRef<AgGridReact<Competitor>>(null);
  const { data, isLoading, refetch } = useCompetitorPaged(0, pageSize);

  const columnDefs = useMemo<ColDef[]>(() => [
    { field: "name", headerName: "Name", flex: 1 },
    { field: "url", headerName: "URL", flex: 1 },
    { field: "priority", headerName: "Priority", width: 120 },
    { field: "enabled", headerName: "Enabled", width: 120 }
  ], []);

  const onGridReady = (params: GridReadyEvent) => {
    const dataSource = {
      rowCount: data?.total ?? undefined,
      getRows: async (gridParams: IGetRowsParams) => {
        const offset = gridParams.startRow;
        const limit = gridParams.endRow - gridParams.startRow;
        const res = await refetch({ queryKey: ["competitors-paged", offset, limit] as any, meta: { offset, limit } });
        const items = res.data?.items ?? [];
        gridParams.successCallback(items, res.data?.total);
      },
    };
    params.api.setDatasource(dataSource);
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
