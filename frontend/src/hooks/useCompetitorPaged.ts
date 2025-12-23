import { useQuery } from "@tanstack/react-query";
import client from "@api/client";
import { Competitor } from "../types/api";

type PagedResult = { items: Competitor[]; total: number };

export const useCompetitorPaged = (offset: number, limit: number) =>
  useQuery<PagedResult>({
    queryKey: ["competitors-paged", offset, limit],
    queryFn: async () => {
      const { data } = await client.get<PagedResult>("/api/v1/competitors/paged", {
        params: { offset, limit },
      });
      return data;
    },
  });
