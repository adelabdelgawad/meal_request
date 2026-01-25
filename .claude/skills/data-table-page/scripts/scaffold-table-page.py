#!/usr/bin/env python3
"""
Scaffold a new data table page following the established patterns.

Usage:
    python scaffold-table-page.py <feature-name>
    python scaffold-table-page.py products
    python scaffold-table-page.py products --output src/my-app/app/(pages)
    python scaffold-table-page.py products --dry-run
"""

import argparse
import os
import sys
from pathlib import Path


def to_pascal_case(name: str) -> str:
    """Convert to PascalCase."""
    return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))


def to_camel_case(name: str) -> str:
    """Convert to camelCase."""
    pascal = to_pascal_case(name)
    return pascal[0].lower() + pascal[1:] if pascal else ""


def get_templates(feature: str) -> dict[str, str]:
    """Get file templates for the feature."""
    pascal = to_pascal_case(feature)
    camel = to_camel_case(feature)
    singular = feature.rstrip("s")
    singular_pascal = to_pascal_case(singular)

    templates = {}

    # page.tsx
    templates["page.tsx"] = f'''// app/(pages)/{feature}/page.tsx
import {{ get{pascal} }} from "@/lib/actions/{feature}.actions";
import {pascal}Table from "./_components/table/{feature}-table";

export default async function {pascal}Page({{
  searchParams,
}}: {{
  searchParams: Promise<{{
    page?: string;
    limit?: string;
    search?: string;
    is_active?: string;
  }}>;
}}) {{
  const params = await searchParams;
  const {{ page, limit, search, is_active }} = params;

  const pageNumber = Number(page) || 1;
  const limitNumber = Number(limit) || 10;
  const skip = (pageNumber - 1) * limitNumber;

  const filters = {{
    is_active,
    search,
  }};

  const data = await get{pascal}(limitNumber, skip, filters);

  return <{pascal}Table initialData={{data}} />;
}}
'''

    # {feature}-table.tsx
    templates[f"_components/table/{feature}-table.tsx"] = f'''"use client";

import {{ useSearchParams }} from "next/navigation";
import useSWR from "swr";
import {{ useState }} from "react";
import type {{ {pascal}Response, {singular_pascal}Response }} from "@/types/{feature}";
import {{ clientApi }} from "@/lib/http/axios-client";
import {{ {pascal}Provider }} from "../../context/{feature}-actions-context";
import {pascal}TableBody from "./{feature}-table-body";
import {{ Pagination }} from "@/components/data-table/table/pagination";
import LoadingSkeleton from "@/components/loading-skeleton";

interface {pascal}TableProps {{
  initialData: {pascal}Response | null;
}}

const fetcher = async (url: string): Promise<{pascal}Response> => {{
  const response = await clientApi.get<{pascal}Response>(url);
  if (!response.ok) throw new Error(response.error || "Failed to fetch");
  return response.data;
}};

export default function {pascal}Table({{ initialData }}: {pascal}TableProps) {{
  const searchParams = useSearchParams();

  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const filter = searchParams?.get("filter") || "";
  const isActive = searchParams?.get("is_active") || "";

  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());
  if (filter) params.append("search", filter);
  if (isActive) params.append("is_active", isActive);

  const apiUrl = `/{feature}?${{params.toString()}}`;

  const {{ data, mutate, isLoading, error }} = useSWR<{pascal}Response>(
    apiUrl,
    fetcher,
    {{
      fallbackData: initialData ?? undefined,
      keepPreviousData: true,
      revalidateOnMount: false,
      revalidateIfStale: true,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }}
  );

  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());

  const markUpdating = (ids: string[]) => {{
    setUpdatingIds((prev) => {{
      const next = new Set(prev);
      ids.forEach((id) => next.add(id));
      return next;
    }});
  }};

  const clearUpdating = (ids?: string[]) => {{
    setUpdatingIds((prev) => {{
      if (!ids) return new Set();
      const next = new Set(prev);
      ids.forEach((id) => next.delete(id));
      return next;
    }});
  }};

  const update{pascal} = async (updated{pascal}: {singular_pascal}Response[]) => {{
    await mutate(
      (currentData) => {{
        if (!currentData) return currentData;
        const updatedMap = new Map(updated{pascal}.map((item) => [item.id, item]));
        const updatedList = currentData.{camel}.map((item) =>
          updatedMap.has(item.id) ? updatedMap.get(item.id)! : item
        );
        const newActiveCount = updatedList.filter((i) => i.isActive).length;
        const newInactiveCount = updatedList.filter((i) => !i.isActive).length;
        return {{
          ...currentData,
          {camel}: updatedList,
          activeCount: newActiveCount,
          inactiveCount: newInactiveCount,
        }};
      }},
      {{ revalidate: false }}
    );
  }};

  if (error) {{
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-red-500 mb-2">Failed to load data</div>
          <button onClick={{() => mutate()}} className="px-4 py-2 bg-blue-500 text-white">
            Retry
          </button>
        </div>
      </div>
    );
  }}

  const {camel} = data?.{camel} ?? [];
  const totalItems = data?.total ?? 0;
  const totalPages = Math.ceil(totalItems / limit);

  const actions = {{
    update{pascal},
    onRefresh: async () => {{
      await mutate();
      return {{ success: true }};
    }},
  }};

  return (
    <{pascal}Provider actions={{actions}}>
      <div className="relative h-full flex flex-col gap-3 bg-muted/30 min-h-0 pt-1.5">
        {{isLoading && <LoadingSkeleton />}}
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <{pascal}TableBody
            {camel}={{{camel}}}
            page={{page}}
            mutate={{mutate}}
            update{pascal}={{update{pascal}}}
            updatingIds={{updatingIds}}
            markUpdating={{markUpdating}}
            clearUpdating={{clearUpdating}}
          />
        </div>
        <div className="shrink-0 bg-card">
          <Pagination
            currentPage={{page}}
            totalPages={{totalPages}}
            pageSize={{limit}}
            totalItems={{totalItems}}
          />
        </div>
      </div>
    </{pascal}Provider>
  );
}}
'''

    # {feature}-table-columns.tsx
    templates[f"_components/table/{feature}-table-columns.tsx"] = f'''"use client";

import {{ ColumnDef }} from "@tanstack/react-table";
import {{ Loader2 }} from "lucide-react";
import type {{ {singular_pascal}Response }} from "@/types/{feature}";

interface ColumnsProps {{
  updatingIds: Set<string>;
  update{pascal}: (items: {singular_pascal}Response[]) => Promise<void>;
  markUpdating: (ids: string[]) => void;
  clearUpdating: (ids?: string[]) => void;
}}

export function create{pascal}Columns({{
  updatingIds,
  update{pascal},
  markUpdating,
  clearUpdating,
}}: ColumnsProps): ColumnDef<{singular_pascal}Response>[] {{
  return [
    {{
      id: "select",
      header: ({{ table }}) => (
        <div className="flex justify-center">
          <input
            type="checkbox"
            checked={{table.getIsAllPageRowsSelected()}}
            onChange={{(e) => table.toggleAllPageRowsSelected(e.target.checked)}}
            disabled={{updatingIds.size > 0}}
          />
        </div>
      ),
      cell: ({{ row }}) => {{
        const isUpdating = Boolean(row.original.id && updatingIds.has(row.original.id));
        return (
          <div className={{`flex justify-center ${{isUpdating ? "opacity-60" : ""}}`}}>
            {{isUpdating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <input
                type="checkbox"
                checked={{row.getIsSelected()}}
                onChange={{(e) => row.toggleSelected(e.target.checked)}}
              />
            )}}
          </div>
        );
      }},
      enableSorting: false,
      enableHiding: false,
      size: 50,
    }},
    {{
      accessorKey: "name",
      header: () => <div className="text-center">Name</div>,
      cell: (info) => <div className="text-center">{{info.getValue() as string}}</div>,
      size: 200,
    }},
    // TODO: Add more columns
    {{
      id: "actions",
      header: () => <div className="text-center">Actions</div>,
      cell: () => <div />,
      enableSorting: false,
      enableHiding: false,
      size: 150,
    }},
  ];
}}
'''

    # context/{feature}-actions-context.tsx
    templates[f"context/{feature}-actions-context.tsx"] = f'''"use client";

import {{ createContext, useContext, ReactNode }} from "react";
import type {{ {singular_pascal}Response }} from "@/types/{feature}";

interface ActionsContextType {{
  update{pascal}: (items: {singular_pascal}Response[]) => Promise<void>;
  onRefresh: () => Promise<{{ success: boolean }}>;
}}

const {pascal}Context = createContext<ActionsContextType | null>(null);

interface ProviderProps {{
  children: ReactNode;
  actions: ActionsContextType;
}}

export function {pascal}Provider({{ children, actions }}: ProviderProps) {{
  return (
    <{pascal}Context.Provider value={{actions}}>
      {{children}}
    </{pascal}Context.Provider>
  );
}}

export function use{pascal}Context() {{
  const context = useContext({pascal}Context);
  if (!context) {{
    throw new Error("use{pascal}Context must be used within {pascal}Provider");
  }}
  return context;
}}

export function use{pascal}Actions() {{
  const {{ update{pascal}, onRefresh }} = use{pascal}Context();
  return {{ update{pascal}, onRefresh }};
}}
'''

    return templates


