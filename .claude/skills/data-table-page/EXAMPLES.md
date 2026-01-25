# Data Table Page Examples

Complete, working code examples for building data table pages.

## Example 1: Complete Page Setup

### page.tsx (Server Component)

```typescript
// app/(pages)/products/page.tsx
import { getProducts } from "@/lib/actions/products.actions";
import { getCategories } from "@/lib/actions/categories.actions";
import ProductsTable from "./_components/table/products-table";

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string;
    limit?: string;
    search?: string;
    is_active?: string;
    category?: string;
  }>;
}) {
  const params = await searchParams;
  const { page, limit, search, is_active, category } = params;

  const pageNumber = Number(page) || 1;
  const limitNumber = Number(limit) || 10;
  const skip = (pageNumber - 1) * limitNumber;

  const filters = {
    is_active,
    search,
    category,
  };

  // Parallel fetching for performance
  const [products, categories] = await Promise.all([
    getProducts(limitNumber, skip, filters),
    getCategories({ limit: 1000, skip: 0 }),
  ]);

  return (
    <ProductsTable
      initialData={products}
      categories={categories}
    />
  );
}
```

### products-table.tsx (Client Component with SWR)

```typescript
// app/(pages)/products/_components/table/products-table.tsx
"use client";

import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { useState, useMemo } from "react";
import type { ProductsResponse, ProductResponse, CategoryResponse } from "@/types/products";
import { clientApi } from "@/lib/http/axios-client";
import { ProductsProvider } from "../../context/products-actions-context";
import ProductsTableBody from "./products-table-body";
import { StatusPanel } from "../sidebar/status-panel";
import { Pagination } from "@/components/data-table/table/pagination";
import LoadingSkeleton from "@/components/loading-skeleton";
import { useLanguage } from "@/hooks/use-language";

interface ProductsTableProps {
  initialData: ProductsResponse | null;
  categories: CategoryResponse[];
}

const fetcher = async (url: string): Promise<ProductsResponse> => {
  const response = await clientApi.get<ProductsResponse>(url);
  if (!response.ok) throw new Error(response.error || "Failed to fetch");
  return response.data;
};

export default function ProductsTable({
  initialData,
  categories,
}: ProductsTableProps) {
  const { t, language } = useLanguage();
  const searchParams = useSearchParams();

  // URL state
  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const filter = searchParams?.get("filter") || "";
  const isActive = searchParams?.get("is_active") || "";
  const category = searchParams?.get("category") || "";

  // Build API URL
  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());
  if (filter) params.append("search", filter);
  if (isActive) params.append("is_active", isActive);
  if (category) params.append("category", category);

  const apiUrl = `/products?${params.toString()}`;

  // SWR hook
  const { data, mutate, isLoading, error } = useSWR<ProductsResponse>(
    apiUrl,
    fetcher,
    {
      fallbackData: initialData ?? undefined,
      keepPreviousData: true,
      revalidateOnMount: false,
      revalidateIfStale: true,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  // Loading state tracking
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());

  const markUpdating = (ids: string[]) => {
    setUpdatingIds((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => next.add(id));
      return next;
    });
  };

  const clearUpdating = (ids?: string[]) => {
    setUpdatingIds((prev) => {
      if (!ids) return new Set();
      const next = new Set(prev);
      ids.forEach((id) => next.delete(id));
      return next;
    });
  };

  // Cache update function
  const updateProducts = async (updatedProducts: ProductResponse[]) => {
    await mutate(
      (currentData) => {
        if (!currentData) return currentData;

        const updatedMap = new Map(updatedProducts.map((p) => [p.id, p]));

        const updatedList = currentData.products.map((product) =>
          updatedMap.has(product.id) ? updatedMap.get(product.id)! : product
        );

        const newActiveCount = updatedList.filter((p) => p.isActive).length;
        const newInactiveCount = updatedList.filter((p) => !p.isActive).length;

        return {
          ...currentData,
          products: updatedList,
          activeCount: newActiveCount,
          inactiveCount: newInactiveCount,
        };
      },
      { revalidate: false }
    );
  };

  // Derived values
  const products = data?.products ?? [];
  const activeCount = data?.activeCount ?? 0;
  const inactiveCount = data?.inactiveCount ?? 0;
  const totalItems = data?.total ?? 0;
  const totalPages = Math.ceil(totalItems / limit);

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-red-500 mb-2">Failed to load products</div>
          <button
            onClick={() => mutate()}
            className="px-4 py-2 bg-blue-500 text-white hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Context actions
  const actions = {
    onToggleStatus: async (productId: string, isActive: boolean) => {
      try {
        const response = await clientApi.put<ProductResponse>(
          `/products/${productId}/status`,
          { isActive }
        );
        if (!response.ok) {
          return { success: false, error: response.error || "Failed" };
        }
        await updateProducts([response.data]);
        return { success: true, message: "Status updated" };
      } catch (error) {
        return { success: false, error: "Failed to update" };
      }
    },
    updateProducts,
    onRefresh: async () => {
      await mutate();
      return { success: true, message: "Refreshed" };
    },
  };

  return (
    <ProductsProvider actions={actions} categories={categories}>
      <div className="relative h-full flex gap-3 bg-muted/30 min-h-0 pt-1.5">
        {isLoading && <LoadingSkeleton />}

        <StatusPanel
          totalCount={activeCount + inactiveCount}
          activeCount={activeCount}
          inactiveCount={inactiveCount}
        />

        <div className="flex-1 flex flex-col min-h-0 space-y-2">
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            <ProductsTableBody
              products={products}
              page={page}
              mutate={mutate}
              updateProducts={updateProducts}
              updatingIds={updatingIds}
              markUpdating={markUpdating}
              clearUpdating={clearUpdating}
            />
          </div>

          <div className="shrink-0 bg-card">
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              pageSize={limit}
              totalItems={totalItems}
            />
          </div>
        </div>
      </div>
    </ProductsProvider>
  );
}
```

