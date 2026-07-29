import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { eventsApi } from "@/lib/api";
import { SecurityEvent, PaginatedResponse } from "@/types";
import { toast } from "sonner";
import { useEffect } from "react";
import { useOrgSocket } from "./useSocket";

export function useEvents(filters?: { page?: number; size?: number; severity?: string; resolved?: boolean }) {
  const queryClient = useQueryClient();

  const query = useQuery<PaginatedResponse<SecurityEvent>>({
    queryKey: ["events", filters],
    queryFn: async () => {
      const response = await eventsApi.listAll(filters);
      return response.data;
    },
  });

  return query;
}

export function useResolveEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ eventId, note }: { eventId: string; note?: string }) => {
      const { data } = await eventsApi.resolve(eventId, { resolution_note: note });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      toast.success("Incident marked as resolved");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to resolve incident");
    },
  });
}
