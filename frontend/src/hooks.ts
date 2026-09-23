import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api/client";
import type { NoticeQuery } from "./api/types";

export function useNotices(params: NoticeQuery) {
  return useQuery({
    queryKey: ["notices", params],
    queryFn: () => api.notices(params),
  });
}

export function useNotice(id: number | null) {
  return useQuery({
    queryKey: ["notice", id],
    queryFn: () => api.notice(id!),
    enabled: id !== null,
  });
}

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: api.stats });
}

export function useDigest(date: string) {
  return useQuery({
    queryKey: ["digest", date],
    queryFn: () => api.digest(date),
    // 요약이 아직 없으면 404 다. 재시도할 이유가 없다.
    retry: false,
  });
}

/** 읽음, 별표는 즉시 반영하고 실패하면 되돌린다. 목록 클릭이 굼뜨면 안 된다. */
function useToggle(fn: (id: number, value: boolean) => Promise<void>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, value }: { id: number; value: boolean }) => fn(id, value),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["notices"] });
      qc.invalidateQueries({ queryKey: ["notice"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}

export const useSetRead = () => useToggle(api.setRead);
export const useSetStar = () => useToggle(api.setStar);