---

## Example 2: Column Definitions with Mutations

```typescript
// app/(pages)/products/_components/table/products-table-columns.tsx
"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { StatusSwitch } from "@/components/ui/status-switch";
import { Loader2, Package } from "lucide-react";
import { toast } from "@/components/ui/custom-toast";
import { toggleProductStatus } from "@/lib/api/products";
import type { ProductResponse } from "@/types/products";

interface ColumnTranslations {
  name: string;
  category: string;
  price: string;
  active: string;
  actions: string;
  activateSuccess: string;
  deactivateSuccess: string;
}

interface ProductsColumnsProps {
  updatingIds: Set<string>;
  updateProducts: (products: ProductResponse[]) => Promise<void>;
  markUpdating: (ids: string[]) => void;
  clearUpdating: (ids?: string[]) => void;
  translations: ColumnTranslations;
  language: string;
}

export function createProductsColumns({
  updatingIds,
  updateProducts,
  markUpdating,
  clearUpdating,
  translations: t,
  language,
}: ProductsColumnsProps): ColumnDef<ProductResponse>[] {
  return [
    // Selection column
    {
      id: "select",
      header: ({ table }) => (
        <div className="flex justify-center">
          <input
            type="checkbox"
            checked={table.getIsAllPageRowsSelected()}
            onChange={(e) => table.toggleAllPageRowsSelected(e.target.checked)}
            disabled={updatingIds.size > 0}
          />
        </div>
      ),
      cell: ({ row }) => {
        const isUpdating = Boolean(
          row.original.id && updatingIds.has(row.original.id)
        );
        return (
          <div className={`flex justify-center ${isUpdating ? "opacity-60" : ""}`}>
            {isUpdating ? (
              <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            ) : (
              <input
                type="checkbox"
                checked={row.getIsSelected()}
                onChange={(e) => row.toggleSelected(e.target.checked)}
                disabled={updatingIds.size > 0}
              />
            )}
          </div>
        );
      },
      enableSorting: false,
      enableHiding: false,
      size: 50,
    },

    // Name column
    {
      accessorKey: "name",
      header: () => <div className="text-center">{t.name}</div>,
      cell: ({ row }) => {
        const product = row.original;
        const isUpdating = updatingIds.has(product.id);
        const displayName = language === "ar" && product.nameAr
          ? product.nameAr
          : product.nameEn;

        return (
          <div className={`flex items-center gap-2 ${isUpdating ? "opacity-60" : ""}`}>
            <Package className="w-4 h-4 text-gray-500" />
            <span className="font-medium">{displayName}</span>
          </div>
        );
      },
      size: 200,
    },

    // Category column
    {
      accessorKey: "category",
      header: () => <div className="text-center">{t.category}</div>,
      cell: ({ row }) => (
        <div className="flex justify-center">
          <Badge variant="outline">{row.original.categoryName}</Badge>
        </div>
      ),
      size: 120,
    },

    // Price column
    {
      accessorKey: "price",
      header: () => <div className="text-center">{t.price}</div>,
      cell: ({ row }) => (
        <div className="text-center font-mono">
          ${row.original.price.toFixed(2)}
        </div>
      ),
      size: 100,
    },

    // Status column with inline toggle
    {
      id: "isActive",
      accessorKey: "isActive",
      header: () => <div className="text-center">{t.active}</div>,
      cell: ({ row }) => {
        const product = row.original;
        const isUpdating = Boolean(product.id && updatingIds.has(product.id));

        return (
          <div className={`flex justify-center ${isUpdating ? "opacity-60 pointer-events-none" : ""}`}>
            <StatusSwitch
              checked={product.isActive}
              onToggle={async () => {
                if (!product.id) return;

                const newStatus = !product.isActive;
                markUpdating([product.id]);

                try {
                  // Call API and wait for response
                  const result = await toggleProductStatus(product.id, newStatus);

                  // Update cache with server response
                  await updateProducts([result]);

                  // Show success toast
                  toast.success(newStatus ? t.activateSuccess : t.deactivateSuccess);
                } catch (error) {
                  console.error("Failed to toggle status:", error);
                  toast.error("Failed to update status");
                } finally {
                  clearUpdating([product.id]);
                }
              }}
              size="sm"
            />
          </div>
        );
      },
      size: 80,
    },

    // Actions column
    {
      id: "actions",
      header: () => <div className="text-center">{t.actions}</div>,
      cell: () => <div />, // Populated in table body
      enableSorting: false,
      enableHiding: false,
      size: 150,
    },
  ];
}
```

