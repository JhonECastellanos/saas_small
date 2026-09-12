export interface Category {
  id: number;
  name: string;
}

export interface AttributeValue {
  id: number;
  value: string;
  code: string;
}

export interface Attribute {
  id: number;
  name: string;
  code: string;
  sort_order: number;
  values: AttributeValue[];
}

export interface VariantAttribute {
  attribute_id: number;
  attribute_name: string;
  value_id: number;
  value: string;
  code: string;
}

export interface Variant {
  id: number;
  sku: string;
  barcode: string | null;
  is_active: boolean;
  unit_of_measure: string;
  attributes: VariantAttribute[];
  price: string | null;
  price_per_lb: string | null;
  price_status: string | null;
  stock: string | null;
}

export interface ProductListItem {
  id: number;
  name: string;
  base_sku: string;
  category_id: number | null;
  category_name: string | null;
  unit_of_measure: string;
  is_bulk: boolean;
  tax_rate: string;
  is_active: boolean;
  photo_path: string | null;
  variant_count: number;
}

export interface ProductDetail {
  id: number;
  name: string;
  description: string | null;
  base_sku: string;
  category_id: number | null;
  category_name: string | null;
  unit_of_measure: string;
  is_bulk: boolean;
  photo_path: string | null;
  tax_rate: string;
  is_active: boolean;
  variants: Variant[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
