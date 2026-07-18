import { usePosStore } from "../store";
import { useState } from "react";
import { Search, Plus, Star, Coffee } from "lucide-react";

type MenuItem = {
  id: number;
  name: string;
  description: string;
  price: string;
  image_url: string;
  category: string;
  is_available: boolean;
  is_featured: boolean;
  loyalty_reward: boolean;
  points_per_item: number;
  emoji: string;
};

export default function MenuGrid() {
  const menu = usePosStore((s) => s.menu);
  const addItemToCart = usePosStore((s) => s.addItemToCart);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  if (!menu) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>Loading menu...</p>
      </div>
    );
  }

  const categories = Object.keys(menu.categories);
  const allItems = Array.from(
    new Map(Object.values(menu.categories).flat().map((item) => [item.id, item])).values()
  );

  const filteredItems = allItems.filter((item) => {
    if (!item.is_available) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        item.name.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q)
      );
    }
    if (selectedCategory) {
      return item.category === selectedCategory;
    }
    return true;
  });

  function handleAddItem(item: MenuItem) {
    addItemToCart({
      menu_item_id: item.id,
      name: item.name,
      price: parseFloat(item.price),
      quantity: 1,
      subtotal: parseFloat(item.price),
    });
  }

  return (
    <div className="flex h-full flex-col">
      {/* Search bar */}
      <div className="shrink-0 border-b border-border px-4 py-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search menu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-border bg-muted/50 py-2.5 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:border-ink focus:outline-none focus:ring-1 focus:ring-ink"
          />
        </div>
      </div>

      {/* Category tabs */}
      <div className="shrink-0 flex gap-2 overflow-x-auto border-b border-border px-4 py-2 scrollbar-none">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`shrink-0 rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
            selectedCategory === null
              ? "bg-ink text-white"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`shrink-0 rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
              selectedCategory === cat
                ? "bg-ink text-white"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Menu items grid */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Coffee className="mb-3 h-10 w-10 opacity-40" />
            <p className="text-sm">No items found</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredItems.map((item) => (
              <button
                key={item.id}
                onClick={() => handleAddItem(item)}
                className="group flex flex-col rounded-2xl border border-border bg-card p-3 text-left transition-all hover:border-ink/20 hover:shadow-md active:scale-[0.98]"
              >
                {/* Image / Emoji */}
                <div className="relative mb-2 aspect-square overflow-hidden rounded-xl bg-muted">
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.name}
                      className="h-full w-full object-cover"
                      crossOrigin="anonymous"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-3xl">
                      {item.emoji || "☕"}
                    </div>
                  )}
                  {/* Badges */}
                  <div className="absolute left-1.5 top-1.5 flex gap-1">
                    {item.is_featured && (
                      <span className="rounded-full bg-amber-500 px-2 py-0.5 text-[9px] font-bold text-white">
                        FEATURED
                      </span>
                    )}
                    {item.loyalty_reward && (
                      <span className="rounded-full bg-green-500 px-2 py-0.5 text-[9px] font-bold text-white">
                        LOYALTY
                      </span>
                    )}
                  </div>
                  {/* Add button overlay */}
                  <div className="absolute bottom-1.5 right-1.5 opacity-0 transition-opacity group-hover:opacity-100">
                    <div className="grid h-8 w-8 place-items-center rounded-full bg-ink text-white shadow-lg">
                      <Plus className="h-4 w-4" />
                    </div>
                  </div>
                </div>

                {/* Info */}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {item.name}
                  </p>
                  {item.description && (
                    <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                      {item.description}
                    </p>
                  )}
                </div>

                {/* Price */}
                <div className="mt-2 flex items-center justify-between">
                  <p className="text-sm font-bold text-ink">
                    Rs {Number(item.price).toFixed(2)}
                  </p>
                  {item.points_per_item > 0 && (
                    <p className="flex items-center gap-0.5 text-[10px] text-amber-600">
                      <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                      {item.points_per_item}
                    </p>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
