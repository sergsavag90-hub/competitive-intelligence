import { useQuery } from "react-query";
import client from "@api/client";
import { Competitor } from "@types/api";

export const useCompetitorData = () => {
  return useQuery<Competitor[]>(["competitors"], async () => {
    const { data } = await client.get<Competitor[]>("/competitors");
    return data;
  });
};
