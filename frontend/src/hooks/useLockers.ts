import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { lockerApi } from "@/lib/api";
import { Locker } from "@/types";
import { toast } from "sonner";

export function useLockers() {
  return useQuery<Locker[]>({
    queryKey: ["lockers"],
    queryFn: async () => {
      const { data } = await lockerApi.list();
      return data;
    },
  });
}

export function useCreateLocker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: object) => {
      const { data } = await lockerApi.create(payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lockers"] });
      toast.success("Locker created successfully");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to create locker");
    }
  });
}

export function useDeleteLocker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await lockerApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lockers"] });
      toast.success("Locker deleted successfully");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to delete locker");
    }
  });
}

export function useLockerControl() {
  return useMutation({
    mutationFn: async ({ id, action }: { id: string; action: 'unlock' | 'lock' | 'lockdown' }) => {
      if (action === 'unlock') await lockerApi.unlock(id);
      if (action === 'lock') await lockerApi.lock(id);
      if (action === 'lockdown') await lockerApi.lockdown(id);
    },
    onSuccess: (_, variables) => {
      toast.success(`Command '${variables.action}' sent successfully`);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to send command");
    }
  });
}