---

## Example 3: Context Provider

```typescript
// app/(pages)/products/context/products-actions-context.tsx
"use client";

import { createContext, useContext, ReactNode } from "react";
import type { ProductResponse, CategoryResponse } from "@/types/products";

interface ActionResult {
  success: boolean;
  message?: string;
  error?: string;
  data?: ProductResponse | ProductResponse[];
}

interface ActionsContextType {
  onToggleStatus: (id: string, isActive: boolean) => Promise<ActionResult>;
  updateProducts: (products: ProductResponse[]) => Promise<void>;
  onRefresh: () => Promise<ActionResult>;
}

interface DataContextType {
  categories: CategoryResponse[];
}

type ContextType = ActionsContextType & DataContextType;

const ProductsContext = createContext<ContextType | null>(null);

interface ProviderProps {
  children: ReactNode;
  actions: ActionsContextType;
  categories: CategoryResponse[];
}

export function ProductsProvider({
  children,
  actions,
  categories,
}: ProviderProps) {
  const value: ContextType = {
    ...actions,
    categories,
  };

  return (
    <ProductsContext.Provider value={value}>
      {children}
    </ProductsContext.Provider>
  );
}

export function useProductsContext() {
  const context = useContext(ProductsContext);
  if (!context) {
    throw new Error("useProductsContext must be used within ProductsProvider");
  }
  return context;
}

// Convenience hooks
export function useProductsActions() {
  const { onToggleStatus, updateProducts, onRefresh } = useProductsContext();
  return { onToggleStatus, updateProducts, onRefresh };
}

export function useCategories() {
  const { categories } = useProductsContext();
  return categories;
}
```

---

## Example 4: Server Actions

```typescript
// lib/actions/products.actions.ts
"use server";

import { serverApi } from "@/lib/http/axios-server";
import type { ProductsResponse, ProductResponse } from "@/types/products";

export async function getProducts(
  limit: number = 10,
  skip: number = 0,
  filters?: {
    is_active?: string;
    search?: string;
    category?: string;
  }
): Promise<ProductsResponse | null> {
  try {
    const params: Record<string, string | number> = { limit, skip };

    if (filters?.is_active) params.is_active = filters.is_active;
    if (filters?.search) params.search = filters.search;
    if (filters?.category) params.category = filters.category;

    const result = await serverApi.get<ProductsResponse>("/products", {
      params,
      useVersioning: true,
    });

    if (result.ok && result.data) {
      return result.data;
    }

    console.error("Failed to fetch products:", result.error);
    return null;
  } catch (error) {
    console.error("Error in getProducts:", error);
    return null;
  }
}

export async function getProductById(
  productId: string
): Promise<ProductResponse | null> {
  try {
    const result = await serverApi.get<ProductResponse>(
      `/products/${productId}`,
      { useVersioning: true }
    );

    if (result.ok && result.data) {
      return result.data;
    }

    return null;
  } catch (error) {
    console.error("Error in getProductById:", error);
    return null;
  }
}
```

---

## Example 5: Client API Functions

