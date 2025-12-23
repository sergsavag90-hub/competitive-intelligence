import { useQuery } from "@tanstack/react-query";
import client from "@api/client";
import { Competitor } from "../types/api";

export const useCompetitorData = () => {
  return useQuery<Competitor[]>({
    queryKey: ["competitors"],
    queryFn: async () => {
      const { data } = await client.get<Competitor[]>("/api/v1/competitors");
      return data;
    },
  });
};
