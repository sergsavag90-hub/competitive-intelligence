import { useQuery } from "react-query";
import client from "@api/client";
import { Competitor } from "@types/api";

type PagedResult = { items: Competitor[]; total: number };

export const useCompetitorPaged = (offset: number, limit: number) => {
  return useQuery<PagedResult>(
    ["competitors-paged", offset, limit],
    async () => {
      const { data } = await client.get<PagedResult>("/competitors/paged", {
        params: { offset, limit },
      });
      return data;
    },
    { keepPreviousData: true }
  );
};