def create_files(feature: str, output_dir: str, dry_run: bool = False) -> list[str]:
    """Create all files for the feature."""
    templates = get_templates(feature)
    created = []
    base_path = Path(output_dir) / feature

    for rel_path, content in templates.items():
        file_path = base_path / rel_path
        dir_path = file_path.parent

        if dry_run:
            print(f"Would create: {file_path}")
            created.append(str(file_path))
            continue

        dir_path.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        print(f"Created: {file_path}")
        created.append(str(file_path))

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new data table page"
    )
    parser.add_argument(
        "feature",
        help="Feature name (e.g., 'products', 'orders')"
    )
    parser.add_argument(
        "--output", "-o",
        default="src/my-app/app/(pages)",
        help="Output directory (default: src/my-app/app/(pages))"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview without creating files"
    )

    args = parser.parse_args()

    # Validate feature name
    feature = args.feature.lower().replace("-", "_").replace(" ", "_")

    print(f"Scaffolding data table page for: {feature}")
    print(f"Output directory: {args.output}")
    if args.dry_run:
        print("DRY RUN - No files will be created\n")

    created = create_files(feature, args.output, args.dry_run)

    print(f"\n{'Would create' if args.dry_run else 'Created'} {len(created)} files")

    print("\nNext steps:")
    print(f"  1. Create types in types/{feature}.ts")
    print(f"  2. Create server actions in lib/actions/{feature}.actions.ts")
    print(f"  3. Create client API in lib/api/{feature}.ts")
    print(f"  4. Add translations in locales/{{lang}}/{feature}.json")
    print(f"  5. Customize columns in {feature}-table-columns.tsx")


if __name__ == "__main__":
    main()
