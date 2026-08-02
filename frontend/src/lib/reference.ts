"use client";

/** TanStack Query hooks for the public reference-data lists. */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface LabelOption {
  id: string;
  label: string;
}

export interface LanguageOption {
  code: string;
  name: string;
}

export interface CountryOption {
  code: string;
  name: string;
}

function useReferenceList<T>(path: string) {
  return useQuery({
    queryKey: ["reference", path],
    queryFn: () => api.get<T[]>(`/v1/reference/${path}`),
    staleTime: Infinity, // static seed lists
  });
}

export const useCommunities = () => useReferenceList<LabelOption>("communities");
export const useReligiousPractices = () => useReferenceList<LabelOption>("religious-practices");
export const useLanguages = () => useReferenceList<LanguageOption>("languages");
export const useInterests = () => useReferenceList<LabelOption>("interests");
export const useEducationLevels = () => useReferenceList<LabelOption>("education-levels");
export const useOccupationCategories = () => useReferenceList<LabelOption>("occupation-categories");
export const useCountries = () => useReferenceList<CountryOption>("countries");
