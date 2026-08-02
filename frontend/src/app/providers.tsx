"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { ThemeController } from "@/components/theme-controller";
import { ActingProfileProvider } from "@/lib/profiles";
import { AuthProvider } from "@/lib/auth";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            retry: (failureCount, error) => {
              // Never retry 4xx (auth/validation) — only transient failures.
              const status = (error as { status?: number }).status;
              if (status && status >= 400 && status < 500) return false;
              return failureCount < 2;
            },
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ActingProfileProvider>
          <ThemeController />
          {children}
        </ActingProfileProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