```typescript
// lib/api/products.ts
import { clientApi } from "@/lib/http/axios-client";
import type {
  ProductResponse,
  ProductCreate,
  ProductUpdate,
  BulkStatusResponse,
} from "@/types/products";

export async function toggleProductStatus(
  productId: string,
  isActive: boolean
): Promise<ProductResponse> {
  const result = await clientApi.put<ProductResponse>(
    `/products/${productId}/status`,
    { isActive }
  );

  if (!result.ok) {
    throw new Error(result.error || "Failed to toggle status");
  }

  return result.data;
}

export async function createProduct(
  data: ProductCreate
): Promise<ProductResponse> {
  const result = await clientApi.post<ProductResponse>("/products", data);

  if (!result.ok) {
    throw new Error(result.error || "Failed to create product");
  }

  return result.data;
}

export async function updateProduct(
  productId: string,
  data: ProductUpdate
): Promise<ProductResponse> {
  const result = await clientApi.put<ProductResponse>(
    `/products/${productId}`,
    data
  );

  if (!result.ok) {
    throw new Error(result.error || "Failed to update product");
  }

  return result.data;
}

export async function deleteProduct(productId: string): Promise<void> {
  const result = await clientApi.delete(`/products/${productId}`);

  if (!result.ok) {
    throw new Error(result.error || "Failed to delete product");
  }
}

export async function bulkUpdateProductStatus(
  productIds: string[],
  isActive: boolean
): Promise<BulkStatusResponse> {
  const result = await clientApi.put<BulkStatusResponse>("/products/status", {
    productIds,
    isActive,
  });

  if (!result.ok) {
    throw new Error(result.error || "Failed to bulk update");
  }

  return result.data;
}
```

---

## Example 6: Add/Edit Sheet Modal

```typescript
// app/(pages)/products/_components/modal/add-product-sheet.tsx
"use client";

import { useState, useRef, useMemo } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertDialog } from "@/components/ui/alert-dialog";
import { toast } from "@/components/ui/custom-toast";
import { createProduct } from "@/lib/api/products";
import { useProductsContext } from "../../context/products-actions-context";
import type { ProductCreate } from "@/types/products";

interface AddProductSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

interface FormData {
  nameEn: string;
  nameAr: string;
  price: string;
  categoryId: number | null;
}

const initialFormData: FormData = {
  nameEn: "",
  nameAr: "",
  price: "",
  categoryId: null,
};

export function AddProductSheet({
  open,
  onOpenChange,
  onSuccess,
}: AddProductSheetProps) {
  const { categories, updateProducts } = useProductsContext();

  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const initialValues = useRef<FormData>(initialFormData);

  // Check if form has unsaved changes
  const isDirty = useMemo(() => {
    return (
      formData.nameEn !== initialValues.current.nameEn ||
      formData.nameAr !== initialValues.current.nameAr ||
      formData.price !== initialValues.current.price ||
      formData.categoryId !== initialValues.current.categoryId
    );
  }, [formData]);

  const handleClose = () => {
    if (isDirty) {
      setShowCloseConfirm(true);
    } else {
      resetAndClose();
    }
  };

  const resetAndClose = () => {
    setFormData(initialFormData);
    initialValues.current = initialFormData;
    onOpenChange(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!formData.nameEn.trim()) {
      toast.error("Name is required");
      return;
    }
    if (!formData.categoryId) {
      toast.error("Category is required");
      return;
    }

    setIsSubmitting(true);

    try {
      const createData: ProductCreate = {
        nameEn: formData.nameEn.trim(),
        nameAr: formData.nameAr.trim() || undefined,
        price: parseFloat(formData.price) || 0,
        categoryId: formData.categoryId,
      };

      // Call API
      const newProduct = await createProduct(createData);

      // Update cache with new product
      await updateProducts([newProduct]);

      toast.success("Product created successfully");
      resetAndClose();
      onSuccess();
    } catch (error) {
      console.error("Failed to create product:", error);
      toast.error("Failed to create product");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Sheet open={open} onOpenChange={handleClose}>
        <SheetContent side="right" className="w-[400px]">
          <SheetHeader>
            <SheetTitle>Add New Product</SheetTitle>
          </SheetHeader>

          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            <div>
              <Label htmlFor="nameEn">Name (English) *</Label>
              <Input
                id="nameEn"
                value={formData.nameEn}
                onChange={(e) =>
                  setFormData({ ...formData, nameEn: e.target.value })
                }
                placeholder="Enter product name"
              />
            </div>

            <div>
              <Label htmlFor="nameAr">Name (Arabic)</Label>
              <Input
                id="nameAr"
                value={formData.nameAr}
                onChange={(e) =>
                  setFormData({ ...formData, nameAr: e.target.value })
                }
                placeholder="أدخل اسم المنتج"
                dir="rtl"
              />
            </div>

            <div>
              <Label htmlFor="price">Price</Label>
              <Input
                id="price"
                type="number"
                step="0.01"
                value={formData.price}
                onChange={(e) =>
                  setFormData({ ...formData, price: e.target.value })
                }
                placeholder="0.00"
              />
            </div>

            <div>
              <Label htmlFor="category">Category *</Label>
              <select
                id="category"
                value={formData.categoryId || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    categoryId: e.target.value ? parseInt(e.target.value) : null,
                  })
                }
                className="w-full border rounded-md p-2"
              >
                <option value="">Select category</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.nameEn}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating..." : "Create Product"}
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      {/* Unsaved changes confirmation */}
      <AlertDialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved Changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to close?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continue Editing</AlertDialogCancel>
            <AlertDialogAction onClick={resetAndClose}>
              Discard Changes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
```

