import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { User } from "@/types";

export function useMe() {
  return useQuery<User>({
    queryKey: ["me"],
    queryFn: async () => {
      const { data } = await authApi.me();
      return data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = localStorage.getItem("va_refresh_token") || "";
      await authApi.logout({ refresh_token: token });
    },
    onSuccess: () => {
      localStorage.clear();
      queryClient.clear();
      toast.success("Successfully logged out");
      router.push("/auth/login");
    },
    onError: () => {
      localStorage.clear();
      queryClient.clear();
      router.push("/auth/login");
    }
  });
}