---

## Example 7: Bulk Operations Handler

```typescript
// app/(pages)/products/_components/table/products-table-actions.tsx
"use client";

import { toast } from "@/components/ui/custom-toast";
import { bulkUpdateProductStatus } from "@/lib/api/products";
import type { ProductResponse } from "@/types/products";

interface UseProductsTableActionsProps {
  products: ProductResponse[];
  updateProducts: (products: ProductResponse[]) => Promise<void>;
  markUpdating: (ids: string[]) => void;
  clearUpdating: (ids?: string[]) => void;
  resetSelection: () => void;
}

export function useProductsTableActions({
  products,
  updateProducts,
  markUpdating,
  clearUpdating,
  resetSelection,
}: UseProductsTableActionsProps) {
  const handleBulkEnable = async (selectedIds: string[]) => {
    // Filter to products that need enabling
    const productsToEnable = products.filter(
      (p) => selectedIds.includes(p.id) && !p.isActive
    );

    if (productsToEnable.length === 0) {
      toast.info("All selected products are already active");
      return;
    }

    const idsToEnable = productsToEnable.map((p) => p.id);
    markUpdating(idsToEnable);

    try {
      const response = await bulkUpdateProductStatus(idsToEnable, true);

      if (response.updatedProducts?.length > 0) {
        await updateProducts(response.updatedProducts);
      }

      resetSelection();
      toast.success(`Enabled ${response.updatedProducts.length} products`);
    } catch (error) {
      console.error("Bulk enable failed:", error);
      toast.error("Failed to enable products");
    } finally {
      clearUpdating();
    }
  };

  const handleBulkDisable = async (selectedIds: string[]) => {
    const productsToDisable = products.filter(
      (p) => selectedIds.includes(p.id) && p.isActive
    );

    if (productsToDisable.length === 0) {
      toast.info("All selected products are already inactive");
      return;
    }

    const idsToDisable = productsToDisable.map((p) => p.id);
    markUpdating(idsToDisable);

    try {
      const response = await bulkUpdateProductStatus(idsToDisable, false);

      if (response.updatedProducts?.length > 0) {
        await updateProducts(response.updatedProducts);
      }

      resetSelection();
      toast.success(`Disabled ${response.updatedProducts.length} products`);
    } catch (error) {
      console.error("Bulk disable failed:", error);
      toast.error("Failed to disable products");
    } finally {
      clearUpdating();
    }
  };

  return {
    handleBulkEnable,
    handleBulkDisable,
  };
}
```

---

## Example 8: Type Definitions

```typescript
// types/products.ts

// Response types (from API)
export interface ProductResponse {
  id: string;
  nameEn: string;
  nameAr: string | null;
  price: number;
  categoryId: number;
  categoryName: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string | null;
}

export interface ProductsResponse {
  products: ProductResponse[];
  total: number;
  activeCount: number;
  inactiveCount: number;
}

// Request types (to API)
export interface ProductCreate {
  nameEn: string;
  nameAr?: string;
  price: number;
  categoryId: number;
}

export interface ProductUpdate {
  nameEn?: string;
  nameAr?: string;
  price?: number;
  categoryId?: number;
  isActive?: boolean;
}

// Bulk operation response
export interface BulkStatusResponse {
  updatedProducts: ProductResponse[];
  failedIds: string[];
}

// Category type
export interface CategoryResponse {
  id: number;
  nameEn: string;
  nameAr: string | null;
  isActive: boolean;
}
```
